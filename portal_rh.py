import os
import json
import calendar
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime, date

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Portal RH | 10 Sul", page_icon="👥", layout="wide")

def segredo(nome):
    try:
        return str(st.secrets[nome]).strip()
    except Exception:
        return os.getenv(nome, "").strip()

SUPABASE_URL = segredo("SUPABASE_URL").rstrip("/")
SUPABASE_SERVICE_KEY = segredo("SUPABASE_SERVICE_KEY")

def sb(method, tabela, params="", payload=None, prefer=None):
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise RuntimeError("Configure SUPABASE_URL e SUPABASE_SERVICE_KEY nos Secrets do Portal RH.")
    url = f"{SUPABASE_URL}/rest/v1/{tabela}"
    if params:
        url += "?" + params
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("apikey", SUPABASE_SERVICE_KEY)
    req.add_header("Authorization", f"Bearer {SUPABASE_SERVICE_KEY}")
    req.add_header("Content-Type", "application/json")
    if prefer:
        req.add_header("Prefer", prefer)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
            return json.loads(raw.decode("utf-8")) if raw else None
    except urllib.error.HTTPError as e:
        detalhe = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Supabase HTTP {e.code}: {detalhe}") from e

SEED_COLABORADORES = [('ABRAAO OLIVEIRA DOS SANTOS', 'MECANICO'), ('ADAIR DO ROSARIO FERNANDES', 'SOLDADOR'), ('ADRIANO DOS SANTOS RIBEIRO', 'SOLDADOR'), ('MANOEL LUZ ALVES', 'MECANICO (SOCORRISTA)'), ('ALESSANDRO ROCHA MOREIRA', 'ELETRICISTA'), ('ANDRE GUIMARAES CORDEIRO', 'ENCARREGADO DE MANUTENCAO'), ('ANDRE MIRANDA', 'SOLDADOR'), ('ARTHUR DOS SANTOS DA SILVA', 'PINTOR'), ('BRUNO HENRIQUE ARAUJO DA SILVA', 'RESERVA SAP'), ('CARLOS ALBERTO DE SOUZA', 'LAVADOR'), ('CARLOS HENRIQUE DE SOUZA TESTA DA SILVA', 'MECANICO'), ('CARLOS HENRIQUE NASCIMENTO', 'SOLDADOR'), ('CLAUDINEI AMANCIO JACOB', 'LUBRIFICADOR'), ('CLEBER FRAGA BANDEIRA', 'MECANICO (SOCORRISTA)'), ('CLEBES SANTANA SANTOS', 'MECANICO III'), ('CLEISIMAR NICANOR ESPERANCA', 'MECANICO'), ('CRISTIANO QUIRINO MORAES', 'BARRACHEIRO'), ('DANIEL BERTOLDO RODRIGUES', 'MECANICO'), ('DEIVISON BUENO CUNHA', 'MECANICO'), ('DEMETRIO CORDEIRO FLORINDO', 'MECANICO'), ('DENISIO MAGELA ALVES', 'MECANICO II'), ('DIEGO ATHAYDE SCARDUA', 'MECANICO'), ('DIEGO MONTEIRO SILVA', 'AUX TEC E SEG DO TRABALHO'), ('DIMAS DA SILVA MUNIZ', 'MECANICO'), ('DIONES ALVARENGA DOS SANTOS', 'MECANICO'), ('DIONIS GABRIEL CAMPOS', 'AUXILIAR MECANICO'), ('DOUGLAS PEREIRA SANTOS', 'ELETRICISTA'), ('EDCARLOS FRANCISCO DA SILVA', 'MECANICO IV'), ('EDRICK OLIVIERA ALMEIDA', 'LAVADOR'), ('ELIAS DA SILVA JOVENCIO', 'APROVISIONADOR'), ('ELOISIO COVRE', 'MANOBRISTA 10S'), ('ENOC DE OLIVEIRA SANTOS', 'MECANICO (SOCORRISTA)'), ('EVANDRO DOS SANTOS OLIVEIRA JUNIOR', 'ANALISTA DE MANUTENÇÃO'), ('ERICK ROCHA COCCO', 'MECANICO (SOCORRISTA)'), ('EZEQUIEL ALVES VIEIRA', 'MECANICO'), ('EZEQUIEL DE MOURA PAIXÃO', 'BORRACHEIRO II'), ('EZEQUIEL SANTOS HERCULANO', 'APROVISIONADOR'), ('FABIO CANDEIAS SOUZA', 'MECANICO'), ('FABIO CORDEIRO DOS SANTOS', 'MECANICO III'), ('FABIO OLIVEIRA SILVA NOGUEIRA', 'MECANICO'), ('FABRICIO FANCHIOTTI', 'TORNEIRO MECANICO'), ('FELIPE REIS DE SOUZA', 'MECANICO'), ('FERNANDO FERNANDES COSTA', 'ALMOXARIFE DE MANUTENÇÃO II'), ('FRANCINY GIACOMIN ALBORGHETE MARTINELI', 'ANALISTA DE RH'), ('GABRIEL DA VITÓRIA ALVARENGA', 'ENCARREGADO DE MANUTENÇÃO II'), ('GABRYEL MACIEL PEREIRA', 'RECONDICIONAMENTO DE CUICA'), ('GEAN PEREIRA DE CARLI', 'AUXILIAR DE MECANICO'), ('GILMAR SILVA OLIVEIRA', 'BORRACHEIRO'), ('GILSON MATHIAS DO NASCIMENTO', 'ELETRICISTA'), ('FELIPE SOUZA MEDEIROS', 'MECANICO (SOCORRISTA)'), ('HELDER DA SILVA ROQUE', 'AUXILIAR MECANICO'), ('HORACIO GUILHERME DE SOUZA ALMEIDA', 'AUXILIAR MECANICO'), ('JARDEL SABINO FELIZARDO', 'MECANICO'), ('JEAN CARLOS LOUREIRO BARBOSA', 'MECANICO'), ('JEFFERSON DE SOUZA MONTEIRO', 'MECANICO'), ('JOAO MACHADO FERNANDES', 'AUXILIAR MECANICO'), ('JOCELI LIRIO DOS SANTOS', 'MECANICO II'), ('JORDAN DAS VIRGENS RIBEIRO', 'LUBRIFICADOR'), ('JOSE ANGEL LARA MATUTE', 'SOLDADOR'), ('JOSE ANTONIO DA SILVA ROSA', 'SOLDADOR'), ('JOSE RICARDO SANTOS', 'LAVADOR'), ('JULIANO DOS SANTOS DIOGO', 'MECANICO'), ('JULIO PAES SOUZA', 'MECANICO'), ('JURANDIR FERREIRA NUNES', 'MECANICO'), ('KAROLINA VAZ PEREIRA', 'TECNICO EM SEGURANÇA DO TRABALHO'), ('KELVIN CHAGAS SANTOS', 'MECANICO'), ('KENNEDY SANTOS DE JESUS', 'AUXILIAR MECANICO II'), ('KIERLEN ALMEIDA DOS SANTOS', 'SOLDADOR'), ('LEONARDO SANTOS MOURA', 'MECANICO'), ('LHESLEY GOMES DE OLIVEIRA', 'MECANICO'), ('LUAN GUIDOTI LIMA', 'MECANICO'), ('LUCAS AZEVEDO RUFINO', 'SOLDADOR'), ('LUCAS CORREA SA SILVA', 'APROVISIONADOR'), ('LUCAS DE SOUZA GOMES', 'SOLDADOR'), ('LUZINETE MONTEIRO CRUZ', 'AUXILIAR ADMINISTRATIVO'), ('MAIKO JHONATAN MARTINS LISBOA', 'MECANICO'), ('MARCELO DE OLIVEIRA', 'AUXILIAR DE SERVIÇOS GERAIS II'), ('MARCOS JACOB DE SOUZA', 'BORRACHEIRO'), ('MARCOS VINICIUS BENEDITO LEMOS', ''), ('MARLON PINHEIRO DE MATOS', 'MECANICO'), ('MATEUS GOMES BITI', 'MECANICO'), ('MATHEUS FERREIRA SANTUZZI', 'APROVISIONADOR'), ('MURILO GOMES CARVALHO', 'AUXILIAR MECANICO'), ('OSNIR PASSOS GOMES', 'ENCARREGADO DE MANUTENÇÃO IV'), ('PAULO CESAR DOS REIS', 'MECANICO'), ('PEDRO DE ASSIS JUNIOR', 'ELETRICISTA'), ('PEDRO DE JESUS BARBOSA', 'ELETRICISTA'), ('RAFAEL FRANCISCO DO NASCIMENTO SANTOS', 'MECANICO'), ('RAMON MUNIZ COSER', 'AUXILIAR MECANICO'), ('REGINALDO RIBEIRO DA SILVA', 'SOLDADOR'), ('RENATO DOS SANTOS GONÇALVES', 'MECANICO'), ('RIAN ANTONIO FERNANDES VARGAS', 'AUXILIAR DE ELETRICISTA DE VEICULOS'), ('ROGERIO DA CONCEIÇÃO REBOUÇAS', 'SOLDADOR'), ('ROSIVELTON OLIVEIRA GOMES', 'MECANICO'), ('RUBENS GUILHERME MARINS', 'SUPERVISOR'), ('RUBENS ROCHA CRUZ', 'INSPETOR'), ('SANTINHO PERONI', 'MECANICO'), ('SILAS PASSOS DE SOUSA', 'MECANICO (SOCORRISTA)'), ('SILVIO CARLOS SOUZA', 'CRAVEJAMENTO DE LONA'), ('SOLIMAR NATALI', 'SOLDADOR'), ('TASSIO DOS SANTOS QUARESMA', 'MECANICO'), ('VALTEMI CORREIA DE OLIVEIRA', 'SOLDADOR'), ('VANDER MARCOS DE SOUZA', 'MANOBRISTA'), ('VANILSON DE JESUS', 'MECANICO'), ('VICTOR MARCELINO RAMOS', 'AUXILIAR MECANICO'), ('VINICIUS HENRIQUE SANTOS SILVA', 'BORRACHEIRO'), ('VINICIUS PINTO ROSA', 'BORRACHEIRO'), ('VITOR SANTOS SOUZA', 'SOLDADOR'), ('WAGNER HONORIO DE ALMEIDA', 'SUPERVISOR'), ('WANDERSON SANTOS SOUZA', 'ELETRICISTA'), ('WALLACE RODRIGUES DO NASCIMENTO', 'BORRACHEIRO II'), ('WEBERSON CORDEIRO DOS SANTOS', 'SOLDADOR'), ('WENDRYEL PEREIRA AMORIM PAULUSCENA', 'MECANICO II'), ('WENIO DA PURIFICAÇÃO RIBEIRO', 'MECANICO'), ('WESLEY BRAGA CABRAL', 'MECANICO'), ('WESLEY SOUZA DOS SANTOS', 'MECANICO')]

STATUS_PADRAO = [
    {"codigo":"OK", "descricao":"PRESENÇA", "ordem":1, "ativo":True, "exige_observacao":False},
    {"codigo":"FO", "descricao":"FOLGA", "ordem":2, "ativo":True, "exige_observacao":False},
    {"codigo":"FA", "descricao":"FALTA", "ordem":3, "ativo":True, "exige_observacao":False},
    {"codigo":"A",  "descricao":"ATESTADO", "ordem":4, "ativo":True, "exige_observacao":False},
    {"codigo":"FE", "descricao":"FÉRIAS", "ordem":5, "ativo":True, "exige_observacao":False},
    {"codigo":"LB", "descricao":"LIBERADO", "ordem":6, "ativo":True, "exige_observacao":True},
]

def _campo_nome_colaborador(registro):
    """Aceita a estrutura atual do banco e também a estrutura antiga."""
    for campo in ("colaborador", "nome", "nome_colaborador"):
        if campo in registro:
            return campo
    return None

def _nome_colaborador(registro):
    campo = _campo_nome_colaborador(registro)
    return str(registro.get(campo) or "") if campo else ""

def sincronizar_seed():
    # O cadastro de colaboradores já existe no Supabase.
    # O Portal RH apenas consulta esse cadastro; não tenta recriá-lo
    # nem adivinhar o nome físico da coluna.
    return

def ler_colaboradores():
    # Não ordena pelo Supabase para não depender do nome físico da coluna.
    rows = sb("GET", "rh_colaboradores", "select=*&ativo=eq.true") or []
    return sorted(rows, key=lambda r: _nome_colaborador(r).upper())

def ler_ocorrencias():
    rows = sb("GET", "rh_ocorrencias", "select=*&ativo=eq.true") or []
    if not rows:
        return STATUS_PADRAO
    ordem = {x["codigo"]: x["ordem"] for x in STATUS_PADRAO}
    return sorted(rows, key=lambda x: ordem.get(str(x.get("codigo","")).upper(), 999))

def ler_frequencia(ano, mes):
    ini = f"{ano:04d}-{mes:02d}-01"
    ultimo = calendar.monthrange(ano, mes)[1]
    fim = f"{ano:04d}-{mes:02d}-{ultimo:02d}"
    params = (
        "select=*&data=gte." + urllib.parse.quote(ini) +
        "&data=lte." + urllib.parse.quote(fim)
    )
    return sb("GET", "rh_frequencia", params) or []

def salvar_frequencia(colaborador_id, dia, codigo, observacao=""):
    payload = {
        "colaborador_id": int(colaborador_id),
        "data": dia.isoformat(),
        "situacao": codigo,
        "observacao": observacao.strip() or None,
        "atualizado_em": datetime.now().isoformat(timespec="seconds"),
    }
    sb("POST", "rh_frequencia", "on_conflict=colaborador_id,data", payload,
       "resolution=merge-duplicates,return=minimal")

st.markdown("""
<style>
.block-container{padding-top:1.25rem;max-width:98%}
h1{margin-bottom:.1rem}
.rh-sub{color:#667085;margin-bottom:1rem}
div[data-testid="stDataEditor"]{border:1px solid #d0d5dd;border-radius:8px;overflow:hidden}
div[data-testid="stDataEditor"] [role="columnheader"]{font-weight:700!important}
</style>
""", unsafe_allow_html=True)

st.title("👥 Portal RH — Frequência")
st.markdown('<div class="rh-sub">10 Sul • Controle mensal de presença e ocorrências</div>', unsafe_allow_html=True)

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    st.error("Supabase ainda não configurado neste app. Adicione SUPABASE_URL e SUPABASE_SERVICE_KEY nos Secrets.")
    st.stop()

# Inicialização segura
try:
    garantir_ocorrencias()
    colaboradores = ler_colaboradores()
    if not colaboradores:
        sincronizar_seed()
        colaboradores = ler_colaboradores()
except Exception as e:
    st.error(f"Falha ao acessar o banco: {e}")
    st.stop()

hoje = date.today()
meses = ["Janeiro","Fevereiro","Março","Abril","Maio","Junho","Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"]

c1, c2, c3 = st.columns([1.4, .8, 3])
with c1:
    mes = st.selectbox("Mês", range(1,13), index=hoje.month-1, format_func=lambda x: meses[x-1])
with c2:
    ano = st.number_input("Ano", min_value=2025, max_value=2100, value=hoje.year, step=1)
with c3:
    st.markdown(f"### {meses[mes-1].upper()} / {int(ano)}")

ultimo_mes = calendar.monthrange(int(ano), mes)[1]
if int(ano) < hoje.year or (int(ano) == hoje.year and mes < hoje.month):
    ultimo_visivel = ultimo_mes
elif int(ano) == hoje.year and mes == hoje.month:
    ultimo_visivel = hoje.day
else:
    ultimo_visivel = 0

if ultimo_visivel == 0:
    st.info("Este mês ainda não começou. As colunas dos dias serão liberadas automaticamente conforme a data.")
    st.stop()

ocorrencias = ler_ocorrencias()
codigos = [str(x.get("codigo","")).upper().strip() for x in ocorrencias if x.get("codigo")]
codigos = list(dict.fromkeys(codigos))
if "" not in codigos:
    opcoes = [""] + codigos
else:
    opcoes = codigos

freq = ler_frequencia(int(ano), mes)
mapa = {}
obs_mapa = {}
for r in freq:
    try:
        d = pd.to_datetime(r.get("data")).date()
        chave = (int(r.get("colaborador_id")), d.day)
        mapa[chave] = str(r.get("situacao") or "")
        obs_mapa[chave] = str(r.get("observacao") or "")
    except Exception:
        pass

linhas = []
ids = []
for c in colaboradores:
    cid = int(c["id"])
    ids.append(cid)
    row = {
        "COLABORADOR": _nome_colaborador(c),
        "FUNÇÃO": str(c.get("funcao") or c.get("funcao_padrao") or ""),
    }
    for dia in range(1, ultimo_visivel + 1):
        row[f"{dia:02d}"] = mapa.get((cid, dia), "")
    linhas.append(row)

df = pd.DataFrame(linhas)
colunas_dia = [f"{d:02d}" for d in range(1, ultimo_visivel + 1)]

config = {
    "COLABORADOR": st.column_config.TextColumn("COLABORADOR", width="large", disabled=True),
    "FUNÇÃO": st.column_config.TextColumn("FUNÇÃO", width="medium", disabled=True),
}
for c in colunas_dia:
    config[c] = st.column_config.SelectboxColumn(c, options=opcoes, width="small", required=False)

editado = st.data_editor(
    df,
    use_container_width=True,
    hide_index=True,
    disabled=["COLABORADOR","FUNÇÃO"],
    column_config=config,
    key=f"rh_grade_{ano}_{mes}",
    height=min(820, 72 + max(1, len(df))*35),
)

alteracoes = []
for i, cid in enumerate(ids):
    for dia in range(1, ultimo_visivel + 1):
        col = f"{dia:02d}"
        antes = str(df.iloc[i][col] or "")
        depois = str(editado.iloc[i][col] or "")
        if antes != depois:
            alteracoes.append((i, cid, dia, antes, depois))

if alteracoes:
    st.markdown("#### Alterações pendentes")
    precisa_lb = [(i,cid,d,a,n) for i,cid,d,a,n in alteracoes if n == "LB"]
    observacoes = {}
    for i, cid, dia, antes, depois in precisa_lb:
        nome = editado.iloc[i]["COLABORADOR"]
        chave = (cid, dia)
        observacoes[chave] = st.text_input(
            f"{nome} • dia {dia:02d} • LB — Quem liberou / observação",
            value=obs_mapa.get(chave, ""),
            key=f"obs_lb_{cid}_{ano}_{mes}_{dia}",
            placeholder="Ex.: Liberado por Supervisor Fulano — motivo..."
        )

    pode_salvar = all(str(v).strip() for v in observacoes.values())
    if precisa_lb and not pode_salvar:
        st.warning("LB exige obrigatoriamente quem liberou / observação.")

    if st.button("💾 Salvar alterações", type="primary", disabled=not pode_salvar):
        try:
            for i, cid, dia, antes, depois in alteracoes:
                data_dia = date(int(ano), mes, dia)
                obs = observacoes.get((cid,dia), obs_mapa.get((cid,dia), ""))
                salvar_frequencia(cid, data_dia, depois, obs)
            st.success(f"{len(alteracoes)} lançamento(s) salvo(s).")
            st.rerun()
        except Exception as e:
            st.error(f"Não foi possível salvar: {e}")

with st.expander("⚙️ Cadastro de ocorrências"):
    st.caption("Esses códigos alimentam as opções disponíveis na grade.")
    st.dataframe(pd.DataFrame(ocorrencias), use_container_width=True, hide_index=True)

st.caption("Desenvolvido para 10 Sul • Portal RH")
