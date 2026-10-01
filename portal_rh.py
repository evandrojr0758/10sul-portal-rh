import os
import json
import calendar
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime, date
from io import BytesIO

import pandas as pd
import streamlit as st
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
from openpyxl.utils import get_column_letter

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

CLASSIFICACAO_REFERENCIA = {'ABRAAO OLIVEIRA DOS SANTOS': 'OPERACIONAL', 'ADAIR DO ROSARIO FERNANDES': 'OPERACIONAL', 'ADRIANO DOS SANTOS RIBEIRO': 'OPERACIONAL', 'MANOEL LUZ ALVES': 'OPERACIONAL', 'ALESSANDRO ROCHA MOREIRA': 'OPERACIONAL', 'ANDRE GUIMARAES CORDEIRO': 'OUTROS', 'ANDRE MIRANDA': 'OPERACIONAL', 'ARTHUR DOS SANTOS DA SILVA': 'OPERACIONAL', 'BRUNO HENRIQUE ARAUJO DA SILVA': 'OPERACIONAL', 'CARLOS ALBERTO DE SOUZA': 'OPERACIONAL', 'CARLOS HENRIQUE DE SOUZA TESTA DA SILVA': 'OPERACIONAL', 'CARLOS HENRIQUE NASCIMENTO': 'OPERACIONAL', 'CLAUDINEI AMANCIO JACOB': 'OPERACIONAL', 'CLEBER FRAGA BANDEIRA': 'OPERACIONAL', 'CLEBES SANTANA SANTOS': 'OPERACIONAL', 'CLEISIMAR NICANOR ESPERANCA': 'OPERACIONAL', 'CRISTIANO QUIRINO MORAES': 'OPERACIONAL', 'DANIEL BERTOLDO RODRIGUES': 'OPERACIONAL', 'DEIVISON BUENO CUNHA': 'OPERACIONAL', 'DEMETRIO CORDEIRO FLORINDO': 'OPERACIONAL', 'DENISIO MAGELA ALVES': 'OPERACIONAL', 'DIEGO ATHAYDE SCARDUA': 'OPERACIONAL', 'DIEGO MONTEIRO SILVA': 'OUTROS', 'DIMAS DA SILVA MUNIZ': 'OPERACIONAL', 'DIONES ALVARENGA DOS SANTOS': 'OPERACIONAL', 'DIONIS GABRIEL CAMPOS': 'OPERACIONAL', 'DOUGLAS PEREIRA SANTOS': 'OPERACIONAL', 'EDCARLOS FRANCISCO DA SILVA': 'OPERACIONAL', 'EDRICK OLIVIERA ALMEIDA': 'OUTROS', 'ELIAS DA SILVA JOVENCIO': 'OPERACIONAL', 'ELOISIO COVRE': 'OUTROS', 'ENOC DE OLIVEIRA SANTOS': 'OPERACIONAL', 'EVANDRO DOS SANTOS OLIVEIRA JUNIOR': 'OUTROS', 'ERICK ROCHA COCCO': 'OPERACIONAL', 'EZEQUIEL ALVES VIEIRA': 'OPERACIONAL', 'EZEQUIEL DE MOURA PAIXÃO': 'OPERACIONAL', 'EZEQUIEL SANTOS HERCULANO': 'OPERACIONAL', 'FABIO CANDEIAS SOUZA': 'OPERACIONAL', 'FABIO CORDEIRO DOS SANTOS': 'OPERACIONAL', 'FABIO OLIVEIRA SILVA NOGUEIRA': 'OPERACIONAL', 'FABRICIO FANCHIOTTI': 'OUTROS', 'FELIPE REIS DE SOUZA': 'OPERACIONAL', 'FERNANDO FERNANDES COSTA': 'OUTROS', 'FRANCINY GIACOMIN ALBORGHETE MARTINELI': 'OUTROS', 'GABRIEL DA VITÓRIA ALVARENGA': 'OUTROS', 'GABRYEL MACIEL PEREIRA': 'OPERACIONAL', 'GEAN PEREIRA DE CARLI': 'OPERACIONAL', 'GILMAR SILVA OLIVEIRA': 'OPERACIONAL', 'GILSON MATHIAS DO NASCIMENTO': 'OPERACIONAL', 'FELIPE SOUZA MEDEIROS': 'OPERACIONAL', 'HELDER DA SILVA ROQUE': 'OPERACIONAL', 'HORACIO GUILHERME DE SOUZA ALMEIDA': 'OPERACIONAL', 'HUGO ROSSONY RUY': 'OPERACIONAL', 'JARDEL SABINO FELIZARDO': 'OPERACIONAL', 'JEAN CARLOS LOUREIRO BARBOSA': 'OPERACIONAL', 'JEFFERSON DE SOUZA MONTEIRO': 'OPERACIONAL', 'JOAO MACHADO FERNANDES': 'OPERACIONAL', 'JOCELI LIRIO DOS SANTOS': 'OPERACIONAL', 'JORDAN DAS VIRGENS RIBEIRO': 'OPERACIONAL', 'JOSE ANGEL LARA MATUTE': 'OPERACIONAL', 'JOSE ANTONIO DA SILVA ROSA': 'OPERACIONAL', 'JOSE RICARDO SANTOS': 'OPERACIONAL', 'JULIANO DOS SANTOS DIOGO': 'OPERACIONAL', 'JULIO PAES SOUZA': 'OPERACIONAL', 'JURANDIR FERREIRA NUNES': 'OPERACIONAL', 'KAROLINA VAZ PEREIRA': 'OUTROS', 'KELVIN ALEXANDRE RAMOS': 'OPERACIONAL', 'KELVIN CHAGAS SANTOS': 'OPERACIONAL', 'KENNEDY SANTOS DE JESUS': 'OPERACIONAL', 'KIERLEN ALMEIDA DOS SANTOS': 'OPERACIONAL', 'LEONARDO SANTOS MOURA': 'OPERACIONAL', 'LHESLEY GOMES DE OLIVEIRA': 'OPERACIONAL', 'LUAN GUIDOTI LIMA': 'OPERACIONAL', 'LUCAS AZEVEDO RUFINO': 'OPERACIONAL', 'LUCAS CORREA SA SILVA': 'OPERACIONAL', 'LUCAS DE SOUZA GOMES': 'OPERACIONAL', 'LUZINETE MONTEIRO CRUZ': 'OUTROS', 'MAIKO JHONATAN MARTINS LISBOA': 'OPERACIONAL', 'MARCELO DE OLIVEIRA': 'OPERACIONAL', 'MARCOS JACOB DE SOUZA': 'OPERACIONAL', 'MARCOS VINICIUS BENEDITO LEMOS': 'OUTROS', 'MARLON PINHEIRO DE MATOS': 'OPERACIONAL', 'MATEUS GOMES BITI': 'OPERACIONAL', 'MATHEUS FERREIRA SANTUZZI': 'OPERACIONAL', 'MURILO GOMES CARVALHO': 'OPERACIONAL', 'OSNIR PASSOS GOMES': 'OUTROS', 'PAULO CESAR DOS REIS': 'OPERACIONAL', 'PEDRO DE ASSIS JUNIOR': 'OPERACIONAL', 'PEDRO DE JESUS BARBOSA': 'OPERACIONAL', 'RAFAEL FRANCISCO DO NASCIMENTO SANTOS': 'OPERACIONAL', 'RAMON MUNIZ COSER': 'OPERACIONAL', 'REGINALDO RIBEIRO DA SILVA': 'OPERACIONAL', 'RENATO DOS SANTOS GONÇALVES': 'OPERACIONAL', 'RIAN ANTONIO FERNANDES VARGAS': 'OPERACIONAL', 'ROGERIO DA CONCEIÇÃO REBOUÇAS': 'OPERACIONAL', 'ROSIVELTON OLIVEIRA GOMES': 'OPERACIONAL', 'RUBENS BRAGANÇA DA SILVA': 'OPERACIONAL', 'RUBENS GUILHERME MARINS': 'OUTROS', 'RUBENS ROCHA CRUZ': 'OPERACIONAL', 'SANTINHO PERONI': 'OPERACIONAL', 'SILAS PASSOS DE SOUSA': 'OPERACIONAL', 'SILVIO CARLOS SOUZA': 'OPERACIONAL', 'SOLIMAR NATALI': 'OPERACIONAL', 'TASSIO DOS SANTOS QUARESMA': 'OPERACIONAL', 'VALTEMI CORREIA DE OLIVEIRA': 'OPERACIONAL', 'VANDER MARCOS DE SOUZA': 'OUTROS', 'VANILSON DE JESUS': 'OPERACIONAL', 'VICTOR MARCELINO RAMOS': 'OPERACIONAL', 'VINICIUS HENRIQUE SANTOS SILVA': 'OPERACIONAL', 'VINICIUS PINTO ROSA': 'OPERACIONAL', 'VITOR SANTOS SOUZA': 'OPERACIONAL', 'WAGNER HONORIO DE ALMEIDA': 'OUTROS', 'WANDERSON SANTOS SOUZA': 'OPERACIONAL', 'WALLACE RODRIGUES DO NASCIMENTO': 'OPERACIONAL', 'WEBERSON CORDEIRO DOS SANTOS': 'OPERACIONAL', 'WENDRYEL PEREIRA AMORIM PAULUSCENA': 'OPERACIONAL', 'WENIO DA PURIFICAÇÃO RIBEIRO': 'OPERACIONAL', 'WESLEY BRAGA CABRAL': 'OPERACIONAL', 'WESLEY SOUZA DOS SANTOS': 'OPERACIONAL'}

EMPRESA_REFERENCIA = {
    'ABRAAO OLIVEIRA DOS SANTOS': '10 SUL SERVICE',
    'ADAIR DO ROSARIO FERNANDES': '10 SUL SERVICE',
    'ADRIANO DOS SANTOS RIBEIRO': '10 SUL SERVICE',
    'ALESSANDRO ROCHA MOREIRA': '10 SUL SERVICE',
    'ANDRE GUIMARAES CORDEIRO': '10 SUL SERVICE',
    'ANDRE MIRANDA': '10 SUL SERVICE',
    'ARTHUR DOS SANTOS DA SILVA': '10 SUL PRESTADORA',
    'BRUNO HENRIQUE ARAUJO DA SILVA': '10 SUL SERVICE',
    'CARLOS ALBERTO DE SOUZA': '10 SUL SERVICE',
    'CARLOS HENRIQUE DE SOUZA TESTA DA SILVA': '10 SUL SERVICE',
    'CARLOS HENRIQUE NASCIMENTO': '10 SUL SERVICE',
    'CLAUDINEI AMANCIO JACOB': '10 SUL SERVICE',
    'CLEBER FRAGA BANDEIRA': '10 SUL SERVICE',
    'CLEBES SANTANA SANTOS': '10 SUL SERVICE',
    'CLEISIMAR NICANOR ESPERANCA': '10 SUL SERVICE',
    'CRISTIANO QUIRINO MORAES': '10 SUL SERVICE',
    'DANIEL BERTOLDO RODRIGUES': '10 SUL SERVICE',
    'DEIVISON BUENO CUNHA': '10 SUL SERVICE',
    'DEMETRIO CORDEIRO FLORINDO': '10 SUL SERVICE',
    'DENISIO MAGELA ALVES': '10 SUL SERVICE',
    'DIEGO ATHAYDE SCARDUA': '10 SUL SERVICE',
    'DIEGO MONTEIRO SILVA': '10 SUL SERVICE',
    'DIMAS DA SILVA MUNIZ': '10 SUL SERVICE',
    'DIONES ALVARENGA DOS SANTOS': '10 SUL SERVICE',
    'DIONIS GABRIEL CAMPOS': '10 SUL SERVICE',
    'DOUGLAS PEREIRA SANTOS': '10 SUL SERVICE',
    'EDCARLOS FRANCISCO DA SILVA': '10 SUL SERVICE',
    'EDRICK OLIVIERA ALMEIDA': '10 SUL SERVICE',
    'ELIAS DA SILVA JOVENCIO': '10 SUL SERVICE',
    'ELOISIO COVRE': '10 SUL SERVICE',
    'ENOC DE OLIVEIRA SANTOS': '10 SUL SERVICE',
    'ERICK ROCHA COCCO': '10 SUL PRESTADORA',
    'EVANDRO DOS SANTOS OLIVEIRA JUNIOR': '10 SUL SERVICE',
    'EZEQUIEL ALVES VIEIRA': '10 SUL SERVICE',
    'EZEQUIEL DE MOURA PAIXÃO': '10 SUL SERVICE',
    'EZEQUIEL SANTOS HERCULANO': '10 SUL SERVICE',
    'FABIO CANDEIAS SOUZA': '10 SUL SERVICE',
    'FABIO CORDEIRO DOS SANTOS': '10 SUL SERVICE',
    'FABIO OLIVEIRA SILVA NOGUEIRA': '10 SUL SERVICE',
    'FABRICIO FANCHIOTTI': '10 SUL SERVICE',
    'FELIPE REIS DE SOUZA': '10 SUL SERVICE',
    'FELIPE SOUZA MEDEIROS': '10 SUL PRESTADORA',
    'FERNANDO FERNANDES COSTA': '10 SUL SERVICE',
    'FRANCINY GIACOMIN ALBORGHETE MARTINELI': '10 SUL SERVICE',
    'GABRIEL DA VITÓRIA ALVARENGA': '10 SUL SERVICE',
    'GABRYEL MACIEL PEREIRA': '10 SUL SERVICE',
    'GEAN PEREIRA DE CARLI': '10 SUL SERVICE',
    'GILMAR SILVA OLIVEIRA': '10 SUL SERVICE',
    'GILSON MATHIAS DO NASCIMENTO': '10 SUL SERVICE',
    'HELDER DA SILVA ROQUE': '10 SUL SERVICE',
    'HORACIO GUILHERME DE SOUZA ALMEIDA': '10 SUL SERVICE',
    'HUGO ROSSONY RUY': '10 SUL SERVICE',
    'JARDEL SABINO FELIZARDO': '10 SUL SERVICE',
    'JEAN CARLOS LOUREIRO BARBOSA': '10 SUL SERVICE',
    'JEFFERSON DE SOUZA MONTEIRO': '10 SUL SERVICE',
    'JOAO MACHADO FERNANDES': '10 SUL SERVICE',
    'JOCELI LIRIO DOS SANTOS': '10 SUL SERVICE',
    'JORDAN DAS VIRGENS RIBEIRO': '10 SUL SERVICE',
    'JOSE ANGEL LARA MATUTE': '10 SUL SERVICE',
    'JOSE ANTONIO DA SILVA ROSA': '10 SUL SERVICE',
    'JOSE RICARDO SANTOS': '10 SUL SERVICE',
    'JULIANO DOS SANTOS DIOGO': '10 SUL SERVICE',
    'JULIO PAES SOUZA': '10 SUL SERVICE',
    'JURANDIR FERREIRA NUNES': '10 SUL SERVICE',
    'KAROLINA VAZ PEREIRA': '10 SUL SERVICE',
    'KELVIN ALEXANDRE RAMOS': '10 SUL SERVICE',
    'KELVIN CHAGAS SANTOS': '10 SUL SERVICE',
    'KENNEDY SANTOS DE JESUS': '10 SUL SERVICE',
    'KIERLEN ALMEIDA DOS SANTOS': '10 SUL SERVICE',
    'LEONARDO SANTOS MOURA': '10 SUL SERVICE',
    'LHESLEY GOMES DE OLIVEIRA': '10 SUL SERVICE',
    'LUAN GUIDOTI LIMA': '10 SUL SERVICE',
    'LUCAS AZEVEDO RUFINO': '10 SUL SERVICE',
    'LUCAS CORREA SA SILVA': '10 SUL SERVICE',
    'LUCAS DE SOUZA GOMES': '10 SUL SERVICE',
    'LUZINETE MONTEIRO CRUZ': '10 SUL SERVICE',
    'MAIKO JHONATAN MARTINS LISBOA': '10 SUL SERVICE',
    'MANOEL LUZ ALVES': '10 SUL PRESTADORA',
    'MARCELO DE OLIVEIRA': '10 SUL SERVICE',
    'MARCOS JACOB DE SOUZA': '10 SUL SERVICE',
    'MARCOS VINICIUS BENEDITO LEMOS': '10 SUL SERVICE',
    'MARLON PINHEIRO DE MATOS': '10 SUL SERVICE',
    'MATEUS GOMES BITI': '10 SUL SERVICE',
    'MATHEUS FERREIRA SANTUZZI': '10 SUL SERVICE',
    'MURILO GOMES CARVALHO': '10 SUL SERVICE',
    'OSNIR PASSOS GOMES': '10 SUL SERVICE',
    'PAULO CESAR DOS REIS': '10 SUL SERVICE',
    'PEDRO DE ASSIS JUNIOR': '10 SUL SERVICE',
    'PEDRO DE JESUS BARBOSA': '10 SUL SERVICE',
    'RAFAEL FRANCISCO DO NASCIMENTO SANTOS': '10 SUL SERVICE',
    'RAMON MUNIZ COSER': '10 SUL SERVICE',
    'REGINALDO RIBEIRO DA SILVA': '10 SUL SERVICE',
    'RENATO DOS SANTOS GONÇALVES': '10 SUL SERVICE',
    'RIAN ANTONIO FERNANDES VARGAS': '10 SUL SERVICE',
    'ROGERIO DA CONCEIÇÃO REBOUÇAS': '10 SUL PRESTADORA',
    'ROSIVELTON OLIVEIRA GOMES': '10 SUL SERVICE',
    'RUBENS BRAGANÇA DA SILVA': '10 SUL SERVICE',
    'RUBENS GUILHERME MARINS': '10 SUL SERVICE',
    'RUBENS ROCHA CRUZ': '10 SUL SERVICE',
    'SANTINHO PERONI': '10 SUL SERVICE',
    'SILAS PASSOS DE SOUSA': '10 SUL PRESTADORA',
    'SILVIO CARLOS SOUZA': '10 SUL SERVICE',
    'SOLIMAR NATALI': '10 SUL SERVICE',
    'TASSIO DOS SANTOS QUARESMA': '10 SUL SERVICE',
    'VALTEMI CORREIA DE OLIVEIRA': '10 SUL SERVICE',
    'VANDER MARCOS DE SOUZA': '10 SUL SERVICE',
    'VANILSON DE JESUS': '10 SUL SERVICE',
    'VICTOR MARCELINO RAMOS': '10 SUL SERVICE',
    'VINICIUS HENRIQUE SANTOS SILVA': '10 SUL SERVICE',
    'VINICIUS PINTO ROSA': '10 SUL SERVICE',
    'VITOR SANTOS SOUZA': '10 SUL SERVICE',
    'WAGNER HONORIO DE ALMEIDA': '10 SUL SERVICE',
    'WALLACE RODRIGUES DO NASCIMENTO': '10 SUL SERVICE',
    'WANDERSON SANTOS SOUZA': '10 SUL PRESTADORA',
    'WEBERSON CORDEIRO DOS SANTOS': '10 SUL SERVICE',
    'WENDRYEL PEREIRA AMORIM PAULUSCENA': '10 SUL SERVICE',
    'WENIO DA PURIFICAÇÃO RIBEIRO': '10 SUL SERVICE',
    'WESLEY BRAGA CABRAL': '10 SUL SERVICE',
    'WESLEY SOUZA DOS SANTOS': '10 SUL SERVICE',
}

STATUS_PADRAO = [
    {"codigo":"OK", "descricao":"PRESENÇA", "ordem":1, "ativo":True, "exige_observacao":False},
    {"codigo":"FO", "descricao":"FOLGA", "ordem":2, "ativo":True, "exige_observacao":False},
    {"codigo":"FA", "descricao":"FALTA", "ordem":3, "ativo":True, "exige_observacao":False},
    {"codigo":"A",  "descricao":"ATESTADO", "ordem":4, "ativo":True, "exige_observacao":False},
    {"codigo":"FE", "descricao":"FÉRIAS", "ordem":5, "ativo":True, "exige_observacao":False},
    {"codigo":"LB", "descricao":"LIBERADO", "ordem":6, "ativo":True, "exige_observacao":True},
    {"codigo":"COMP", "descricao":"COMPENSAÇÃO", "ordem":7, "ativo":True, "exige_observacao":True},
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

def _classificacao_colaborador(registro):
    """Classificação real da aba BaseFuncionário (STATUS: OPERACIONAL/OUTROS)."""
    nome = _nome_colaborador(registro).strip().upper()
    if nome in CLASSIFICACAO_REFERENCIA:
        return CLASSIFICACAO_REFERENCIA[nome]
    for campo in ("classificacao", "classificação", "tipo", "categoria", "grupo", "tipo_colaborador", "classificacao_colaborador", "status_operacional"):
        valor = str(registro.get(campo) or "").strip().upper()
        if valor in ("OPERACIONAL", "OUTROS"):
            return valor
    return "OUTROS"

def _empresa_colaborador(registro, visual=False):
    """Usa a empresa real da BaseFuncionário como referência sem alterar o cadastro no banco."""
    nome = _nome_colaborador(registro).strip().upper()
    empresa_banco = str(registro.get("empresa") or "").strip().upper()
    empresa = EMPRESA_REFERENCIA.get(nome, empresa_banco)
    if visual:
        return {
            "10 SUL SERVICE": "SERVICE",
            "10 SUL PRESTADORA": "PRESTADORA",
        }.get(empresa, empresa)
    return empresa

def sincronizar_seed():
    """Carrega no Supabase os colaboradores padrão quando a tabela estiver vazia."""
    existentes = sb("GET", "rh_colaboradores", "select=id&limit=1") or []
    if existentes:
        return

    payload = []
    for nome, funcao in SEED_COLABORADORES:
        payload.append({
            "colaborador": nome,
            "funcao": funcao or None,
            "empresa": "10 SUL",
            "status": "ATIVO",
            "ativo": True,
        })

    sb("POST", "rh_colaboradores", "", payload, "return=minimal")


def garantir_ocorrencias():
    for r in STATUS_PADRAO:
        try:
            sb("POST", "rh_ocorrencias", "on_conflict=codigo", r,
               "resolution=merge-duplicates,return=minimal")
        except Exception:
            # Compatibilidade com tabela sem ordem/exige_observacao.
            minimo = {k: r[k] for k in ("codigo", "descricao", "ativo")}
            sb("POST", "rh_ocorrencias", "on_conflict=codigo", minimo,
               "resolution=merge-duplicates,return=minimal")

def ler_colaboradores():
    rows = sb("GET", "rh_colaboradores", "select=*&ativo=eq.true") or []
    return sorted(rows, key=lambda r: _nome_colaborador(r).upper())


def cadastrar_colaborador(nome, funcao="", cracha="", empresa="10 SUL"):
    nome = str(nome or "").strip().upper()
    if not nome:
        raise ValueError("Informe o nome do colaborador.")

    existentes = sb(
        "GET",
        "rh_colaboradores",
        "select=id,colaborador&colaborador=eq." + urllib.parse.quote(nome)
    ) or []
    if existentes:
        raise ValueError("Este colaborador já está cadastrado.")

    payload = {
        "colaborador": nome,
        "funcao": str(funcao or "").strip().upper() or None,
        "cracha": str(cracha or "").strip() or None,
        "empresa": str(empresa or "10 SUL").strip().upper(),
        "status": "ATIVO",
        "ativo": True,
    }
    sb("POST", "rh_colaboradores", "", payload, "return=minimal")


def alterar_status_colaborador(colaborador_id, ativo, data_desligamento=None):
    """Ativa/desativa o colaborador preservando o histórico."""
    payload = {
        "ativo": bool(ativo),
        "status": "ATIVO" if ativo else "INATIVO",
        "data_desligamento": None if ativo else (
            data_desligamento.isoformat()
            if hasattr(data_desligamento, "isoformat")
            else str(data_desligamento)
        ),
    }
    sb(
        "PATCH",
        "rh_colaboradores",
        "id=eq." + urllib.parse.quote(str(colaborador_id)),
        payload,
        "return=minimal",
    )


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



def gerar_excel_frequencia(ano, mes, colaboradores, freq, ocorrencia_codigo_por_id):
    """Gera as abas BaseFuncionario e BaseFuncionário no padrão do fechamento mensal."""
    ano = int(ano)
    mes = int(mes)
    dias_mes = calendar.monthrange(ano, mes)[1]

    freq_por_chave = {}
    for r in freq:
        try:
            d = pd.to_datetime(r.get("data")).date()
            freq_por_chave[(int(r.get("colaborador_id")), d.day)] = ocorrencia_codigo_por_id.get(int(r.get("ocorrencia_id"))) if r.get("ocorrencia_id") is not None else ""
        except Exception:
            pass

    wb = Workbook()
    ws_res = wb.active
    ws_res.title = "BaseFuncionario"
    ws_base = wb.create_sheet("BaseFuncionário")

    # ---------- BaseFuncionário ----------
    cab = ["EMPRESA", "CRACHÁ", "COLABORADOR", "BONIFCAÇÃO", "STATUS", "FUNÇÃO", "LOCAL", "DESLIGAMENTO"]
    for c, valor in enumerate(cab, 1):
        ws_base.cell(3, c, valor)

    for dia in range(1, dias_mes + 1):
        col = 8 + dia
        ws_base.cell(3, col, date(ano, mes, dia))
        ws_base.cell(2, col, f'=TEXT({get_column_letter(col)}3,"ddd")')

    col_falta = 9 + dias_mes
    col_atestado = 10 + dias_mes
    ws_base.cell(3, col_falta, "FALTA")
    ws_base.cell(3, col_atestado, "ATESTADO")

    for idx, c in enumerate(colaboradores, start=4):
        cid = int(c["id"])
        empresa = _empresa_colaborador(c, visual=False)
        funcao = str(c.get("funcao") or c.get("funcao_padrao") or "").strip().upper()
        status_cad = str(c.get("status") or "ATIVO").strip().upper()
        ativo = bool(c.get("ativo", True))

        ws_base.cell(idx, 1, empresa)
        ws_base.cell(idx, 2, c.get("cracha") or "")
        ws_base.cell(idx, 3, _nome_colaborador(c))
        ws_base.cell(idx, 4, "OPERACIONAL")
        ws_base.cell(idx, 5, "OPERACIONAL" if ativo and status_cad != "INATIVO" else "INATIVO")
        ws_base.cell(idx, 6, funcao)
        ws_base.cell(idx, 7, str(c.get("local") or "CMC ARA"))
        ws_base.cell(idx, 8, "REGISTRO" if ativo else (c.get("data_desligamento") or "DESLIGAMENTO"))

        for dia in range(1, dias_mes + 1):
            ws_base.cell(idx, 8 + dia, freq_por_chave.get((cid, dia), ""))

        primeira = get_column_letter(9)
        ultima = get_column_letter(8 + dias_mes)
        ws_base.cell(idx, col_falta, f'=COUNTIF({primeira}{idx}:{ultima}{idx},"FA")')
        ws_base.cell(idx, col_atestado, f'=COUNTIF({primeira}{idx}:{ultima}{idx},"A")')

    # ---------- BaseFuncionario (resumo) ----------
    ws_res["C1"] = "Operacional"
    ws_res["B2"] = "Data"
    codigos_resumo = [
        (3, "OK", "Presentes"),
        (4, "A", "Atestado"),
        (5, "LP", "Licença Paternidade"),
        (6, "FE", "Férias"),
        (7, "DE", "Destra"),
        (8, "FA", "Falta"),
        (9, "FO", "Folga"),
    ]
    for linha, codigo, descricao in codigos_resumo:
        ws_res.cell(linha, 1, codigo)
        ws_res.cell(linha, 2, descricao)

    ultima_linha_base = max(130, 3 + len(colaboradores))
    for dia in range(1, dias_mes + 1):
        col_res = 2 + dia
        col_base = 8 + dia
        letra_res = get_column_letter(col_res)
        letra_base = get_column_letter(col_base)
        ws_res.cell(2, col_res, date(ano, mes, dia))
        for linha, _, _ in codigos_resumo:
            ws_res.cell(
                linha, col_res,
                f'=COUNTIFS(BaseFuncionário!$E$4:$E${ultima_linha_base},BaseFuncionario!$C$1,'
                f'BaseFuncionário!{letra_base}$4:{letra_base}${ultima_linha_base},BaseFuncionario!$A{linha})'
            )

    ws_res["B10"] = "HORA EXTRA"
    ws_res["B11"] = "08:00"
    ws_res["B13"] = "EQUIVALÊNCIA"
    ws_res["B14"] = "AUSÊNCIAS"
    ws_res["B15"] = "Total faltas após compe"
    ws_res["B17"] = "Descrição"
    ws_res["B18"] = "Qtd Frota"
    ws_res["B19"] = "M.O Ideal"
    ws_res["B20"] = "M.O Real"
    ws_res["B21"] = "Delta M.O"
    ws_res["B23"] = "EXCEDENTE"
    ws_res["B24"] = "FALTAS"

    for dia in range(1, dias_mes + 1):
        col = 2 + dia
        letra = get_column_letter(col)
        ws_res.cell(17, col, date(ano, mes, dia))
        ws_res.cell(11, col, f'={letra}3+{letra}4+{letra}8+{letra}9')
        ws_res.cell(12, col, f'={letra}4+{letra}8')
        ws_res.cell(13, col, 0)  # Hora extra ainda não é controlada neste Portal RH.
        ws_res.cell(14, col, f'={letra}4+{letra}8')
        ws_res.cell(15, col, f'=IF({letra}14=0,"",IF({letra}14<{letra}13,"",IF({letra}14>{letra}13,{letra}14-{letra}13,"")))')
        ws_res.cell(16, col, f'={letra}9+{letra}8+{letra}4+{letra}3')
        ws_res.cell(18, col, 202)
        ws_res.cell(19, col, f'={letra}18*0.47')
        ws_res.cell(20, col, f'=IF({letra}3+{letra}9+{letra}4+{letra}8>{letra}19,{letra}19,{letra}9+{letra}3+{letra}4+{letra}8)')
        ws_res.cell(21, col, f'=IF({letra}19-{letra}20>{letra}19,{letra}19,{letra}19-{letra}20)')
        ws_res.cell(22, col, f'={letra}19-{letra}20')
        ws_res.cell(23, col, f'=IF({letra}22>{letra}19,{letra}22-{letra}19,"")')
        ws_res.cell(24, col, f'=IF({letra}8>0,{letra}8,"")')

    # Formatação aproximada ao modelo de fechamento.
    azul = "1F4E78"
    azul_claro = "D9EAF7"
    cinza = "E7E6E6"
    branco = "FFFFFF"
    borda = Side(style="thin", color="B7B7B7")

    for ws in (ws_base, ws_res):
        ws.freeze_panes = "I4" if ws.title == "BaseFuncionário" else "C3"

    for cell in ws_base[3]:
        if cell.value is not None:
            cell.fill = PatternFill("solid", fgColor=azul)
            cell.font = Font(color=branco, bold=True)
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = Border(bottom=borda)
    for c in range(9, 9 + dias_mes):
        ws_base.cell(2, c).fill = PatternFill("solid", fgColor=azul_claro)
        ws_base.cell(2, c).alignment = Alignment(horizontal="center")
        ws_base.cell(3, c).number_format = "dd/mm"
        ws_base.column_dimensions[get_column_letter(c)].width = 6
    ws_base.column_dimensions["A"].width = 20
    ws_base.column_dimensions["B"].width = 12
    ws_base.column_dimensions["C"].width = 38
    ws_base.column_dimensions["D"].width = 16
    ws_base.column_dimensions["E"].width = 16
    ws_base.column_dimensions["F"].width = 28
    ws_base.column_dimensions["G"].width = 15
    ws_base.column_dimensions["H"].width = 16
    ws_base.column_dimensions[get_column_letter(col_falta)].width = 10
    ws_base.column_dimensions[get_column_letter(col_atestado)].width = 11

    for r in range(1, 25):
        for c in range(1, 3 + dias_mes):
            cell = ws_res.cell(r, c)
            if r in (2, 17):
                cell.fill = PatternFill("solid", fgColor=azul_claro)
                cell.font = Font(bold=True)
            if c >= 3 and r in (2, 17):
                cell.number_format = "dd/mm"
            cell.alignment = Alignment(horizontal="center", vertical="center")
    ws_res.column_dimensions["A"].width = 10
    ws_res.column_dimensions["B"].width = 25
    for c in range(3, 3 + dias_mes):
        ws_res.column_dimensions[get_column_letter(c)].width = 7

    saida = BytesIO()
    wb.save(saida)
    saida.seek(0)
    return saida.getvalue()

def salvar_frequencia(colaborador_id, dia, codigo, ocorrencia_id_por_codigo, observacao="", autorizado_por=""):
    codigo = str(codigo or "").strip().upper()
    ocorrencia_id = ocorrencia_id_por_codigo.get(codigo)
    if codigo and ocorrencia_id is None:
        raise ValueError(f"Ocorrência {codigo} não encontrada em rh_ocorrencias.")
    payload = {
        "colaborador_id": int(colaborador_id),
        "data": dia.isoformat(),
        "ocorrencia_id": ocorrencia_id,
        "observacao": str(observacao or "").strip() or None,
        "autorizado_por": str(autorizado_por or "").strip() or None,
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
ocorrencia_id_por_codigo = {str(x.get("codigo") or "").upper().strip(): int(x["id"]) for x in ocorrencias if x.get("codigo") and x.get("id") is not None}
ocorrencia_codigo_por_id = {v: k for k, v in ocorrencia_id_por_codigo.items()}
codigos = [str(x.get("codigo","")).upper().strip() for x in ocorrencias if x.get("codigo")]
codigos = list(dict.fromkeys(codigos))
if "" not in codigos:
    opcoes = [""] + codigos
else:
    opcoes = codigos

freq = ler_frequencia(int(ano), mes)

# Reserva o espaço do resumo no topo. Ele será preenchido depois da grade,
# usando inclusive os lançamentos que o RH acabou de selecionar e ainda não salvou.
resumo_topo = st.container()

mapa = {}
obs_mapa = {}
for r in freq:
    try:
        d = pd.to_datetime(r.get("data")).date()
        chave = (int(r.get("colaborador_id")), d.day)
        mapa[chave] = ocorrencia_codigo_por_id.get(int(r.get("ocorrencia_id")), "") if r.get("ocorrencia_id") is not None else ""
        obs_mapa[chave] = str(r.get("observacao") or "")
    except Exception:
        pass

# Filtro visual por classificação do colaborador. Não altera cadastro nem dados salvos.
_colaboradores_todos = list(colaboradores)
_filtro_status = st.selectbox(
    "Filtrar por STATUS",
    ["TODOS", "OPERACIONAL", "OUTROS"],
    index=0,
    key=f"rh_filtro_status_{int(ano)}_{mes}",
)
if _filtro_status == "TODOS":
    colaboradores = _colaboradores_todos
else:
    colaboradores = [
        c for c in _colaboradores_todos
        if _classificacao_colaborador(c) == _filtro_status
    ]

# Pequeno quadro de quantidade de colaboradores por função, obedecendo ao filtro.
_resumo_funcoes = (
    pd.DataFrame({"FUNÇÃO": [str(c.get("funcao") or c.get("funcao_padrao") or "SEM FUNÇÃO").strip() or "SEM FUNÇÃO" for c in colaboradores]})
    .value_counts("FUNÇÃO")
    .reset_index(name="QTD")
    .sort_values(["QTD", "FUNÇÃO"], ascending=[False, True])
    .reset_index(drop=True)
)
with st.expander("📊 Resumo por função", expanded=False):
    st.dataframe(_resumo_funcoes, use_container_width=False, hide_index=True)

linhas = []
ids = []
for c in colaboradores:
    cid = int(c["id"])
    ids.append(cid)
    row = {
        "COLABORADOR": _nome_colaborador(c),
        # Classificação usada na Média de Recebíveis. Apenas OPERACIONAL entra no cálculo.
        "STATUS": _classificacao_colaborador(c),
        "FUNÇÃO": str(c.get("funcao") or c.get("funcao_padrao") or ""),
        # Na grade usa a empresa real da BaseFuncionário e exibe o nome abreviado.
        "EMPRESA": _empresa_colaborador(c, visual=True),
    }
    for dia in range(1, ultimo_visivel + 1):
        row[f"{dia:02d}"] = mapa.get((cid, dia), "")
    linhas.append(row)

df = pd.DataFrame(linhas)
colunas_dia = [f"{d:02d}" for d in range(1, ultimo_visivel + 1)]

config = {
    "COLABORADOR": st.column_config.TextColumn("COLABORADOR", width="large", disabled=True),
    "STATUS": st.column_config.TextColumn("STATUS", width="small", disabled=True),
    "FUNÇÃO": st.column_config.TextColumn("FUNÇÃO", width="medium", disabled=True),
    "EMPRESA": st.column_config.TextColumn("EMPRESA", width="small", disabled=True),
}
for c in colunas_dia:
    config[c] = st.column_config.SelectboxColumn(c, options=opcoes, width="small", required=False)

# A grade usa um rascunho em session_state. Isso permite desfazer SOMENTE a célula
# LB/COMP quando o modal é fechado no X, sem perder outras alterações pendentes.
_periodo_key = f"{int(ano)}_{mes}"
_draft_key = f"rh_grade_draft_{_periodo_key}"
_nonce_key = f"rh_grade_nonce_{_periodo_key}"
if _nonce_key not in st.session_state:
    st.session_state[_nonce_key] = 0

# Se o modal foi fechado no X, o callback deixou uma solicitação de cancelamento.
_cancelar = st.session_state.pop("rh_cancelar_modal", None)
if _cancelar:
    _draft = st.session_state.get(_draft_key)
    if isinstance(_draft, pd.DataFrame):
        _draft = _draft.copy()
        _row = int(_cancelar["row"])
        _col = str(_cancelar["col"])
        # Volta exatamente ao valor que existia antes da seleção de LB/COMP.
        _draft.at[_row, _col] = _cancelar.get("antes", "")
        st.session_state[_draft_key] = _draft
    st.session_state.get("rh_observacoes_pendentes", {}).pop(_cancelar.get("obs_key", ""), None)
    st.session_state.get("rh_responsaveis_pendentes", {}).pop(_cancelar.get("obs_key", ""), None)
    _txt = _cancelar.get("modal_text_key")
    _resp = _cancelar.get("modal_resp_key")
    if _txt:
        st.session_state.pop(_txt, None)
    if _resp:
        st.session_state.pop(_resp, None)

# Fonte exibida pelo editor: rascunho atual ou a base salva.
# O fingerprint da base garante que, após F5/salvamento, o Supabase volte a ser
# a fonte de verdade. Assim, registro já persistido nunca perde a trava de edição.
import hashlib
_base_serializada = df.fillna("").astype(str).to_csv(index=False)
_base_fingerprint = hashlib.sha256(_base_serializada.encode("utf-8")).hexdigest()
_fp_key = f"rh_grade_base_fp_{_periodo_key}"
_base_editor = st.session_state.get(_draft_key)
if (
    not isinstance(_base_editor, pd.DataFrame)
    or list(_base_editor.columns) != list(df.columns)
    or len(_base_editor) != len(df)
    or st.session_state.get(_fp_key) != _base_fingerprint
):
    _base_editor = df.copy()
    st.session_state[_draft_key] = _base_editor.copy()
    st.session_state[_fp_key] = _base_fingerprint

editado = st.data_editor(
    _base_editor,
    use_container_width=True,
    hide_index=True,
    disabled=["COLABORADOR","STATUS","FUNÇÃO","EMPRESA"],
    column_config=config,
    key=f"rh_grade_{ano}_{mes}_{st.session_state[_nonce_key]}",
    height=min(820, 72 + max(1, len(df))*35),
)
# Mantém o que está visualmente na grade como rascunho oficial.
st.session_state[_draft_key] = editado.copy()

# Conta diretamente o que está aparecendo na grade, inclusive alterações ainda não salvas.
contagens = {"FA": 0, "A": 0, "FO": 0, "OK": 0, "LB": 0, "COMP": 0}
for coluna in colunas_dia:
    for valor in editado[coluna].tolist():
        codigo = str(valor or "").upper().strip()
        if codigo in contagens:
            contagens[codigo] += 1

# Média de Recebíveis — sempre considera TODOS os OPERACIONAIS, independentemente do filtro visual.
# Soma FO + FA + OK + A de todos os OPERACIONAIS em todos os dias até hoje e divide pelos dias transcorridos.
_codigos_recebiveis = {"FO", "FA", "OK", "A"}
_total_recebiveis = 0
# Mapa com o que está salvo; depois sobrepomos o que estiver visível/pendente na grade atual.
_mapa_media = dict(mapa)
for i, cid in enumerate(ids):
    for dia in range(1, ultimo_visivel + 1):
        _mapa_media[(cid, dia)] = str(editado.iloc[i][f"{dia:02d}"] or "").upper().strip()
for _c in _colaboradores_todos:
    if _classificacao_colaborador(_c) != "OPERACIONAL":
        continue
    _cid = int(_c["id"])
    for _dia in range(1, ultimo_visivel + 1):
        if str(_mapa_media.get((_cid, _dia), "") or "").upper().strip() in _codigos_recebiveis:
            _total_recebiveis += 1
_media_diaria = (_total_recebiveis / ultimo_visivel) if ultimo_visivel else 0

with resumo_topo:
    st.markdown("#### Resumo do mês")
    k1, k2, k3, k4, k5, k6, k7 = st.columns(7)
    k1.metric("Faltas", contagens["FA"])
    k2.metric("Atestados", contagens["A"])
    k3.metric("Folgas", contagens["FO"])
    k4.metric("Presenças", contagens["OK"])
    k5.metric("Liberados", contagens["LB"])
    k6.metric("Compensações", contagens["COMP"])
    k7.metric("Média de Recebíveis", f"{_media_diaria:.2f}".replace(".", ","))

# Exportação no mesmo padrão das abas BaseFuncionario e BaseFuncionário usadas no fechamento.
try:
    _excel_export = gerar_excel_frequencia(int(ano), mes, colaboradores, freq, ocorrencia_codigo_por_id)
    st.download_button(
        "📥 Exportar Excel — BaseFuncionario / BaseFuncionário",
        data=_excel_export,
        file_name=f"Frequencia_{int(ano)}_{mes:02d}_BaseFuncionario.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=False,
    )
except Exception as e:
    st.warning(f"Não foi possível preparar a exportação em Excel: {e}")

# Resultado do salvamento parcial: aviso em modal central, sem lista extensa na página.
_aviso_pendencias_key = f"rh_aviso_pendencias_{int(ano)}_{mes}"

@st.dialog("⚠️ Preenchimento pendente")
def modal_pendencias_salvamento(qtd_salvos, qtd_pendencias):
    st.success(f"{int(qtd_salvos)} lançamento(s) salvo(s) com sucesso.")
    st.markdown(
        f"Ainda existem **{int(qtd_pendencias)} célula(s) não preenchida(s)** "
        "até o dia atual."
    )
    st.caption("Você pode sair e retornar depois para concluir o preenchimento.")
    if st.button("Entendi", type="primary", use_container_width=True):
        st.session_state.pop(_aviso_pendencias_key, None)
        st.rerun()

aviso_pendencias = st.session_state.get(_aviso_pendencias_key)
if aviso_pendencias:
    _qtd_salvos = int(aviso_pendencias.get("salvos", 0))
    _qtd_pendencias = int(aviso_pendencias.get("qtd_pendencias", 0))
    if _qtd_pendencias > 0:
        modal_pendencias_salvamento(_qtd_salvos, _qtd_pendencias)
    else:
        st.session_state.pop(_aviso_pendencias_key, None)
        st.success(f"{_qtd_salvos} lançamento(s) salvo(s) com sucesso.")

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

    # Registros que já existem no Supabase são consolidados. Qualquer edição deles
    # exige a senha administrativa, inclusive após F5 ou em outro computador.
    SENHA_EDICAO_RH = "28266451"
    if "rh_edicoes_autorizadas" not in st.session_state:
        st.session_state.rh_edicoes_autorizadas = set()
    if "rh_motivos_edicao" not in st.session_state:
        st.session_state.rh_motivos_edicao = {}

    edicoes_salvas = []
    for _i, _cid, _dia, _antes, _depois in alteracoes:
        _chave_reg = f"{_cid}_{int(ano)}_{mes}_{_dia}"
        # 'antes' vem de df, que é reconstruído a partir de rh_frequencia.
        # Portanto, valor anterior preenchido = registro já persistido no Supabase.
        if str(_antes or "").strip() and _chave_reg not in st.session_state.rh_edicoes_autorizadas:
            edicoes_salvas.append((_i, _cid, _dia, _antes, _depois, _chave_reg))

    def _cancelar_edicao_salva():
        alvo = st.session_state.pop("rh_edicao_salva_alvo", None)
        if alvo:
            _draft = st.session_state.get(_draft_key)
            if isinstance(_draft, pd.DataFrame):
                _draft = _draft.copy()
                _draft.at[int(alvo["row"]), str(alvo["col"])] = alvo.get("antes", "")
                st.session_state[_draft_key] = _draft
            st.session_state[_nonce_key] = int(st.session_state.get(_nonce_key, 0)) + 1

    @st.dialog("🔒 Alteração de lançamento salvo", on_dismiss=_cancelar_edicao_salva)
    def modal_senha_edicao(i, cid, dia, antes, depois, chave_reg):
        nome = str(editado.iloc[i]["COLABORADOR"] or "")
        st.markdown(f"**{nome}**")
        st.caption(f"Dia {dia:02d} • {antes} → {depois or 'VAZIO'}")
        st.warning("Este lançamento já foi salvo. A alteração exige senha e motivo obrigatório.")
        senha = st.text_input("Senha de autorização *", type="password", key=f"senha_edicao_{chave_reg}")
        motivo_alt = st.text_area(
            "Motivo da alteração *",
            key=f"motivo_edicao_{chave_reg}",
            placeholder="Informe por que o lançamento salvo precisa ser alterado",
        )
        if st.button("Confirmar alteração", type="primary", use_container_width=True):
            if senha != SENHA_EDICAO_RH:
                st.error("Senha incorreta. A alteração não foi autorizada.")
            elif not motivo_alt.strip():
                st.error("Informe obrigatoriamente o motivo da alteração.")
            else:
                st.session_state.rh_edicoes_autorizadas.add(chave_reg)
                if "rh_motivos_edicao" not in st.session_state:
                    st.session_state.rh_motivos_edicao = {}
                st.session_state.rh_motivos_edicao[chave_reg] = motivo_alt.strip()
                st.session_state.pop("rh_edicao_salva_alvo", None)
                st.rerun()

    # A senha vem antes de qualquer outra confirmação. Fechar no X restaura o valor salvo.
    modal_senha_aberto = False
    if edicoes_salvas:
        _i, _cid, _dia, _antes, _depois, _chave_reg = edicoes_salvas[0]
        st.session_state.rh_edicao_salva_alvo = {
            "row": _i, "col": f"{_dia:02d}", "antes": _antes
        }
        modal_senha_edicao(_i, _cid, _dia, _antes, _depois, _chave_reg)
        modal_senha_aberto = True

    pendentes_obs = [(i, cid, d, a, n) for i, cid, d, a, n in alteracoes if n in ("LB", "COMP")]

    if "rh_observacoes_pendentes" not in st.session_state:
        st.session_state.rh_observacoes_pendentes = {}
    if "rh_responsaveis_pendentes" not in st.session_state:
        st.session_state.rh_responsaveis_pendentes = {}

    chaves_validas = {f"{cid}_{int(ano)}_{mes}_{dia}" for _, cid, dia, _, novo in pendentes_obs}
    for chave_salva in list(st.session_state.rh_observacoes_pendentes.keys()):
        if chave_salva not in chaves_validas:
            st.session_state.rh_observacoes_pendentes.pop(chave_salva, None)
            st.session_state.rh_responsaveis_pendentes.pop(chave_salva, None)

    def _fechou_modal_sem_confirmar():
        """X do modal = cancelamento. Nunca autoriza LB/COMP."""
        alvo = st.session_state.pop("rh_modal_alvo", None)
        if alvo:
            st.session_state.rh_cancelar_modal = alvo
            # Força recriação do data_editor para refletir imediatamente o valor desfeito.
            st.session_state[_nonce_key] = int(st.session_state.get(_nonce_key, 0)) + 1

    @st.dialog("Autorização obrigatória", on_dismiss=_fechou_modal_sem_confirmar)
    def modal_observacao(i, cid, dia, antes, codigo, nome, valor_atual=""):
        descricao = "LIBERADO (LB)" if codigo == "LB" else "COMPENSAÇÃO (COMP)"
        st.markdown(f"**{nome}**")
        st.caption(f"Dia {dia:02d} • {descricao}")
        chave = f"{cid}_{int(ano)}_{mes}_{dia}"
        modal_resp_key = f"modal_resp_{cid}_{ano}_{mes}_{dia}_{codigo}"
        modal_text_key = f"modal_obs_{cid}_{ano}_{mes}_{dia}_{codigo}"

        responsavel = st.text_input(
            "Responsável pela autorização *",
            value=str(st.session_state.rh_responsaveis_pendentes.get(chave, "")),
            key=modal_resp_key,
            placeholder="Informe quem autorizou a liberação/compensação",
        )
        observacao = st.text_area(
            "Observação *",
            value=str(st.session_state.rh_observacoes_pendentes.get(chave, valor_atual or "")),
            key=modal_text_key,
            placeholder="Informe obrigatoriamente o motivo deste lançamento.",
            height=130,
        )
        if st.button("Confirmar observação", type="primary", use_container_width=True):
            if not responsavel.strip():
                st.error("Informe obrigatoriamente o responsável pela autorização.")
            elif not observacao.strip():
                st.error("A observação é obrigatória para LB e COMP.")
            else:
                st.session_state.rh_responsaveis_pendentes[chave] = responsavel.strip()
                # Salva responsável + motivo em um único campo, preservando o banco atual.
                st.session_state.rh_observacoes_pendentes[chave] = observacao.strip()
                # SOMENTE este botão confirma. Retira o alvo para o callback do X não cancelar.
                st.session_state.pop("rh_modal_alvo", None)
                st.rerun()

    # Abre automaticamente o primeiro LB/COMP ainda não confirmado.
    modal_aberto = False
    for i, cid, dia, antes, depois in ([] if modal_senha_aberto else pendentes_obs):
        chave_sessao = f"{cid}_{int(ano)}_{mes}_{dia}"
        confirmado = (
            str(st.session_state.rh_observacoes_pendentes.get(chave_sessao, "")).strip()
            and str(st.session_state.rh_responsaveis_pendentes.get(chave_sessao, "")).strip()
        )
        if not confirmado:
            nome = str(editado.iloc[i]["COLABORADOR"])
            valor_anterior = obs_mapa.get((cid, dia), "")
            st.session_state.rh_modal_alvo = {
                "row": i,
                "col": f"{dia:02d}",
                "antes": antes,
                "obs_key": chave_sessao,
                "modal_text_key": f"modal_obs_{cid}_{ano}_{mes}_{dia}_{depois}",
                "modal_resp_key": f"modal_resp_{cid}_{ano}_{mes}_{dia}_{depois}",
            }
            modal_observacao(i, cid, dia, antes, depois, nome, valor_anterior)
            modal_aberto = True
            break

    observacoes = {}
    for _, cid, dia, _, depois in pendentes_obs:
        chave_sessao = f"{cid}_{int(ano)}_{mes}_{dia}"
        observacoes[(cid, dia)] = str(st.session_state.rh_observacoes_pendentes.get(chave_sessao, "")).strip()

    # Segurança dupla: LB/COMP só pode ser salvo se houver confirmação explícita
    # com responsável E observação.
    pode_salvar = True
    for _, cid, dia, _, _ in pendentes_obs:
        chave = f"{cid}_{int(ano)}_{mes}_{dia}"
        if not str(st.session_state.rh_responsaveis_pendentes.get(chave, "")).strip():
            pode_salvar = False
        if not str(st.session_state.rh_observacoes_pendentes.get(chave, "")).strip():
            pode_salvar = False

    if pendentes_obs and not pode_salvar and not modal_aberto:
        st.warning("LB e COMP só são permitidos após informar responsável e observação e clicar em Confirmar observação.")

    if st.button("💾 Salvar alterações", type="primary", disabled=(not pode_salvar) or bool(edicoes_salvas)):
        # Células vazias geram ALERTA, mas não bloqueiam o salvamento parcial.
        # Dias futuros não entram porque a grade contém somente até ultimo_visivel.
        celulas_vazias = []
        for i, cid in enumerate(ids):
            nome_colab = str(editado.iloc[i]["COLABORADOR"] or "").strip()
            empresa_colab = str(editado.iloc[i].get("EMPRESA", "") or "").strip()
            for dia_check in range(1, ultimo_visivel + 1):
                col_check = f"{dia_check:02d}"
                valor_check = str(editado.iloc[i][col_check] or "").strip()
                if not valor_check or valor_check.lower() in ("none", "nan"):
                    celulas_vazias.append({
                        "COLABORADOR": nome_colab,
                        "EMPRESA": empresa_colab,
                        "DIA": col_check,
                    })

        try:
            for i, cid, dia, antes, depois in alteracoes:
                data_dia = date(int(ano), mes, dia)
                if depois in ("LB", "COMP"):
                    chave = f"{cid}_{int(ano)}_{mes}_{dia}"
                    responsavel = str(st.session_state.rh_responsaveis_pendentes.get(chave, "")).strip()
                    obs = str(st.session_state.rh_observacoes_pendentes.get(chave, "")).strip()
                    if not responsavel or not obs:
                        raise ValueError("LB/COMP sem autorização confirmada. Operação bloqueada.")
                else:
                    responsavel = ""
                    obs = "" if antes in ("LB", "COMP") else obs_mapa.get((cid, dia), "")

                # Auditoria de alteração de registro já salvo: preserva o motivo no próprio
                # registro, sem exigir mudança de estrutura no Supabase.
                chave_ed = f"{cid}_{int(ano)}_{mes}_{dia}"
                motivo_ed = str(st.session_state.rh_motivos_edicao.get(chave_ed, "")).strip()
                if str(antes or "").strip() and antes != depois and motivo_ed:
                    trilha = f"ALTERAÇÃO {antes or 'VAZIO'} -> {depois or 'VAZIO'} | MOTIVO: {motivo_ed}"
                    obs = f"{obs} | {trilha}".strip(" |") if obs else trilha
                salvar_frequencia(cid, data_dia, depois, ocorrencia_id_por_codigo, obs, responsavel)

            for _, cid, dia, _, _ in pendentes_obs:
                chave = f"{cid}_{int(ano)}_{mes}_{dia}"
                st.session_state.rh_observacoes_pendentes.pop(chave, None)
                st.session_state.rh_responsaveis_pendentes.pop(chave, None)

            # A autorização vale somente para esta edição. Depois de salvar,
            # uma nova alteração do mesmo registro exigirá a senha novamente.
            for _, cid, dia, _, _ in alteracoes:
                st.session_state.rh_edicoes_autorizadas.discard(f"{cid}_{int(ano)}_{mes}_{dia}")
                st.session_state.rh_motivos_edicao.pop(f"{cid}_{int(ano)}_{mes}_{dia}", None)

            # Guarda o resultado para aparecer depois do rerun. O salvamento é permitido
            # mesmo com pendências; as células vazias permanecem para preenchimento posterior.
            st.session_state[_aviso_pendencias_key] = {
                "salvos": len(alteracoes),
                "qtd_pendencias": len(celulas_vazias),
            }
            st.session_state.pop(_draft_key, None)
            st.session_state[_nonce_key] = int(st.session_state.get(_nonce_key, 0)) + 1
            st.rerun()
        except Exception as e:
            st.error(f"Não foi possível salvar: {e}")

with st.expander("👥 Cadastro de colaboradores"):
    st.caption("Cadastre, desative ou reative colaboradores sem apagar o histórico de frequência.")

    with st.form("form_novo_colaborador", clear_on_submit=True):
        cc1, cc2 = st.columns(2)
        with cc1:
            novo_nome = st.text_input("Colaborador *")
            novo_cracha = st.text_input("Crachá")
        with cc2:
            nova_funcao = st.text_input("Função")
            nova_empresa = st.text_input("Empresa", value="10 SUL")

        incluir = st.form_submit_button("➕ Cadastrar colaborador", type="primary")
        if incluir:
            try:
                cadastrar_colaborador(novo_nome, nova_funcao, novo_cracha, nova_empresa)
                st.success("Colaborador cadastrado com sucesso.")
                st.rerun()
            except Exception as e:
                st.error(f"Não foi possível cadastrar: {e}")

    st.markdown("#### Gerenciar colaboradores")
    st.caption("Altere o status diretamente na tabela. Ao mudar para INATIVO, informe a data de desligamento e confirme.")

    mostrar_inativos = st.checkbox("Mostrar colaboradores inativos", value=False)

    # Para permitir reativação, quando marcado traz ativos e inativos.
    params_cadastro = "select=*"
    if not mostrar_inativos:
        params_cadastro += "&ativo=eq.true"
    todos_cadastro = sb("GET", "rh_colaboradores", params_cadastro) or []
    todos_cadastro = sorted(todos_cadastro, key=lambda r: _nome_colaborador(r).upper())

    if todos_cadastro:
        cadastro_df = pd.DataFrame(todos_cadastro)

        # Garante colunas usadas pela interface.
        if "status" not in cadastro_df.columns:
            cadastro_df["status"] = cadastro_df["ativo"].apply(lambda x: "ATIVO" if bool(x) else "INATIVO")
        cadastro_df["status"] = cadastro_df["status"].fillna("ATIVO").astype(str).str.upper()
        if "data_desligamento" not in cadastro_df.columns:
            cadastro_df["data_desligamento"] = None

        cols_editor = [c for c in [
            "id", "cracha", "colaborador", "funcao", "empresa",
            "status", "data_desligamento"
        ] if c in cadastro_df.columns]

        original_status = {
            str(r["id"]): str(r.get("status") or ("ATIVO" if r.get("ativo", True) else "INATIVO")).upper()
            for r in todos_cadastro
        }

        editado = st.data_editor(
            cadastro_df[cols_editor],
            use_container_width=True,
            hide_index=True,
            disabled=[c for c in cols_editor if c not in ("status", "data_desligamento")],
            column_config={
                "id": st.column_config.NumberColumn("ID"),
                "cracha": st.column_config.TextColumn("Crachá"),
                "colaborador": st.column_config.TextColumn("Colaborador"),
                "funcao": st.column_config.TextColumn("Função"),
                "empresa": st.column_config.TextColumn("Empresa"),
                "status": st.column_config.SelectboxColumn(
                    "Status",
                    options=["ATIVO", "INATIVO"],
                    required=True,
                ),
                "data_desligamento": st.column_config.DateColumn(
                    "Data de desligamento",
                    format="DD/MM/YYYY",
                ),
            },
            key="editor_colaboradores",
        )

        alteracoes = []
        erros = []
        for _, linha in editado.iterrows():
            cid = str(linha["id"])
            novo_status = str(linha.get("status") or "ATIVO").upper()
            status_antigo = original_status.get(cid, "ATIVO")
            if novo_status != status_antigo:
                data_desl = linha.get("data_desligamento")
                if novo_status == "INATIVO" and pd.isna(data_desl):
                    erros.append(str(linha.get("colaborador") or cid))
                else:
                    alteracoes.append((linha, novo_status))

        if erros:
            st.warning(
                "Informe a data de desligamento para: " + ", ".join(erros)
            )

        if alteracoes:
            if st.button("💾 Confirmar alteração de status", type="primary"):
                try:
                    for linha, novo_status in alteracoes:
                        ativo_novo = novo_status == "ATIVO"
                        data_desl = None if ativo_novo else linha.get("data_desligamento")
                        alterar_status_colaborador(linha["id"], ativo_novo, data_desl)
                    st.success("Status atualizado com sucesso.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Não foi possível atualizar o status: {e}")
    else:
        st.info("Nenhum colaborador encontrado para o filtro selecionado.")

with st.expander("⚙️ Cadastro de ocorrências"):
    st.caption("Esses códigos alimentam as opções disponíveis na grade.")
    st.dataframe(pd.DataFrame(ocorrencias), use_container_width=True, hide_index=True)


st.markdown("#### 📝 Observações de LB / COMP")
registros_obs = []
nomes_por_id = {int(c["id"]): _nome_colaborador(c) for c in colaboradores}
for r in freq:
    codigo = ocorrencia_codigo_por_id.get(int(r.get("ocorrencia_id")), "") if r.get("ocorrencia_id") is not None else ""
    observacao = str(r.get("observacao") or "").strip()
    if codigo in ("LB", "COMP") and observacao:
        try:
            data_reg = pd.to_datetime(r.get("data")).strftime("%d/%m/%Y")
        except Exception:
            data_reg = str(r.get("data") or "")
        registros_obs.append({
            "DATA": data_reg,
            "COLABORADOR": nomes_por_id.get(int(r.get("colaborador_id")), str(r.get("colaborador_id") or "")),
            "TIPO": codigo,
            "OBSERVAÇÃO": observacao,
        })

if registros_obs:
    st.dataframe(pd.DataFrame(registros_obs), use_container_width=True, hide_index=True)
else:
    st.caption("Nenhuma observação de LB/COMP registrada neste mês.")

st.caption("Desenvolvido para 10 Sul • Portal RH")
