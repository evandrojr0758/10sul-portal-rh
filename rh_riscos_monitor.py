"""Frequência de atividades a partir da cópia ASN usada pelo Monitor Web."""
from datetime import date, datetime, timedelta, time
from zoneinfo import ZoneInfo
import re
import unicodedata
from urllib.parse import urlencode
import pandas as pd
import streamlit as st

COLUNAS = ["os_id", "frota", "evento", "status", "parada", "inicio", "fim",
           "descricao", "modal", "unidade", "sincronizado_em"]

def normalizar(valor):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKD", str(valor or "")).encode("ascii", "ignore").decode().lower()).strip()

# Variações iniciais; o cadastro da atividade permite complementar os termos.
REGRAS = [
    ("alinhamento de pneus", ["alinhamento", "alinhar pneu", "alinhando pneu"], None),
    ("calibragem", ["calibragem", "calibracao", "calibrar pneu", "calibrado"], "pneus"),
    ("mapeamento de pneus", ["mapeamento", "mapear pneu", "mapeado"], "pneus"),
    ("lavagem de carretas", ["lavagem", "lavar carreta"], None),
    ("lubrificacao de carretas", ["lubrificacao", "lubrificar", "engraxar"], None),
    ("socorro mecanico", ["socorro mecanico", "socorro de mecanica"], "sos"),
    ("regulagem de freios", ["regulagem de freio", "regular freio", "regulagem dos freios"], None),
    ("regulagem da suspensao", ["regulagem da suspensao", "regular suspensao"], None),
    ("remocao e instalacao de rodeiro", ["troca de rodeiro", "trocar rodeiro", "substituicao de rodeiro"], None),
    ("montagem/desmontagem de pneus", ["montagem de pneu", "desmontagem de pneu", "troca de pneu", "trocar pneu"], None),
    ("pintura nas carretas", ["pintura", "pintar carreta"], None),
    ("troca de eixo", ["troca de eixo", "trocar eixo", "substituicao de eixo"], None),
    ("troca de feixes de molas", ["feixe de mola", "feixes de mola"], None),
    ("troca de bolsa de ar", ["bolsa de ar"], None),
    ("troca de paralamas", ["paralama", "para lama"], None),
    ("substituicao de mangueira pneumatica", ["mangueira pneumatica", "mangueira de ar"], None),
    ("substituicao/recuperacao de cuicas", ["cuica"], None),
    ("substituicao da 5", ["quinta roda", "5 roda", "5a roda"], None),
]

def regra_atividade(atividade):
    nome = normalizar(atividade.get("atividade"))
    termos = [nome] if nome else []
    automatica = None
    if "servicos a quente" in nome or "servico a quente" in nome:
        termos = ["solda", "soldas", "soldagem", "soldar", "soldado", "soldada",
                  "soldando", "servicos a quente", "servico a quente"]
    for prefixo, padroes, auto in REGRAS:
        if nome.startswith(prefixo):
            termos, automatica = list(padroes), auto
            break
    personalizados = atividade.get("termos_monitor")
    if isinstance(personalizados, str):
        termos = [normalizar(t) for t in personalizados.splitlines() if normalizar(t)]
    return termos, automatica

def contem(texto, termo):
    return bool(termo and re.search(r"(?<![a-z0-9])" + re.escape(termo) + r"(?![a-z0-9])", texto))

def negado(texto, termos):
    # Negativas explícitas prevalecem sobre menções de serviço planejado.
    for termo in termos:
        palavra = re.escape(termo.split()[0]) if termo else ""
        if palavra and (re.search(r"(?:nao (?:foi )?(?:feito|feita|realizado|realizada|executado|executada)|cancelado|cancelada|reprogramado|reprogramada).{0,45}\b" + palavra, texto)
                        or re.search(r"\b" + palavra + r".{0,30}(?:nao (?:foi )?(?:feito|feita|realizado|realizada|executado|executada)|cancelado|cancelada|reprogramado|reprogramada)", texto)):
            return True
    return False

def reconhecer(registro, atividade):
    termos, auto = regra_atividade(atividade)
    descricao = normalizar(registro.get("descricao"))
    evento = normalizar(registro.get("evento"))
    if negado(descricao, termos):
        return None
    por_evento = auto == "pneus" and bool(re.search(r"\bitr\b|\brevisao\b", evento))
    por_evento = por_evento or (auto == "sos" and "sos" in evento and "pneu" not in evento)
    por_descricao = any(contem(descricao, termo) for termo in termos)
    if por_evento and por_descricao:
        return "ITR/Revisão + descrição" if auto == "pneus" else "Evento + descrição"
    if por_evento:
        return "Regra ITR/Revisão" if auto == "pneus" else "Evento SOS"
    return "Descrição" if por_descricao else None

def momento(valor):
    if not valor:
        return None
    try:
        dt = datetime.fromisoformat(str(valor).replace("Z", "+00:00"))
        if dt.tzinfo is not None:
            dt = dt.astimezone(ZoneInfo("America/Sao_Paulo")).replace(tzinfo=None)
        return dt
    except (ValueError, TypeError):
        return None

def apurar(registros, atividades, inicio, fim, unidade="ARA"):
    atividades = [dict(a) for a in atividades]
    if not any(normalizar(a.get("atividade")).startswith("mapeamento de pneus") for a in atividades):
        atividades.append({"id": "regra_mapeamento", "atividade": "Mapeamento de pneus",
                           "frequencia_atividade": "Diária"})
    resumos, detalhes = [], {}
    elegiveis = []
    for r in registros:
        data = momento(r.get("fim"))
        if not data or not inicio <= data.date() <= fim:
            continue
        if r.get("excluida_asn_em") or "cancel" in normalizar(r.get("status")):
            continue
        if not str(r.get("os_id") or "").strip():
            continue
        if "cavalo" in normalizar(r.get("modal")):
            continue
        if unidade != "TODAS" and str(r.get("unidade") or "").strip().upper() != unidade:
            continue
        elegiveis.append((r, data))
    for a in atividades:
        vistos = {}
        for r, data in elegiveis:
            origem = reconhecer(r, a)
            if origem:
                # Mesmo evento + descrição ou linhas repetidas contam uma só OS.
                chave = str(r["os_id"]).strip()
                atual = vistos.get(chave)
                if not atual or data > atual[1]:
                    vistos[chave] = (r, data, origem)
        linhas = [{"OS": r["os_id"], "Frota": r.get("frota"), "Data": dt.strftime("%d/%m/%Y %H:%M"),
                   "Descrição": r.get("descricao") or "", "Reconhecido por": origem, "_data": dt}
                  for r, dt, origem in vistos.values()]
        linhas.sort(key=lambda l: l["_data"], reverse=True)
        chave = str(a.get("id", a.get("atividade")))
        detalhes[chave] = linhas
        dias = {l["_data"].date() for l in linhas}
        semanas = {l["_data"].date().isocalendar()[:2] for l in linhas}
        meses = {(l["_data"].year, l["_data"].month) for l in linhas}
        resumos.append({"_chave": chave, "Atividade": a.get("atividade"),
                        "Frequência informada": a.get("frequencia_atividade") or "Diária",
                        "Ocorrências (OS)": len(linhas), "Dias com registro": len(dias),
                        "Semanas com registro": len(semanas), "Meses com registro": len(meses),
                        "Frequência observada": f"{len(dias)} de {(fim-inicio).days+1} dias",
                        "Último registro": linhas[0]["Data"] if linhas else "Sem registro no período"})
    return resumos, detalhes

def carregar(sb, inicio, fim, unidade):
    registros = []
    offset = 0
    while True:
        params = {
            "select": ",".join(COLUNAS), "excluida_asn_em": "is.null",
            "and": f"(fim.gte.{inicio.isoformat()}T00:00:00,fim.lt.{(fim+timedelta(days=1)).isoformat()}T00:00:00)",
            "order": "fim.asc,os_id.asc", "limit": "1000", "offset": str(offset),
        }
        if unidade != "TODAS":
            params["unidade"] = "eq." + unidade
        pagina = sb("GET", "monitor_asn", urlencode(params)) or []
        registros.extend(pagina)
        if len(pagina) < 1000:
            break
        offset += len(pagina)
    recente = sb("GET", "monitor_asn", "select=sincronizado_em&order=sincronizado_em.desc.nullslast&limit=1") or []
    return registros, recente[0].get("sincronizado_em") if recente else None

def observacao_na_tabela(sb, atividades):
    """Compartilha a consulta ASN entre a grade principal e a aba detalhada."""
    hoje = datetime.now(ZoneInfo("America/Sao_Paulo")).date()
    inicio = st.session_state.get("freq_monitor_inicio", hoje-timedelta(days=29))
    fim = st.session_state.get("freq_monitor_fim", hoje)
    unidade = st.session_state.get("freq_monitor_unidade", "ARA")
    if inicio > fim:
        return {}, "Período inválido: revise as datas na aba Frequência no Monitor."
    escopo = (inicio.isoformat(), fim.isoformat(), unidade)
    agora = datetime.now(ZoneInfo("America/Sao_Paulo")).timestamp()
    salvo = st.session_state.get("freq_monitor_base")
    idade = agora - st.session_state.get("freq_monitor_cache_em", 0)
    if not salvo or salvo[0] != escopo or idade >= 300:
        registros, sincronizacao = carregar(sb, inicio, fim, unidade)
        salvo = (escopo, registros, sincronizacao)
        st.session_state["freq_monitor_base"] = salvo
        st.session_state["freq_monitor_cache_em"] = agora
    resumos, _ = apurar(salvo[1], atividades, inicio, fim, unidade)
    valores = {
        r["_chave"]: f'{r["Frequência observada"]} ({r["Ocorrências (OS)"]} OS)'
        for r in resumos
    }
    contexto = f"Frequência observada: {inicio:%d/%m/%Y} a {fim:%d/%m/%Y} • Unidade {unidade}. Dias com registros e quantidade de OS finalizadas. Atualização da consulta a cada 5 minutos ao usar a página; período e detalhes na aba Frequência no Monitor."
    return valores, contexto


def tela(sb, atividades):
    st.subheader("Frequência das atividades no Monitor Web / ASN")
    st.caption("Consulta a mesma cópia ASN usada pelo Monitor Web. Conta OS finalizadas pela data de FIM, excluindo CAVALO, exclusões confirmadas e negativas explícitas de execução.")
    hoje = datetime.now(ZoneInfo("America/Sao_Paulo")).date()
    c1,c2,c3 = st.columns(3)
    inicio = c1.date_input("De", value=hoje-timedelta(days=29), key="freq_monitor_inicio")
    fim = c2.date_input("Até", value=hoje, max_value=hoje, key="freq_monitor_fim")
    unidade = c3.selectbox("Unidade", ["ARA","MUC","TODAS"], key="freq_monitor_unidade")
    st.info("ITR e REVISÃO contam como mapeamento e calibração de pneus, mesmo sem descrição. Alinhamento depende da descrição. Uma atividade conta uma vez por OS. Essa inferência não confirma outros serviços, como marcação a quente.")
    if inicio > fim:
        st.error("A data inicial deve ser anterior ou igual à final.")
        return
    escopo = (inicio.isoformat(), fim.isoformat(), unidade)
    if st.button("Consultar / atualizar frequência no monitor", key="freq_monitor_atualizar", type="primary"):
        try:
            with st.spinner("Consultando registros ASN…"):
                registros, sincronizacao = carregar(sb, inicio, fim, unidade)
            st.session_state["freq_monitor_base"] = (escopo, registros, sincronizacao)
            st.session_state["freq_monitor_cache_em"] = datetime.now(ZoneInfo("America/Sao_Paulo")).timestamp()
        except Exception as exc:
            st.error(f"Não foi possível consultar a ASN: {exc}")
            return
    salvo = st.session_state.get("freq_monitor_base")
    if not salvo or salvo[0] != escopo:
        st.caption("Selecione o período e clique em Consultar / atualizar frequência no monitor.")
        return
    _, registros, sincronizacao = salvo
    st.caption("Última sincronização ASN: " + (str(sincronizacao) if sincronizacao else "não informada"))
    resumos, detalhes = apurar(registros, atividades, inicio, fim, unidade)
    tabela = pd.DataFrame(resumos)
    if tabela.empty:
        st.info("Nenhuma atividade cadastrada.")
        return
    selecao = st.dataframe(tabela.drop(columns="_chave"), hide_index=True, use_container_width=True,
                          on_select="rerun", selection_mode="single-row", key="freq_monitor_resumo")
    st.caption("Selecione uma linha para ver OS, frota, data e descrição. A frequência observada mostra dias com registros no período, sem alterar a frequência informada nem a probabilidade.")
    linhas_selecionadas = selecao.get("selection", {}).get("rows", [])
    ids = [r["_chave"] for r in resumos]
    indice = linhas_selecionadas[0] if linhas_selecionadas and linhas_selecionadas[0] < len(ids) else 0
    alvo = st.selectbox("Detalhar atividade", ids, index=indice,
                        format_func=lambda i: next(r["Atividade"] for r in resumos if r["_chave"]==i),
                        key="freq_monitor_detalhar_" + str(indice))
    detalhe = detalhes[alvo]
    st.dataframe(pd.DataFrame([{k:v for k,v in l.items() if k!="_data"} for l in detalhe],
                             columns=["OS","Frota","Data","Descrição","Reconhecido por"]),
                 hide_index=True, use_container_width=True)
    st.download_button("Baixar resumo da frequência (CSV)", tabela.drop(columns="_chave").to_csv(index=False,sep=";").encode("utf-8-sig"),
                       "frequencia_monitor.csv","text/csv",key="freq_monitor_csv")
    st.caption("Atividades sem correspondência não significam ausência de execução: revise os termos de busca na aba Validar / editar atividade. A linha Mapeamento de pneus é acrescentada somente nesta consulta quando não há cadastro próprio no mapa.")
