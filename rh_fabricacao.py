"""Regras e apuração da Fabricação, separadas das demais frentes."""
import calendar
import hashlib
import json
import secrets
import re
from datetime import date, datetime
from zoneinfo import ZoneInfo
from decimal import Decimal, ROUND_HALF_UP


METAS = {
    "Chapa de Dimensão": 3, "Chapa RMT": 4, "Régua 0,75 m": 15,
    "Régua 1 m": 15, "Régua 1,5 m": 15, "Régua 3 m": 16,
    "Chapa de Assoalho": 13, "Mão Francesa": 16,
}
CONFIG = {"desconto_2_atestados_percentual": 50, "desconto_item_percentual": 5,
          "limite_he_sem_solicitacao": 5, "metas": METAS}
BASE_URL = "https://10sul-app-rh-jacpdfktaczhihbjnuucm2.streamlit.app/"


def hoje_local():
    return datetime.now(ZoneInfo("America/Sao_Paulo")).date()


def dias_pendentes(registros, ano, mes, metas):
    presentes = {str(r["data"]) for r in registros
                 if all((r.get("quantidades") or {}).get(item) is not None for item in metas)}
    return [date(ano, mes, dia) for dia in range(1, calendar.monthrange(ano, mes)[1] + 1)
            if date(ano, mes, dia).isoformat() not in presentes]


def verificar_aberta(sb, ano, mes):
    atuais = sb("GET", "rh_gratificacao_aprovacoes", f"select=status&ano=eq.{ano}&mes=eq.{mes}&order=id.desc&limit=1") or []
    if atuais and atuais[0].get("status") in ("AGUARDANDO_AUTORIZACAO", "AUTORIZADA"):
        raise ValueError("Competência enviada/autorizada: estoque bloqueado. Solicite a reabertura ao RH.")


def link_estoque(sb):
    rows = sb("GET", "rh_fabricacao_links", "select=token&ativo=eq.true&order=criado_em.desc&limit=1") or []
    if not rows:
        token = secrets.token_hex(32)
        rows = sb("POST", "rh_fabricacao_links", "", {"token": token}, "return=representation") or []
    return BASE_URL + "?estoque_fabricacao=" + rows[0]["token"]


def validar_link(sb, token):
    if not isinstance(token, str) or not re.fullmatch(r"[a-f0-9]{64}", token):
        return False
    return bool(sb("GET", "rh_fabricacao_links", f"select=id&ativo=eq.true&token=eq.{token}&limit=1"))


def tabela_resumo(st, pd, registros, metas, ano, mes):
    medias, assinatura = resumo_estoque(registros, metas)
    pendentes = dias_pendentes(registros, ano, mes, metas)
    total = calendar.monthrange(ano, mes)[1]
    st.caption(f"{total - len(pendentes)}/{total} dias conferidos. Média = soma das quantidades ÷ dias conferidos. Dias sem lançamento ficam pendentes; não são considerados zero.")
    st.dataframe(pd.DataFrame([{
        "ITEM": item, "META DA MÉDIA": meta, "MÉDIA DO MÊS": medias[item],
        "SITUAÇÃO": "PENDENTE" if medias[item] is None else ("ABAIXO DA META" if medias[item] < float(meta) else "META ATINGIDA")
    } for item, meta in metas.items()]), hide_index=True, use_container_width=True)
    if pendentes:
        st.caption("Dias sem conferência: " + ", ".join(d.strftime("%d/%m") for d in pendentes))
    return medias, assinatura, pendentes


def tela_conferencia(sb, token):
    import streamlit as st
    import pandas as pd
    st.markdown("## 🏭 Conferência diária do estoque — Fabricação")
    try:
        if not validar_link(sb, token):
            st.error("Link inválido ou desativado. Solicite o link atualizado ao RH.")
            return
        regras = sb("GET", "rh_regras_gratificacao", "select=fabricacao_config&codigo=eq.FABRICACAO&limit=1") or []
        if not regras:
            raise ValueError("Metas não cadastradas. Avise o RH.")
        metas = configuracao(regras[0])["metas"]
        st.caption("Informe a quantidade real de cada item. Registre zero quando não houver estoque.")
        dia = st.date_input("Data da conferência", value=hoje_local(), max_value=hoje_local(), key="fab_public_dia")
        registros = sb("GET", "rh_fabricacao_estoque", f"select=*&data=gte.{dia.replace(day=1)}&data=lte.{date(dia.year,dia.month,calendar.monthrange(dia.year,dia.month)[1])}&order=data.asc") or []
        anterior = next((r for r in registros if str(r["data"]) == dia.isoformat()), {})
        try:
            verificar_aberta(sb, dia.year, dia.month)
            bloqueada = False
        except ValueError as exc:
            st.warning(str(exc))
            bloqueada = True
        versao = str(anterior.get("atualizado_em") or "novo")
        with st.form(f"fab_diario_{dia}_{versao}"):
            responsavel = st.text_input("Nome de quem conferiu", disabled=bloqueada)
            quantidades = {}
            cols = st.columns(2)
            for n, item in enumerate(metas):
                salvo = (anterior.get("quantidades") or {}).get(item)
                quantidades[item] = cols[n % 2].number_input(item, min_value=0.0, value=float(salvo) if salvo is not None else None, step=1.0, key=f"fab_public_{dia}_{versao}_{n}", disabled=bloqueada)
            confirma = st.checkbox("Confirmo a substituição da conferência já registrada nesta data", disabled=bloqueada) if anterior else True
            salvar = st.form_submit_button("Salvar conferência do dia", type="primary", disabled=bloqueada)
        if salvar:
            if not responsavel.strip() or any(v is None for v in quantidades.values()) or not confirma:
                st.error("Informe seu nome e os oito itens. Se já existe conferência, confirme a substituição.")
            else:
                if not validar_link(sb, token):
                    raise ValueError("Este link foi desativado.")
                verificar_aberta(sb, dia.year, dia.month)
                atual = sb("GET", "rh_fabricacao_estoque", f"select=atualizado_em&data=eq.{dia}") or []
                if (atual[0].get("atualizado_em") if atual else None) != anterior.get("atualizado_em"):
                    raise ValueError("Outra pessoa alterou esta data. Recarregue antes de salvar.")
                sb("POST", "rh_fabricacao_estoque", "on_conflict=data", {
                    "data": dia.isoformat(), "quantidades": quantidades,
                    "atualizado_por": responsavel.strip(), "atualizado_em": datetime.now(ZoneInfo("America/Sao_Paulo")).isoformat()
                }, "resolution=merge-duplicates,return=minimal")
                st.session_state["fab_public_sucesso"] = f"Conferência de {dia.strftime('%d/%m/%Y')} salva."
                st.rerun()
        if st.session_state.get("fab_public_sucesso"):
            st.success(st.session_state.pop("fab_public_sucesso"))
        st.markdown("### Resumo do estoque no mês")
        tabela_resumo(st, pd, registros, metas, dia.year, dia.month)
        with st.expander("Conferências registradas"):
            st.dataframe(pd.DataFrame([{"DATA": r["data"], "CONFERIDO POR": r.get("atualizado_por"), **r["quantidades"]} for r in registros]), hide_index=True, use_container_width=True)
    except Exception as exc:
        st.error(f"Não foi possível concluir a conferência: {exc}")


def numero(regra, campo, padrao):
    valor = regra.get(campo)
    return float(padrao if valor is None else valor)


def configuracao(regra):
    cfg = {**CONFIG, **(regra.get("fabricacao_config") or {})}
    cfg["metas"] = {**METAS, **cfg.get("metas", {})}
    return cfg


def resumo_estoque(registros, metas):
    medias = {}
    for item in metas:
        valores = [float(r["quantidades"][item]) for r in registros
                   if (r.get("quantidades") or {}).get(item) is not None]
        medias[item] = sum(valores) / len(valores) if valores else None
    # Uma mudança de estoque ou meta exige nova conferência antes do fechamento.
    base = {"metas": metas, "registros": sorted(
        [{"data": str(r["data"]), "quantidades": r["quantidades"]} for r in registros],
        key=lambda r: r["data"])}
    assinatura = hashlib.sha256(json.dumps(base, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    return medias, assinatura


def calcular(salario, faltas, atestados, dna, horas, medias, conferido, regra, estoque_atendido=False):
    cfg = configuracao(regra)
    integral = Decimal(str(salario or 0)) * Decimal(str(numero(regra, "percentual_salario", 35))) / 100
    integral = integral.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    motivos, pendencias = [], []
    if salario is None or float(salario) <= 0:
        pendencias.append("informar salário-base")
    if horas is None:
        pendencias.append("informar horas extras sem solicitação (inclusive zero)")
    if not conferido and not estoque_atendido:
        pendencias.append("conferir estoque mensal")
    if not estoque_atendido and any(medias.get(item) is None for item in cfg["metas"]):
        pendencias.append("informar estoque dos 8 itens")
    # O termo não define o desconto para meio período; não presumir penalidade.
    if 0 < float(atestados) <= 2 and not float(atestados).is_integer():
        pendencias.append("atestado fracionado: definir critério da Fabricação")
    if faltas > 0:
        motivos.append(f"{faltas} falta(s)")
    dna_min = int(numero(regra, "dna_minimo", 2))
    if dna < dna_min:
        motivos.append(f"DNA {dna}/{dna_min}")
    if horas is not None and float(horas) > float(cfg["limite_he_sem_solicitacao"]):
        motivos.append(f"{float(horas):g}h extras sem solicitação: acima de {cfg['limite_he_sem_solicitacao']:g}h")
    if atestados > 2:
        motivos.append(f"{atestados:g} dias de atestado: acima de 2 dias")
    zerada = bool(motivos)
    desconto = Decimal("0")
    if atestados in (1, 2):
        pct = numero(regra, "desconto_1_atestado_percentual", 25) if atestados == 1 else float(cfg["desconto_2_atestados_percentual"])
        desconto += Decimal(str(pct))
        motivos.append(f"{atestados:g} dia(s) de atestado (-{pct:g}%)")
    abaixo = [] if estoque_atendido else [item for item, meta in cfg["metas"].items()
              if medias.get(item) is not None and medias[item] < float(meta)]
    if abaixo:
        pct = Decimal(str(cfg["desconto_item_percentual"])) * len(abaixo)
        desconto += pct
        motivos.append(f"Estoque: {len(abaixo)} item(ns) abaixo da meta (-{pct}%): " + ", ".join(abaixo))
    if estoque_atendido:
        motivos.append("Estoque do mês considerado atendido por opção do RH")
    if pendencias:
        return float(integral), None, " • ".join(pendencias + motivos)
    valor = Decimal("0") if zerada else max(Decimal("0"), integral * (1 - desconto / 100))
    return float(integral), float(valor.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)), " • ".join(motivos) or "Requisitos atendidos"


def tela_regra(st, r):
    cfg = configuracao(r)
    st.caption("35% do salário-base. Estoque: média mensal dos registros diários; desconto por item abaixo da meta.")
    a, b, c = st.columns(3)
    pct = a.number_input("Bonificação integral (% do salário)", 0.0, 100.0, numero(r, "percentual_salario", 35), key="fab_reg_pct")
    d1 = b.number_input("1 dia de atestado — desconto (%)", 0.0, 100.0, numero(r, "desconto_1_atestado_percentual", 25), key="fab_reg_at1")
    d2 = c.number_input("2 dias de atestado — desconto (%)", 0.0, 100.0, float(cfg["desconto_2_atestados_percentual"]), key="fab_reg_at2")
    a, b, c = st.columns(3)
    item = a.number_input("Desconto por item abaixo da meta (%)", 0.0, 100.0, float(cfg["desconto_item_percentual"]), key="fab_reg_item")
    limite = b.number_input("Limite de HE sem solicitação (h)", min_value=0.0, value=float(cfg["limite_he_sem_solicitacao"]), key="fab_reg_he")
    dna = c.number_input("DNA mínimo no mês", min_value=0, value=int(numero(r, "dna_minimo", 2)), key="fab_reg_dna")
    metas = {}
    st.markdown("**Metas de estoque por item**")
    cols = st.columns(4)
    for n, (nome, meta) in enumerate(cfg["metas"].items()):
        metas[nome] = cols[n % 4].number_input(nome, min_value=0.0, value=float(meta), key=f"fab_meta_{n}")
    st.info("Falta injustificada, DNA abaixo do mínimo, mais de 2 dias de atestado ou HE sem solicitação acima do limite zeram a bonificação. Descontos de estoque e atestado são somados sobre o valor integral.")
    return {"percentual_salario": pct, "desconto_1_atestado_percentual": d1, "dna_minimo": dna,
            "fabricacao_config": {"desconto_2_atestados_percentual": d2, "desconto_item_percentual": item,
                                   "limite_he_sem_solicitacao": limite, "metas": metas}}


def tela_lancamentos(st, pd, sb, ano, mes, colabs, regra, usr, bloqueada):
    cfg = configuracao(regra)
    ini = date(ano, mes, 1)
    fim = date(ano, mes, calendar.monthrange(ano, mes)[1])
    regs = sb("GET", "rh_fabricacao_estoque", f"select=*&data=gte.{ini}&data=lte.{fim}&order=data.asc") or []
    ap = sb("GET", "rh_fabricacao_apuracao", f"select=*&ano=eq.{ano}&mes=eq.{mes}") or []
    opcoes_mes = sb("GET", "rh_fabricacao_mes", f"select=*&ano=eq.{ano}&mes=eq.{mes}&limit=1") or []
    opcao_mes = opcoes_mes[0] if opcoes_mes else {}
    estoque_atendido = bool(opcao_mes.get("estoque_atendido", False))
    medias, assinatura = resumo_estoque(regs, cfg["metas"])
    por_id = {int(r["colaborador_id"]): r for r in ap}
    pendentes = dias_pendentes(regs, ano, mes, cfg["metas"])
    with st.expander("🏭 Fabricação — resumo mensal do estoque", expanded=True):
        st.caption("Os lançamentos diários são feitos no link de conferência do estoque. Aqui são exibidas apenas as médias e metas do mês.")
        tabela_resumo(st, pd, regs, cfg["metas"], ano, mes)
        with st.form(f"fab_opcao_mes_{ano}_{mes}"):
            considerar = st.checkbox("Deseja considerar o estoque do mês como atendido?", value=estoque_atendido, disabled=bloqueada)
            st.caption("Ao marcar e salvar, o estoque será considerado atendido para todos os colaboradores da Fabricação nesta competência. Não haverá desconto de estoque nem pendência por conferências diárias. Os demais critérios permanecem válidos.")
            salvar_opcao = st.form_submit_button("Salvar opção do estoque do mês", disabled=bloqueada)
        if salvar_opcao:
            verificar_aberta(sb, ano, mes)
            sb("POST", "rh_fabricacao_mes", "on_conflict=ano,mes", {
                "ano": ano, "mes": mes, "estoque_atendido": considerar,
                "atualizado_por": str(usr), "atualizado_em": datetime.now().isoformat()
            }, "resolution=merge-duplicates,return=minimal")
            st.rerun()
        if estoque_atendido:
            st.success("Estoque do mês considerado atendido. Desconto de estoque: 0%.")
            st.caption(f"Registrado por: {opcao_mes.get('atualizado_por') or '-'} • Em: {opcao_mes.get('atualizado_em') or '-'}")
        elif pendentes:
            st.info("Resumo provisório: faltam conferências diárias. A bonificação ficará pendente até completar o mês.")
        if bloqueada:
            st.info("Competência enviada ou autorizada: conferência mensal bloqueada.")
        opcoes = {int(c["id"]): c for c in colabs if str(c.get("frente") or "").upper().strip() == "FABRICAÇÃO"}
        if opcoes:
            cid = st.selectbox("Colaborador da Fabricação", list(opcoes), format_func=lambda x: f"{opcoes[x]['colaborador']} (ID {x})", key=f"fab_colab_{ano}_{mes}")
            anterior = por_id.get(cid, {})
            with st.form(f"fab_ap_{ano}_{mes}_{cid}_{assinatura[:12]}"):
                horas = st.number_input("Horas extras sem solicitação no mês (h)", min_value=0.0, value=float(anterior["horas_sem_solicitacao"]) if anterior.get("horas_sem_solicitacao") is not None else None, step=0.5, disabled=bloqueada)
                conferido = st.checkbox("Conferi as horas extras deste colaborador" if estoque_atendido else "Conferi os registros de estoque do mês e as horas extras deste colaborador", value=anterior.get("estoque_assinatura") == assinatura, disabled=bloqueada)
                salvar_ap = st.form_submit_button("Salvar conferência da Fabricação", disabled=bloqueada)
            if salvar_ap:
                if horas is None or not conferido or (not estoque_atendido and (pendentes or any(v is None for v in medias.values()))):
                    st.error("Informe as horas (inclusive zero) e marque a conferência das horas extras." if estoque_atendido else "Informe as horas (inclusive zero), complete as conferências diárias pelo link e marque a conferência mensal.")
                else:
                    verificar_aberta(sb, ano, mes)
                    atuais = sb("GET", "rh_fabricacao_estoque", f"select=*&data=gte.{ini}&data=lte.{fim}&order=data.asc") or []
                    if resumo_estoque(atuais, cfg["metas"])[1] != assinatura:
                        raise ValueError("O estoque mudou em outra sessão. Recarregue e confira novamente.")
                    sb("POST", "rh_fabricacao_apuracao", "on_conflict=colaborador_id,ano,mes", {
                        "colaborador_id": cid, "ano": ano, "mes": mes, "horas_sem_solicitacao": horas,
                        "estoque_assinatura": assinatura, "atualizado_por": str(usr),
                        "atualizado_em": datetime.now().isoformat()}, "resolution=merge-duplicates,return=minimal")
                    st.rerun()
    return medias, (None if pendentes else assinatura), por_id, estoque_atendido
