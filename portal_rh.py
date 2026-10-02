import os
import json
import calendar
import urllib.request
import urllib.error
import urllib.parse
import hashlib
from datetime import datetime, date
from io import BytesIO

import pandas as pd
import streamlit as st
import altair as alt

try:
    from st_keyup import st_keyup
except ImportError:
    st_keyup = None
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo

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
SALARIO_REFERENCIA = {
    'ABRAAO OLIVEIRA DOS SANTOS': 3230.83,
    'ADAIR DO ROSARIO FERNANDES': 3119.42,
    'ADRIANO DOS SANTOS RIBEIRO': 2610.01,
    'ALESSANDRO ROCHA MOREIRA': 2770.37,
    'ANDRE GUIMARAES CORDEIRO': 6300.00,
    'ANDRE MIRANDA': 3119.42,
    'ARTHUR DOS SANTOS DA SILVA': 2117.79,
    'BRUNO HENRIQUE ARAUJO DA SILVA': 2500.00,
    'CARLOS ALBERTO DE SOUZA': 1870.52,
    'CARLOS HENRIQUE DE SOUZA TESTA DA SILVA': 2904.93,
    'CARLOS HENRIQUE NASCIMENTO': 3119.42,
    'CLAUDINEI AMANCIO JACOB': 1870.52,
    'CLEBER FRAGA BANDEIRA': 3230.83,
    'CLEBES SANTANA SANTOS': 2904.93,
    'CLEISIMAR NICANOR ESPERANCA': 2610.01,
    'CRISTIANO QUIRINO MORAES': 2473.87,
    'DANIEL BERTOLDO RODRIGUES': 2610.01,
    'DEIVISON BUENO CUNHA': 3230.83,
    'DEMETRIO CORDEIRO FLORINDO': 2610.01,
    'DENISIO MAGELA ALVES': 3230.83,
    'DIEGO ATHAYDE SCARDUA': 2216.28,
    'DIEGO MONTEIRO SILVA': 2354.81,
    'DIMAS DA SILVA MUNIZ': 3230.83,
    'DIONES ALVARENGA DOS SANTOS': 3230.83,
    'DIONIS GABRIEL CAMPOS': 2216.28,
    'DOUGLAS PEREIRA SANTOS': 2770.37,
    'EDCARLOS FRANCISCO DA SILVA': 3230.83,
    'EDRICK OLIVIERA ALMEIDA': 1870.52,
    'ELIAS DA SILVA JOVENCIO': 2400.00,
    'ELOISIO COVRE': 2940.00,
    'ENOC DE OLIVEIRA SANTOS': 3692.50,
    'EVANDRO DOS SANTOS OLIVEIRA JUNIOR': 5275.00,
    'EZEQUIEL ALVES VIEIRA': 2904.93,
    'EZEQUIEL DE MOURA PAIXÃO': 2473.87,
    'EZEQUIEL SANTOS HERCULANO': 3400.00,
    'FABIO CANDEIAS SOUZA': 3230.83,
    'FABIO CORDEIRO DOS SANTOS': 2610.01,
    'FABIO OLIVEIRA SILVA NOGUEIRA': 3230.83,
    'FABRICIO FANCHIOTTI': 5580.95,
    'FELIPE REIS DE SOUZA': 2216.28,
    'FERNANDO FERNANDES COSTA': 3047.39,
    'GABRIEL DA VITÓRIA ALVARENGA': 3748.30,
    'GABRYEL MACIEL PEREIRA': 3230.83,
    'GEAN PEREIRA DE CARLI': 1700.00,
    'GILMAR SILVA OLIVEIRA': 3165.00,
    'GILSON MATHIAS DO NASCIMENTO': 3119.42,
    'HELDER DA SILVA ROQUE': 2216.28,
    'HORACIO GUILHERME DE SOUZA ALMEIDA': 1870.52,
    'JARDEL SABINO FELIZARDO': 2610.01,
    'JEAN CARLOS LOUREIRO BARBOSA': 3230.83,
    'JEFFERSON DE SOUZA MONTEIRO': 3230.83,
    'JOAO MACHADO FERNANDES': 1700.00,
    'JOCELI LIRIO DOS SANTOS': 2610.01,
    'JORDAN DAS VIRGENS RIBEIRO': 1870.52,
    'JOSE ANGEL LARA MATUTE': 3119.42,
    'JOSE ANTONIO DA SILVA ROSA': 3119.42,
    'JOSE RICARDO SANTOS': 1870.52,
    'JULIANO DOS SANTOS DIOGO': 3230.83,
    'JULIO PAES SOUZA': 2216.28,
    'JURANDIR FERREIRA NUNES': 2610.01,
    'KAROLINA VAZ PEREIRA': 3798.00,
    'KELVIN CHAGAS SANTOS': 2904.93,
    'KENNEDY SANTOS DE JESUS': 1779.08,
    'KIERLEN ALMEIDA DOS SANTOS': 2216.28,
    'LEONARDO SANTOS MOURA': 3230.83,
    'LHESLEY GOMES DE OLIVEIRA': 3230.83,
    'LUAN GUIDOTI LIMA': 3230.83,
    'LUCAS AZEVEDO RUFINO': 2216.28,
    'LUCAS CORREA SA SILVA': 2216.28,
    'LUCAS DE SOUZA GOMES': 3119.42,
    'LUZINETE MONTEIRO CRUZ': 2354.81,
    'MAIKO JHONATAN MARTINS LISBOA': 3230.83,
    'MARCELO DE OLIVEIRA': 1870.52,
    'MARCOS JACOB DE SOUZA': 2673.79,
    'MARCOS VINICIUS BENEDITO LEMOS': 3500.00,
    'MARLON PINHEIRO DE MATOS': 2216.28,
    'MATEUS GOMES BITI': 3230.83,
    'MATHEUS FERREIRA SANTUZZI': 2216.28,
    'MURILO GOMES CARVALHO': 1870.52,
    'OSNIR PASSOS GOMES': 5200.00,
    'PAULO CESAR DOS REIS': 3230.83,
    'PEDRO DE ASSIS JUNIOR': 3119.42,
    'PEDRO DE JESUS BARBOSA': 3119.42,
    'RAFAEL FRANCISCO DO NASCIMENTO SANTOS': 3230.83,
    'RAMON MUNIZ COSER': 1700.00,
    'REGINALDO RIBEIRO DA SILVA': 3119.42,
    'RENATO DOS SANTOS GONÇALVES': 3230.83,
    'RIAN ANTONIO FERNANDES VARGAS': 1700.00,
    'ROGERIO DA CONCEIÇÃO REBOUÇAS': 3119.42,
    'ROSIVELTON OLIVEIRA GOMES': 3692.50,
    'RUBENS GUILHERME MARINS': 7798.56,
    'RUBENS ROCHA CRUZ': 2904.93,
    'SANTINHO PERONI': 2904.93,
    'SILVIO CARLOS SOUZA': 2610.01,
    'SOLIMAR NATALI': 3119.42,
    'TASSIO DOS SANTOS QUARESMA': 2610.01,
    'VALTEMI CORREIA DE OLIVEIRA': 3119.42,
    'VANDER MARCOS DE SOUZA': 2940.00,
    'VANILSON DE JESUS': 2904.93,
    'VICTOR MARCELINO RAMOS': 1870.52,
    'VINICIUS HENRIQUE SANTOS SILVA': 2473.87,
    'VINICIUS PINTO ROSA': 2473.87,
    'VITOR SANTOS SOUZA': 3119.42,
    'WAGNER HONORIO DE ALMEIDA': 7798.56,
    'WANDERSON SANTOS SOUZA': 2647.42,
    'WALLACE RODRIGUES DO NASCIMENTO': 2473.87,
    'WEBERSON CORDEIRO DOS SANTOS': 3119.42,
    'WENDRYEL PEREIRA AMORIM PAULUSCENA': 2610.01,
    'WENIO DA PURIFICAÇÃO RIBEIRO': 2610.01,
    'WESLEY BRAGA CABRAL': 3230.83,
    'WESLEY SOUZA DOS SANTOS': 3230.83,
    'FRANCINY GIACOMIN ALBORGHETE MARTINELI': 3376.00,
}


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
            "salario_base": SALARIO_REFERENCIA.get(nome),
        })

    sb("POST", "rh_colaboradores", "", payload, "return=minimal")


def sincronizar_salarios_referencia():
    """Preenche salário-base a partir da Relação de Empregados - Ativos usada na implantação."""
    if st.session_state.get("rh_salarios_ref_sincronizados"):
        return
    try:
        rows = sb("GET", "rh_colaboradores", "select=id,colaborador,salario_base") or []
        for r in rows:
            nome = _nome_colaborador(r).strip().upper()
            salario = SALARIO_REFERENCIA.get(nome)
            atual = r.get("salario_base")
            if salario is not None and (atual is None or str(atual).strip() == ""):
                sb("PATCH", "rh_colaboradores", "id=eq." + urllib.parse.quote(str(r["id"])), {"salario_base": salario}, "return=minimal")
        st.session_state["rh_salarios_ref_sincronizados"] = True
    except Exception as e:
        st.session_state["rh_salarios_ref_erro"] = str(e)


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


def cadastrar_colaborador(nome, funcao="", cracha="", empresa="10 SUL", salario_base=None, frente=None, destra=None, equipe_revisao=None):
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
        "salario_base": salario_base,
        "frente": str(frente or "").strip().upper() or None,
        "destra": str(destra or "").strip() or None,
        "equipe_revisao": str(equipe_revisao or "").strip().upper() or None,
    }
    sb("POST", "rh_colaboradores", "", payload, "return=minimal")


def alterar_status_colaborador(colaborador_id, ativo, data_desligamento=None):
    """Atualiza status e/ou data de desligamento preservando o histórico.

    A data de desligamento é independente do campo ATIVO/INATIVO: se existir,
    ela prevalece na grade de frequência e gera DEM a partir do dia seguinte.
    """
    _data = None
    if data_desligamento is not None and not pd.isna(data_desligamento):
        _data = (
            data_desligamento.isoformat()
            if hasattr(data_desligamento, "isoformat")
            else str(data_desligamento)
        )
    payload = {
        "ativo": bool(ativo),
        "status": "ATIVO" if ativo else "INATIVO",
        "data_desligamento": _data,
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
    # PENDENTE não é ocorrência: significa ausência de lançamento.
    # Se um registro salvo voltar para PENDENTE, removemos a linha do banco.
    if not codigo:
        params = (
            "colaborador_id=eq." + urllib.parse.quote(str(int(colaborador_id))) +
            "&data=eq." + urllib.parse.quote(dia.isoformat())
        )
        sb("DELETE", "rh_frequencia", params)
        return
    ocorrencia_id = ocorrencia_id_por_codigo.get(codigo)
    if ocorrencia_id is None:
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



# ==========================================================
# FICHA DO COLABORADOR / OCORRÊNCIAS INDIVIDUAIS
# ==========================================================
TIPOS_OCORRENCIA_COLABORADOR = [
    "ADVERTÊNCIA VERBAL",
    "ADVERTÊNCIA ESCRITA",
    "SUSPENSÃO",
    "ORIENTAÇÃO",
    "ELOGIO / RECONHECIMENTO",
    "SEGURANÇA",
    "QUALIDADE",
    "COMPORTAMENTO",
    "OUTROS",
]

def ler_ocorrencias_colaborador(colaborador_id):
    params = (
        "select=id,colaborador_id,data,tipo,descricao,registrado_por,criado_em"
        f"&colaborador_id=eq.{int(colaborador_id)}"
        "&order=data.desc,criado_em.desc"
    )
    return sb("GET", "rh_colaborador_ocorrencias", params) or []


def salvar_ocorrencia_colaborador(colaborador_id, data_ocorrencia, tipo, descricao, registrado_por):
    descricao = str(descricao or "").strip()
    registrado_por = str(registrado_por or "").strip()
    if not descricao:
        raise ValueError("Informe a descrição/motivo da ocorrência.")
    if not registrado_por:
        raise ValueError("Informe quem está registrando a ocorrência.")
    payload = {
        "colaborador_id": int(colaborador_id),
        "data": data_ocorrencia.isoformat(),
        "tipo": str(tipo or "OUTROS").strip().upper(),
        "descricao": descricao,
        "registrado_por": registrado_por.upper(),
    }
    sb("POST", "rh_colaborador_ocorrencias", "", payload, "return=minimal")


def _tabela_ocorrencias_disponivel():
    try:
        sb("GET", "rh_colaborador_ocorrencias", "select=id&limit=1")
        return True
    except Exception:
        return False

# ==========================================================
# ACESSO POR PERFIL + CONTROLE DE DNA
# ==========================================================

def _hash_senha(valor):
    return hashlib.sha256(str(valor or "").encode("utf-8")).hexdigest()

def autenticar_usuario(usuario, senha):
    usuario = str(usuario or "").strip().lower()
    if not usuario or not senha:
        return None
    params = "select=id,usuario,nome,perfil,ativo,senha_hash,trocar_senha&usuario=eq." + urllib.parse.quote(usuario) + "&limit=1"
    regs = sb("GET", "rh_usuarios", params) or []
    if not regs:
        return None
    r = regs[0]
    if not bool(r.get("ativo", True)):
        return None
    if str(r.get("senha_hash") or "") != _hash_senha(senha):
        return None
    return {"id": r.get("id"), "usuario": r.get("usuario"), "nome": r.get("nome") or r.get("usuario"), "perfil": str(r.get("perfil") or "").upper(), "trocar_senha": bool(r.get("trocar_senha", False))}

def alterar_senha_usuario(usuario_id, senha_atual, nova_senha):
    usr = st.session_state.get("usuario_logado") or {}
    usuario = str(usr.get("usuario") or "").strip().lower()
    if not autenticar_usuario(usuario, senha_atual):
        raise ValueError("A senha atual está incorreta.")
    nova_senha = str(nova_senha or "")
    if len(nova_senha) < 8:
        raise ValueError("A nova senha deve ter pelo menos 8 caracteres.")
    payload = {"senha_hash": _hash_senha(nova_senha), "trocar_senha": False}
    sb("PATCH", "rh_usuarios", "id=eq." + str(int(usuario_id)), payload, "return=minimal")

def modal_alterar_senha(obrigatoria=False):
    titulo = "🔐 Crie sua nova senha" if obrigatoria else "🔐 Alterar senha"
    st.markdown(f"### {titulo}")
    if obrigatoria:
        st.info("Este é seu primeiro acesso. Para continuar, substitua a senha inicial por uma senha pessoal.")
    with st.form("form_troca_senha_portal", clear_on_submit=False):
        atual = st.text_input("Senha atual", type="password")
        nova = st.text_input("Nova senha", type="password", help="Mínimo de 8 caracteres.")
        confirma = st.text_input("Confirmar nova senha", type="password")
        salvar = st.form_submit_button("Salvar nova senha", type="primary", use_container_width=True)
    if salvar:
        if nova != confirma:
            st.error("A confirmação não confere com a nova senha.")
        elif nova == atual:
            st.error("A nova senha deve ser diferente da senha atual.")
        else:
            try:
                usr = st.session_state.get("usuario_logado") or {}
                alterar_senha_usuario(usr.get("id"), atual, nova)
                st.session_state["usuario_logado"]["trocar_senha"] = False
                st.session_state.pop("abrir_troca_senha", None)
                st.success("Senha alterada com sucesso.")
                st.rerun()
            except Exception as e:
                st.error(str(e))

def competencia_dna_fechada(ano, mes, hoje_ref=None):
    hoje_ref = hoje_ref or date.today()
    limite = date(int(ano) + 1, 1, 10) if int(mes) == 12 else date(int(ano), int(mes) + 1, 10)
    return hoje_ref >= limite, limite

def ler_dna_mensal(ano, mes):
    competencia = f"{int(ano):04d}-{int(mes):02d}-01"
    params = "select=*&competencia=eq." + urllib.parse.quote(competencia)
    return sb("GET", "rh_dna_mensal", params) or []

def salvar_dna_mensal(colaborador_id, ano, mes, quantidade, atualizado_por):
    competencia = f"{int(ano):04d}-{int(mes):02d}-01"
    payload = {
        "colaborador_id": int(colaborador_id),
        "competencia": competencia,
        "quantidade": max(0, int(quantidade or 0)),
        "atualizado_por": str(atualizado_por or "").strip().upper(),
        "atualizado_em": datetime.now().isoformat(timespec="seconds"),
    }
    sb("POST", "rh_dna_mensal", "on_conflict=colaborador_id,competencia", payload, "resolution=merge-duplicates,return=minimal")

def tela_login():
    st.markdown("<div style='height:8vh'></div>", unsafe_allow_html=True)
    c1,c2,c3=st.columns([1,1.15,1])
    with c2:
        st.markdown("## 👥 Portal RH — Aracruz")
        st.caption("10 Sul • Acesso restrito")
        with st.form("form_login_portal"):
            u=st.text_input("Usuário")
            pw=st.text_input("Senha", type="password")
            entrar=st.form_submit_button("Entrar", type="primary", use_container_width=True)
        if entrar:
            try:
                dados=autenticar_usuario(u,pw)
                if dados:
                    st.session_state["usuario_logado"]=dados
                    st.rerun()
                else:
                    st.error("Usuário ou senha inválidos.")
            except Exception as e:
                st.error("Não foi possível validar o acesso. Execute o SQL de usuários desta versão no Supabase.")
                st.caption(str(e))

def cabecalho_sessao(mostrar_ajuda=False):
    usr = st.session_state.get("usuario_logado") or {}
    perfil = str(usr.get("perfil") or "").upper()
    nome_perfil = {
        "RH": "RH",
        "SEGURANCA": "Segurança do Trabalho",
        "ADMIN": "Administrador",
    }.get(perfil, perfil or "Usuário")

    # Barra discreta dentro da área útil da página, evitando ficar escondida
    # sob a barra superior do Streamlit.
    a, b, c, d = st.columns([6.4, 1.55, 0.95, 0.95], vertical_alignment="center")
    with a:
        st.caption(f"👤 {nome_perfil}")
    with b:
        if st.button("🔐 Alterar senha", key="abrir_alterar_senha", use_container_width=True):
            st.session_state["abrir_troca_senha"] = True
    with c:
        if st.button("🚪 Sair", key="logout_portal", use_container_width=True):
            st.session_state.pop("usuario_logado", None)
            st.session_state.pop("abrir_troca_senha", None)
            st.rerun()
    with d:
        if mostrar_ajuda:
            if st.button("❔ Ajuda", key="btn_ajuda_portal", help="Ver explicação desta tela", use_container_width=True):
                abrir_ajuda_portal()

    if st.session_state.get("abrir_troca_senha"):
        with st.expander("🔐 Alteração de senha", expanded=True):
            modal_alterar_senha(False)


# ==========================================================
# REGRAS DE GRATIFICAÇÃO
# ==========================================================
def ler_regras_gratificacao():
    return sb("GET", "rh_regras_gratificacao", "select=*&order=id.asc") or []


def salvar_regra_gratificacao(regra_id, dados, atualizado_por):
    payload = dict(dados)
    payload["atualizado_por"] = str(atualizado_por or "").strip() or None
    payload["atualizado_em"] = datetime.now().isoformat(timespec="seconds")
    sb("PATCH", "rh_regras_gratificacao", f"id=eq.{int(regra_id)}", payload, "return=minimal")


def tela_regras_gratificacao():
    usr = st.session_state.get("usuario_logado") or {}
    st.markdown("### 💰 Cadastro de Regras de Gratificação")
    st.caption("As regras abaixo ficam salvas no banco e podem ser alteradas pelo RH/Administrador. FABRICAÇÃO será configurada em uma etapa separada.")
    try:
        regras = ler_regras_gratificacao()
    except Exception as e:
        st.error("A estrutura das regras ainda não está disponível. Execute o SQL desta versão no Supabase.")
        st.caption(str(e))
        return
    if not regras:
        st.warning("Nenhuma regra cadastrada. Execute o SQL desta versão no Supabase para carregar as regras iniciais.")
        return

    rotulos = {"REVISAO": "REVISÃO", "ITR_DEMAIS": "ITR E DEMAIS FRENTES"}
    for r in regras:
        codigo = str(r.get("codigo") or "")
        titulo = rotulos.get(codigo, str(r.get("nome") or codigo))
        with st.container(border=True):
            st.markdown(f"#### {titulo}")
            if codigo == "REVISAO":
                st.caption("Bonificação integral calculada sobre o salário-base do colaborador.")
                c1,c2,c3 = st.columns(3)
                pct_integral = c1.number_input("Bonificação integral (% do salário)", min_value=0.0, max_value=100.0, value=float(r.get("percentual_salario") or 35), step=0.5, key=f"rg_pct_{r['id']}")
                peso_abs = c2.number_input("Peso Absenteísmo (%)", min_value=0.0, max_value=100.0, value=float(r.get("peso_absenteismo") or 20), step=1.0, key=f"rg_abs_{r['id']}")
                peso_tempo = c3.number_input("Peso Tempo de entrega (%)", min_value=0.0, max_value=100.0, value=float(r.get("peso_tempo_entrega") or 80), step=1.0, key=f"rg_tmp_{r['id']}")
                c4,c5,c6 = st.columns(3)
                desc_1_at = c4.number_input("1 dia de atestado — desconto no Absenteísmo (R$)", min_value=0.0, value=float(r.get("desconto_1_atestado_valor") or 100), step=10.0, key=f"rg_atv_{r['id']}")
                atest_zera = c5.number_input("Dias de atestado para zerar Absenteísmo", min_value=1, value=int(r.get("atestados_zera_categoria") or 2), step=1, key=f"rg_atz_{r['id']}")
                dna_min = c6.number_input("DNA mínimo no mês", min_value=0, value=int(r.get("dna_minimo") or 2), step=1, key=f"rg_dna_{r['id']}")
                st.markdown("**Faixas do Tempo de Entrega — percentual da parcela de Tempo**")
                t1,t2,t3,t4 = st.columns(4)
                tempo_12 = t1.number_input("Até 12h (%)", min_value=0.0, max_value=100.0, value=float(r.get("tempo_ate_12_percentual") if r.get("tempo_ate_12_percentual") is not None else 100), step=5.0, key=f"rg_t12_{r['id']}")
                tempo_16 = t2.number_input("> 12h até 16h (%)", min_value=0.0, max_value=100.0, value=float(r.get("tempo_ate_16_percentual") if r.get("tempo_ate_16_percentual") is not None else 60), step=5.0, key=f"rg_t16_{r['id']}")
                tempo_24 = t3.number_input("> 16h até 24h (%)", min_value=0.0, max_value=100.0, value=float(r.get("tempo_ate_24_percentual") if r.get("tempo_ate_24_percentual") is not None else 40), step=5.0, key=f"rg_t24_{r['id']}")
                tempo_acima = t4.number_input("> 24h (%)", min_value=0.0, max_value=100.0, value=float(r.get("tempo_acima_24_percentual") if r.get("tempo_acima_24_percentual") is not None else 0), step=5.0, key=f"rg_tac_{r['id']}")
                st.info("FALTA = zera a gratificação inteira • Desvio comportamental/advertência = zera a gratificação inteira • DNA abaixo do mínimo = zera a gratificação inteira.")
                if abs((peso_abs + peso_tempo) - 100) > 0.001:
                    st.warning("Absenteísmo + Tempo de entrega deve totalizar 100%.")
                dados = {
                    "percentual_salario": pct_integral, "valor_fixo": None,
                    "peso_absenteismo": peso_abs, "peso_tempo_entrega": peso_tempo,
                    "falta_zera_tudo": True, "desconto_1_atestado_valor": desc_1_at,
                    "desconto_1_atestado_percentual": None, "atestados_zera_categoria": int(atest_zera),
                    "atestados_zera_tudo": None, "dna_minimo": int(dna_min),
                    "dna_abaixo_minimo_zera": True, "desvio_comportamental_zera": True,
                    "atraso_habilitado": False,
                    "tempo_ate_12_percentual": tempo_12,
                    "tempo_ate_16_percentual": tempo_16,
                    "tempo_ate_24_percentual": tempo_24,
                    "tempo_acima_24_percentual": tempo_acima,
                }
            else:
                st.caption("Regra-base para ITR, SOS, CNP, BORRACHARIA, CAPD e CRAVEJAMENTO. FABRICAÇÃO não entra nesta regra.")
                c1,c2,c3 = st.columns(3)
                valor = c1.number_input("Bonificação integral (R$)", min_value=0.0, value=float(r.get("valor_fixo") or 360), step=10.0, key=f"rg_vlr_{r['id']}")
                desc_at = c2.number_input("1 dia de atestado — desconto (%)", min_value=0.0, max_value=100.0, value=float(r.get("desconto_1_atestado_percentual") or 20), step=1.0, key=f"rg_atp_{r['id']}")
                atest_tudo = c3.number_input("Dias de atestado para zerar tudo", min_value=1, value=int(r.get("atestados_zera_tudo") or 2), step=1, key=f"rg_att_{r['id']}")
                c4,c5 = st.columns(2)
                dna_min = c4.number_input("DNA mínimo no mês", min_value=0, value=int(r.get("dna_minimo") or 2), step=1, key=f"rg_dna_{r['id']}")
                atraso_hab = c5.checkbox("Ativar regra de atraso acumulado", value=bool(r.get("atraso_habilitado", False)), key=f"rg_atraso_{r['id']}", help="Deixe desativado por enquanto. Depois vamos calcular automaticamente a soma dos atrasos.")
                limite_atraso = None
                if atraso_hab:
                    limite_atraso = st.number_input("Limite de atraso acumulado para zerar bônus (minutos)", min_value=0, value=int(r.get("limite_atraso_minutos") or 0), step=5, key=f"rg_atlim_{r['id']}")
                st.info("FALTA = zera tudo • Desvio comportamental/advertência = zera tudo • DNA abaixo do mínimo = zera tudo.")
                dados = {
                    "percentual_salario": None, "valor_fixo": valor,
                    "peso_absenteismo": None, "peso_tempo_entrega": None,
                    "falta_zera_tudo": True, "desconto_1_atestado_valor": None,
                    "desconto_1_atestado_percentual": desc_at, "atestados_zera_categoria": None,
                    "atestados_zera_tudo": int(atest_tudo), "dna_minimo": int(dna_min),
                    "dna_abaixo_minimo_zera": True, "desvio_comportamental_zera": True,
                    "atraso_habilitado": bool(atraso_hab), "limite_atraso_minutos": limite_atraso,
                }
            if st.button("💾 Salvar esta regra", type="primary", key=f"salvar_regra_{r['id']}"):
                if codigo == "REVISAO" and abs((peso_abs + peso_tempo) - 100) > 0.001:
                    st.error("Não foi salvo: os pesos de Absenteísmo e Tempo de entrega precisam totalizar 100%.")
                else:
                    try:
                        salvar_regra_gratificacao(r["id"], dados, usr.get("nome") or usr.get("usuario"))
                        st.success("Regra atualizada com sucesso.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Não foi possível salvar a regra: {e}")


# ==========================================================
# APURAÇÃO MENSAL DE GRATIFICAÇÃO
# ==========================================================
def ler_apuracao_gratificacao(ano, mes):
    try:
        return sb("GET", "rh_gratificacao_apuracao", f"select=*&ano=eq.{int(ano)}&mes=eq.{int(mes)}") or []
    except Exception:
        return []


def salvar_apuracao_manual(colaborador_id, ano, mes, equipe, media_horas, observacao, atualizado_por):
    payload = {
        "colaborador_id": int(colaborador_id), "ano": int(ano), "mes": int(mes),
        "equipe_revisao": str(equipe or "").strip() or None,
        "media_tempo_entrega_horas": None if media_horas in (None, "") else float(media_horas),
        "observacao": str(observacao or "").strip() or None,
        "atualizado_por": str(atualizado_por or "").strip() or None,
        "atualizado_em": datetime.now().isoformat(timespec="seconds"),
    }
    sb("POST", "rh_gratificacao_apuracao", "on_conflict=colaborador_id,ano,mes", payload,
       "resolution=merge-duplicates,return=minimal")


def _regra_por_codigo(regras, codigo):
    return next((r for r in regras if str(r.get("codigo") or "").upper() == codigo), {})


def _percentual_tempo_revisao(media, regra):
    if media is None:
        return None
    h=float(media)
    if h <= 12: return float(regra.get("tempo_ate_12_percentual") if regra.get("tempo_ate_12_percentual") is not None else 100)
    if h <= 16: return float(regra.get("tempo_ate_16_percentual") if regra.get("tempo_ate_16_percentual") is not None else 60)
    if h <= 24: return float(regra.get("tempo_ate_24_percentual") if regra.get("tempo_ate_24_percentual") is not None else 40)
    return float(regra.get("tempo_acima_24_percentual") if regra.get("tempo_acima_24_percentual") is not None else 0)


def tela_apuracao_gratificacao():
    usr=st.session_state.get("usuario_logado") or {}
    st.markdown("### 💰 Apuração Mensal de Gratificação")
    st.caption("Frequência, DNA, salário e desvios são carregados automaticamente. Para REVISÃO, informe a equipe e a média mensal do Tempo de Entrega.")
    hoje=date.today(); meses_g=["Janeiro","Fevereiro","Março","Abril","Maio","Junho","Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"]
    g1,g2,g3=st.columns([1.1,.7,2.6])
    mes_g=g1.selectbox("Mês da apuração", range(1,13), index=hoje.month-1, format_func=lambda x: meses_g[x-1], key="grat_mes")
    ano_g=int(g2.number_input("Ano da apuração", min_value=2025, max_value=2100, value=hoje.year, step=1, key="grat_ano"))
    g3.markdown(f"### {meses_g[mes_g-1].upper()} / {ano_g}")
    try:
        regras=ler_regras_gratificacao(); freq=ler_frequencia(ano_g,mes_g)
        colabs=sb("GET","rh_colaboradores","select=*&order=colaborador.asc") or []
        ocorr_status=ler_ocorrencias(); dna_regs=ler_dna_mensal(ano_g,mes_g)
        ap_regs=ler_apuracao_gratificacao(ano_g,mes_g)
    except Exception as e:
        st.error(f"Não foi possível montar a apuração: {e}"); return
    rev=_regra_por_codigo(regras,"REVISAO"); demais=_regra_por_codigo(regras,"ITR_DEMAIS")
    if not rev or not demais:
        st.warning("Cadastre/salve primeiro as regras de gratificação."); return
    cod_por_id={int(o["id"]):str(o.get("codigo") or "").upper() for o in ocorr_status if o.get("id") is not None}
    dna_por={int(r["colaborador_id"]):int(r.get("quantidade") or 0) for r in dna_regs if r.get("colaborador_id") is not None}
    ap_por={int(r["colaborador_id"]):r for r in ap_regs if r.get("colaborador_id") is not None}

    # Médias mensais da REVISÃO são informadas em lote, uma vez por equipe.
    def _media_salva_equipe(nome_equipe):
        vals=[]
        for c in colabs:
            if str(c.get("frente") or "").upper().strip()=="REVISÃO" and str(c.get("equipe_revisao") or "").upper().strip()==nome_equipe:
                reg=ap_por.get(int(c["id"]), {})
                v=reg.get("media_tempo_entrega_horas")
                if v not in (None, ""):
                    try: vals.append(float(v))
                    except Exception: pass
        return vals[0] if vals else 0.0

    st.markdown("#### ⏱️ Média mensal por equipe — Revisão")
    st.caption("Informe a média uma única vez para cada equipe. O sistema aplica automaticamente a todos os colaboradores conforme a equipe cadastrada.")
    # Controles em lote alinhados e próximos aos campos das médias.
    _mc1,_mc2,_mc3,_mc4=st.columns([1,1,.58,.48], vertical_alignment="bottom")
    media_eq1=_mc1.number_input("Média EQUIPE 1 (h)", min_value=0.0, step=0.1, value=float(_media_salva_equipe("EQUIPE 1")), format="%.2f", key=f"media_eq1_{ano_g}_{mes_g}")
    media_eq2=_mc2.number_input("Média EQUIPE 2 (h)", min_value=0.0, step=0.1, value=float(_media_salva_equipe("EQUIPE 2")), format="%.2f", key=f"media_eq2_{ano_g}_{mes_g}")

    limpar_key=f"confirmar_limpeza_medias_{ano_g}_{mes_g}"
    if _mc4.button("🧹 Limpar médias", key=f"limpar_medias_{ano_g}_{mes_g}", use_container_width=True):
        st.session_state[limpar_key]=True

    if st.session_state.get(limpar_key, False):
        st.warning(f"⚠️ Confirma limpar as médias aplicadas em lote de {meses_g[mes_g-1]} / {ano_g}? A equipe cadastrada dos colaboradores NÃO será alterada.")
        _lc1,_lc2,_lc3=st.columns([1,1,3])
        if _lc1.button("✅ Sim, limpar", type="primary", key=f"confirmar_limpar_medias_{ano_g}_{mes_g}"):
            try:
                params=("ano=eq."+urllib.parse.quote(str(int(ano_g)))+"&mes=eq."+urllib.parse.quote(str(int(mes_g))))
                sb("DELETE", "rh_gratificacao_apuracao", params)
                st.session_state.pop(f"media_eq1_{ano_g}_{mes_g}", None)
                st.session_state.pop(f"media_eq2_{ano_g}_{mes_g}", None)
                st.session_state.pop(limpar_key, None)
                st.success("Médias da competência removidas. As equipes cadastradas nos colaboradores foram mantidas.")
                st.rerun()
            except Exception as e:
                st.error(f"Não foi possível limpar as médias: {e}")
        if _lc2.button("Cancelar", key=f"cancelar_limpar_medias_{ano_g}_{mes_g}"):
            st.session_state.pop(limpar_key, None)
            st.rerun()

    if _mc3.button("💾 Aplicar médias", type="primary", key=f"aplicar_medias_{ano_g}_{mes_g}", use_container_width=True):
        try:
            usuario=usr.get("nome") or usr.get("usuario")
            qtd=0
            for c in colabs:
                if str(c.get("frente") or "").upper().strip() != "REVISÃO":
                    continue
                eq=str(c.get("equipe_revisao") or "").upper().strip()
                if eq not in ("EQUIPE 1","EQUIPE 2"):
                    continue
                med=media_eq1 if eq=="EQUIPE 1" else media_eq2
                salvar_apuracao_manual(int(c["id"]),ano_g,mes_g,eq,med,None,usuario)
                qtd+=1
            st.success(f"Médias aplicadas a {qtd} colaborador(es) da Revisão.")
            st.rerun()
        except Exception as e:
            st.error(f"Não foi possível aplicar as médias: {e}")

    # A média individual agora é editada diretamente na linha da apuração.
    # O lançamento em lote acima continua disponível e pode ser usado normalmente.

    # A gratificação SEMPRE usa somente a frequência já persistida no Supabase.
    # Se existir rascunho/alteração pendente na tela de frequência desta mesma competência,
    # deixa isso explícito para evitar interpretar a grade editada como dado já salvo.
    _periodo_grat = f"{int(ano_g)}_{int(mes_g)}"
    _drafts_pendentes = [
        k for k, v in st.session_state.items()
        if str(k).startswith("rh_grade_draft_") and _periodo_grat in str(k) and isinstance(v, pd.DataFrame)
    ]
    if _drafts_pendentes:
        st.info(
            "ℹ️ A apuração considera os lançamentos **salvos no RH**. "
            "Se você acabou de trocar FALTA por ATESTADO na frequência, confirme a alteração com a senha/motivo "
            "e clique em **💾 Salvar alterações** antes de conferir a gratificação."
        )

    faltas={}; atest={}
    for f in freq:
        cid=int(f.get("colaborador_id") or 0); cod=cod_por_id.get(int(f.get("ocorrencia_id") or 0),"")
        if cod=="FA": faltas[cid]=faltas.get(cid,0)+1
        if cod=="A": atest[cid]=atest.get(cid,0)+1
    ini=f"{ano_g:04d}-{mes_g:02d}-01"; fim=f"{ano_g:04d}-{mes_g:02d}-{calendar.monthrange(ano_g,mes_g)[1]:02d}"
    try:
        oc_mes=sb("GET","rh_colaborador_ocorrencias",f"select=*&data=gte.{ini}&data=lte.{fim}") or []
    except Exception: oc_mes=[]
    # Regra da gratificação: somente estas ocorrências NÃO retiram a bonificação.
    # Qualquer outro tipo de ocorrência individual registrado pelo RH na competência
    # é considerado ocorrência que zera a gratificação.
    tipos_nao_penalizam={"ADVERTÊNCIA VERBAL","ORIENTAÇÃO","ELOGIO / RECONHECIMENTO"}
    desvios={}
    for o in oc_mes:
        tipo_oc=str(o.get("tipo") or "").upper().strip()
        if tipo_oc and tipo_oc not in tipos_nao_penalizam:
            cid=int(o.get("colaborador_id") or 0)
            desvios[cid]=desvios.get(cid,0)+1
    linhas=[]; ids={}
    # Somente colaboradores com uma FRENTE válida cadastrada participam da apuração.
    # Valores vazios vindos do banco/DataFrame (None, NaN, "nan", etc.) não são elegíveis.
    frentes_validas={"REVISÃO","ITR","SOS","CNP","BORRACHARIA","CAPD","FABRICAÇÃO","CRAVEJAMENTO"}
    for c in colabs:
        cid=int(c["id"]); nome=_nome_colaborador(c)
        frente_raw=c.get("frente")
        if frente_raw is None or pd.isna(frente_raw):
            continue
        frente=str(frente_raw).upper().strip()
        if frente not in frentes_validas:
            continue
        # FABRICAÇÃO já fica identificada pelo cadastro, mas seu cálculo específico
        # será implementado na etapa própria; por enquanto não entra no fechamento.
        if frente=="FABRICAÇÃO":
            continue
        dd=c.get("data_desligamento")
        if dd and str(dd) < ini: continue
        sal=float(c.get("salario_base") or 0); fa=faltas.get(cid,0); at=atest.get(cid,0); dna=dna_por.get(cid,0); des=desvios.get(cid,0)
        manual=ap_por.get(cid,{})
        equipe=str(c.get("equipe_revisao") or "").upper().strip() if frente=="REVISÃO" else ""
        # Valor individual salvo prevalece sobre o valor digitado nos campos de lote.
        _media_manual = manual.get("media_tempo_entrega_horas") if frente=="REVISÃO" else None
        if _media_manual not in (None, ""):
            try: media=float(_media_manual)
            except Exception: media=None
        elif frente=="REVISÃO" and equipe=="EQUIPE 1": media=media_eq1
        elif frente=="REVISÃO" and equipe=="EQUIPE 2": media=media_eq2
        else: media=None
        integral=(sal*float(rev.get("percentual_salario") or 35)/100) if frente=="REVISÃO" else float(demais.get("valor_fixo") or 360)
        valor=integral; motivos=[]; pct_tempo=None
        regra=rev if frente=="REVISÃO" else demais
        if fa>0 and bool(regra.get("falta_zera_tudo",True)): valor=0; motivos.append(f"{fa} falta(s)")
        if des>0 and bool(regra.get("desvio_comportamental_zera",True)): valor=0; motivos.append(f"{des} desvio(s)")
        if dna < int(regra.get("dna_minimo") or 2) and bool(regra.get("dna_abaixo_minimo_zera",True)): valor=0; motivos.append(f"DNA {dna}/{int(regra.get('dna_minimo') or 2)}")
        if valor>0 and frente=="REVISÃO" and media is not None and float(media) > 24:
            valor=0
            motivos.append("Tempo de entrega > 24h")
        if valor>0 and frente=="REVISÃO":
            abs_parcela=integral*float(rev.get("peso_absenteismo") or 20)/100
            tempo_parcela=integral*float(rev.get("peso_tempo_entrega") or 80)/100
            if at>=int(rev.get("atestados_zera_categoria") or 2): abs_parcela=0; motivos.append(f"{at} dias de atestado: absenteísmo zerado")
            elif at==1: abs_parcela=max(0,abs_parcela-float(rev.get("desconto_1_atestado_valor") or 100)); motivos.append("1 dia de atestado")
            pct_tempo=_percentual_tempo_revisao(media,rev)
            if pct_tempo is None:
                valor=None; motivos.append("informar média da Revisão")
            else: valor=abs_parcela + tempo_parcela*(pct_tempo/100)
        elif valor>0:
            if at>=int(demais.get("atestados_zera_tudo") or 2): valor=0; motivos.append(f"{at} dias de atestado")
            elif at==1:
                desc=float(demais.get("desconto_1_atestado_percentual") or 20); valor=integral*(1-desc/100); motivos.append(f"1 dia de atestado (-{desc:.0f}%)")
        status="⏳ PENDENTE" if valor is None else ("❌ ZERADA" if valor<=0 else ("✅ INTEGRAL" if abs(float(valor)-float(integral)) < 0.01 else "🟠 PARCIAL"))
        ids[nome]=cid
        linhas.append({"COLABORADOR":nome,"EMPRESA":_empresa_colaborador(c, visual=False),"FUNÇÃO":str(c.get("funcao") or "").strip(),"FRENTE":frente,"SALÁRIO":sal,"EQUIPE REVISÃO":equipe,"MÉDIA TEMPO (h)":media,"FALTAS":fa,"ATESTADOS (dias)":at,"DNA":dna,"DESVIOS":des,"INTEGRAL":integral,"GRATIFICAÇÃO":valor,"STATUS":status,"MOTIVO / CÁLCULO":" • ".join(motivos) if motivos else "Requisitos atendidos"})
    if not linhas:
        st.info("Nenhum colaborador com frente de gratificação definida para esta competência."); return
    df=pd.DataFrame(linhas)

    # Busca rápida na apuração para evitar rolagem em listas grandes.
    busca_grat = st.text_input(
        "🔎 Buscar colaborador",
        placeholder="Digite parte do nome...",
        key=f"grat_busca_{ano_g}_{mes_g}",
    ).strip()
    df_view = df.copy()
    if busca_grat:
        df_view = df_view[df_view["COLABORADOR"].astype(str).str.contains(busca_grat, case=False, na=False)]

    st.caption(
        "**EQUIPE REVISÃO** vem do Cadastro do Colaborador. **MÉDIA TEMPO** pode ser aplicada em lote acima ou alterada individualmente direto na linha. "
        "Os demais campos são calculados pelo sistema. Para conferir os desvios, clique em **🔎 VER** na própria linha do colaborador."
    )

    def _abrir_modal_desvios_grat(nome_colaborador, cid_colaborador, ocorrencias_impactantes):
        @st.dialog(f"⚠️ Desvios — {nome_colaborador}", width="large")
        def _modal():
            regs = [o for o in ocorrencias_impactantes if int(o.get("colaborador_id") or 0) == int(cid_colaborador)]
            if not regs:
                st.info("Não há ocorrência que retire a bonificação nesta competência.")
                return
            dados=[]
            for r in sorted(regs, key=lambda x: str(x.get("data") or ""), reverse=True):
                data_txt = ""
                if r.get("data"):
                    try: data_txt = pd.to_datetime(r.get("data")).strftime("%d/%m/%Y")
                    except Exception: data_txt = str(r.get("data"))
                dados.append({
                    "DATA": data_txt,
                    "TIPO": str(r.get("tipo") or ""),
                    "DESCRIÇÃO / MOTIVO": str(r.get("descricao") or ""),
                    "REGISTRADO POR": str(r.get("registrado_por") or ""),
                })
            st.dataframe(pd.DataFrame(dados), use_container_width=True, hide_index=True)
            st.caption("ADVERTÊNCIA VERBAL, ORIENTAÇÃO e ELOGIO / RECONHECIMENTO não aparecem aqui porque não retiram a bonificação.")
        _modal()

    # Somente ocorrências que efetivamente impactam a gratificação entram no detalhamento.
    oc_impactantes = [
        o for o in oc_mes
        if str(o.get("tipo") or "").upper().strip()
        and str(o.get("tipo") or "").upper().strip() not in tipos_nao_penalizam
    ]

    # Edição individual diretamente na própria linha.
    # Apenas MÉDIA TEMPO (h) fica editável; os demais campos continuam protegidos.
    df_editor = df_view.drop(columns=["EMPRESA", "FUNÇÃO"], errors="ignore").copy()
    df_editor["VER DESVIOS"] = False
    # Deixa a ação de visualizar os desvios junto do motivo/cálculo, no fim da linha.
    cols_editor = [c for c in df_editor.columns if c != "VER DESVIOS"]
    try:
        idx_motivo = cols_editor.index("MOTIVO / CÁLCULO")
        cols_editor.insert(idx_motivo, "VER DESVIOS")
    except ValueError:
        cols_editor.append("VER DESVIOS")
    df_editor = df_editor[cols_editor]
    editado_grat = st.data_editor(
        df_editor,
        use_container_width=True,
        hide_index=True,
        height=min(760,90+max(1,len(df_editor))*35),
        disabled=[c for c in df_editor.columns if c not in ("MÉDIA TEMPO (h)", "VER DESVIOS")],
        column_config={
            "VER DESVIOS": st.column_config.CheckboxColumn("🔎 VER", help="Clique aqui para abrir quais ocorrências retiraram a gratificação."),
            "SALÁRIO":st.column_config.NumberColumn("SALÁRIO",format="R$ %.2f"),
            "INTEGRAL":st.column_config.NumberColumn("INTEGRAL",format="R$ %.2f"),
            "GRATIFICAÇÃO":st.column_config.NumberColumn("GRATIFICAÇÃO",format="R$ %.2f"),
            "MÉDIA TEMPO (h)":st.column_config.NumberColumn(
                "MÉDIA TEMPO (h)", min_value=0.0, step=0.1, format="%.2f",
                help="Na REVISÃO, altere aqui para lançar uma média individual."
            ),
        },
        key=f"grat_editor_{ano_g}_{mes_g}",
    )

    # Salva automaticamente qualquer alteração individual feita na coluna MÉDIA TEMPO.
    # Para frentes diferentes de REVISÃO, a média não se aplica e a edição é descartada.
    alterou_media = False
    for pos in range(min(len(df_editor), len(editado_grat))):
        antes = df_editor.iloc[pos]
        depois = editado_grat.iloc[pos]
        nome_ed = str(antes["COLABORADOR"])
        frente_ed = str(antes["FRENTE"] or "").upper().strip()
        va = antes.get("MÉDIA TEMPO (h)")
        vd = depois.get("MÉDIA TEMPO (h)")
        va_cmp = None if pd.isna(va) else float(va)
        vd_cmp = None if pd.isna(vd) else float(vd)
        if va_cmp != vd_cmp:
            if frente_ed != "REVISÃO":
                st.warning(f"Média de tempo individual é utilizada somente para REVISÃO. Alteração de {nome_ed} ignorada.")
                alterou_media = True
                continue
            try:
                cid_ed = int(ids[nome_ed])
                colab_ed = next(c for c in colabs if int(c["id"]) == cid_ed)
                equipe_ed = str(colab_ed.get("equipe_revisao") or "").upper().strip() or None
                usuario_ed = usr.get("nome") or usr.get("usuario")
                salvar_apuracao_manual(cid_ed, ano_g, mes_g, equipe_ed, vd_cmp, None, usuario_ed)
                st.toast(f"Média de {nome_ed} salva: {vd_cmp:.2f} h" if vd_cmp is not None else f"Média de {nome_ed} removida.")
                alterou_media = True
            except Exception as e:
                st.error(f"Não foi possível salvar a média individual de {nome_ed}: {e}")

    # Abre o detalhamento de desvios somente uma vez por marcação.
    # Isso evita reabrir o dialog em todo rerun e impede conflito com a Ficha do Colaborador.
    _chave_desvio_tratado = f"grat_desvio_tratado_{ano_g}_{mes_g}"
    _marcados_agora = []
    for pos in range(len(editado_grat)):
        if bool(editado_grat.iloc[pos].get("VER DESVIOS", False)):
            _marcados_agora.append(str(editado_grat.iloc[pos]["COLABORADOR"]))

    _tratados = set(st.session_state.get(_chave_desvio_tratado, []))
    # Se o usuário desmarcou uma linha, ela volta a poder abrir no próximo clique.
    _tratados.intersection_update(_marcados_agora)
    _novo_clique = next((n for n in _marcados_agora if n not in _tratados), None)

    if _novo_clique:
        _tratados.add(_novo_clique)
        st.session_state[_chave_desvio_tratado] = list(_tratados)
        _linha_sel = editado_grat[editado_grat["COLABORADOR"].astype(str) == _novo_clique].iloc[0]
        if int(_linha_sel.get("DESVIOS", 0) or 0) > 0:
            _abrir_modal_desvios_grat(_novo_clique, ids.get(_novo_clique), oc_impactantes)
        else:
            st.info(f"{_novo_clique} não possui desvio que retire a bonificação nesta competência.")
    else:
        st.session_state[_chave_desvio_tratado] = list(_tratados)

    if alterou_media:
        st.rerun()

    validos=df["GRATIFICAÇÃO"].dropna()
    k1,k2,k3,k4=st.columns(4)
    k1.metric("Colaboradores",len(df)); k2.metric("Elegíveis",int((df["GRATIFICAÇÃO"].fillna(0)>0).sum())); k3.metric("Zerados",int((df["GRATIFICAÇÃO"]==0).sum())); k4.metric("Total previsto",f"R$ {validos.sum():,.2f}".replace(",","X").replace(".",",").replace("X","."))

    # Relatório de fechamento para a Contabilidade
    st.markdown("---")
    st.markdown("#### 📄 Relatório para Contabilidade")
    st.caption("Escolha a empresa e gere o fechamento da gratificação desta competência em Excel.")
    rc1, rc2 = st.columns([1, 2], vertical_alignment="bottom")
    empresa_rel = rc1.selectbox(
        "Empresa", ["SERVICE", "PRESTADORA"],
        key=f"grat_rel_empresa_{ano_g}_{mes_g}"
    )

    def _gerar_relatorio_contabilidade(df_base, empresa):
        dfr = df_base[df_base["EMPRESA"].astype(str).str.upper().str.strip() == empresa].copy()
        cols = ["COLABORADOR","EMPRESA","FUNÇÃO","FRENTE","SALÁRIO","INTEGRAL","GRATIFICAÇÃO","STATUS","MOTIVO / CÁLCULO","EQUIPE REVISÃO","MÉDIA TEMPO (h)"]
        dfr = dfr[cols].copy()
        dfr = dfr.rename(columns={
            "SALÁRIO":"SALÁRIO BASE",
            "INTEGRAL":"GRATIFICAÇÃO INTEGRAL",
            "GRATIFICAÇÃO":"GRATIFICAÇÃO APURADA",
            "EQUIPE REVISÃO":"EQUIPE",
            "MÉDIA TEMPO (h)":"MÉDIA TEMPO (h)"
        })
        wb = Workbook(); ws = wb.active; ws.title = "Gratificação"
        titulo = f"RELATÓRIO DE GRATIFICAÇÃO - {empresa} - {meses_g[mes_g-1].upper()} / {ano_g}"
        ws.merge_cells(start_row=1,start_column=1,end_row=1,end_column=len(dfr.columns))
        c=ws.cell(1,1,titulo); c.font=Font(bold=True,size=14,color="FFFFFF"); c.fill=PatternFill("solid",fgColor="1F4E78"); c.alignment=Alignment(horizontal="center")
        for j,col in enumerate(dfr.columns,1):
            cell=ws.cell(3,j,col); cell.font=Font(bold=True,color="FFFFFF"); cell.fill=PatternFill("solid",fgColor="4472C4"); cell.alignment=Alignment(horizontal="center")
        for i,row in enumerate(dfr.itertuples(index=False,name=None),4):
            for j,val in enumerate(row,1):
                if pd.isna(val): val=None
                ws.cell(i,j,val)
        total_row=4+len(dfr)
        ws.cell(total_row,1,"TOTAL").font=Font(bold=True)
        grat_col=list(dfr.columns).index("GRATIFICAÇÃO APURADA")+1
        ws.cell(total_row,grat_col,float(pd.to_numeric(dfr["GRATIFICAÇÃO APURADA"],errors="coerce").fillna(0).sum())).font=Font(bold=True)
        for row in range(4,total_row+1):
            for nome_col in ["SALÁRIO BASE","GRATIFICAÇÃO INTEGRAL","GRATIFICAÇÃO APURADA"]:
                idx=list(dfr.columns).index(nome_col)+1; ws.cell(row,idx).number_format='R$ #,##0.00'
        if len(dfr)>0:
            ref=f"A3:{get_column_letter(len(dfr.columns))}{3+len(dfr)}"
            tab=Table(displayName="TabelaGratificacao",ref=ref)
            tab.tableStyleInfo=TableStyleInfo(name="TableStyleMedium2",showFirstColumn=False,showLastColumn=False,showRowStripes=True,showColumnStripes=False)
            ws.add_table(tab)
        widths={1:34,2:15,3:24,4:18,5:16,6:22,7:22,8:16,9:42,10:18,11:18}
        for col,w in widths.items(): ws.column_dimensions[get_column_letter(col)].width=w
        ws.freeze_panes="A4"
        bio=BytesIO(); wb.save(bio); bio.seek(0)
        return bio.getvalue(), len(dfr)

    chave_rel=f"grat_rel_bytes_{ano_g}_{mes_g}_{empresa_rel}"
    if rc2.button("📊 Gerar relatório de gratificação", type="primary", key=f"gerar_rel_{ano_g}_{mes_g}"):
        try:
            dados_rel, qtd_rel = _gerar_relatorio_contabilidade(df, empresa_rel)
            st.session_state[chave_rel]=dados_rel
            st.session_state[chave_rel+"_qtd"]=qtd_rel
        except Exception as e:
            st.error(f"Não foi possível gerar o relatório: {e}")
    if st.session_state.get(chave_rel):
        qtd_rel=st.session_state.get(chave_rel+"_qtd",0)
        if qtd_rel==0:
            st.warning(f"Nenhum colaborador elegível para apuração encontrado na empresa {empresa_rel} nesta competência.")
        else:
            nome_arq=f"GRATIFICACAO_{empresa_rel}_{meses_g[mes_g-1].upper()}_{ano_g}.xlsx"
            st.download_button("⬇️ Baixar relatório para Contabilidade", data=st.session_state[chave_rel], file_name=nome_arq, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key=f"baixar_rel_{ano_g}_{mes_g}_{empresa_rel}")

def tela_dna_seguranca():
    usr=st.session_state.get("usuario_logado") or {}
    st.title("🦺 Controle de DNA — Segurança do Trabalho")
    st.caption("Informe somente a quantidade de DNAs realizados por colaborador em cada competência.")
    cabecalho_sessao()
    hoje=date.today(); meses=["Janeiro","Fevereiro","Março","Abril","Maio","Junho","Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"]
    a,b,c=st.columns([1.2,.7,2.5], vertical_alignment="bottom")
    with a: mes_d=st.selectbox("Mês", range(1,13), index=hoje.month-1, format_func=lambda x: meses[x-1], key="dna_mes_seg")
    with b: ano_d=st.number_input("Ano", min_value=2025, max_value=2100, value=hoje.year, step=1, key="dna_ano_seg")
    with c:
        st.markdown(
            f'<div style="height:38px;display:flex;align-items:center;font-size:1.55rem;font-weight:700;line-height:1;">{meses[mes_d-1].upper()} / {int(ano_d)}</div>',
            unsafe_allow_html=True,
        )
    fechado, limite=competencia_dna_fechada(int(ano_d), mes_d, hoje)
    unlock_key=f"dna_seg_unlock_{int(ano_d)}_{mes_d}"
    liberado=bool(st.session_state.get(unlock_key,False))
    if fechado and not liberado:
        st.warning(f"🔒 Competência fechada desde {limite.strftime('%d/%m/%Y')}. Alterações após o prazo exigem autorização do RH/Administrador.")
        with st.expander("🔐 Desbloquear competência"):
            su=st.text_input("Usuário RH/Administrador", key=f"dna_auth_u_{ano_d}_{mes_d}")
            sp=st.text_input("Senha", type="password", key=f"dna_auth_p_{ano_d}_{mes_d}")
            if st.button("Liberar edição", key=f"dna_auth_b_{ano_d}_{mes_d}"):
                aut=autenticar_usuario(su,sp)
                if aut and aut.get("perfil") in ("RH","ADMIN"):
                    st.session_state[unlock_key]=True; st.rerun()
                else: st.error("Autorização inválida.")
    elif fechado and liberado:
        st.info("🔓 Competência liberada nesta sessão por autorização.")
    else:
        st.caption(f"Prazo para lançamento desta competência: até {limite.strftime('%d/%m/%Y')}.")
    pode=(not fechado) or liberado

    colabs=sb("GET","rh_colaboradores","select=*&order=colaborador.asc") or []
    ativos=[c for c in colabs if bool(c.get("ativo", True))]
    regs=ler_dna_mensal(int(ano_d),mes_d)
    qtd_por={int(r['colaborador_id']):int(r.get('quantidade') or 0) for r in regs if r.get('colaborador_id') is not None}
    linhas=[]; id_por_nome={}
    for col in ativos:
        cid=int(col['id']); nome=_nome_colaborador(col); id_por_nome[nome]=cid
        q=int(qtd_por.get(cid,0) or 0)
        linhas.append({"DESTRA":str(col.get("destra") or ""),"COLABORADOR":nome,"DNA":q,"STATUS GRATIFICAÇÃO":"✅ APTO" if q>=2 else "❌ NÃO ATENDE"})
    df_banco=pd.DataFrame(linhas)
    if df_banco.empty:
        st.info("Nenhum colaborador ativo encontrado."); return

    # Rascunho da competência: alterações ficam na tela sem voltar ao valor do banco.
    periodo=f"{int(ano_d)}_{int(mes_d):02d}"
    draft_key=f"dna_draft_seg_{periodo}"
    nonce_key=f"dna_nonce_seg_{periodo}"
    fp_key=f"dna_fp_seg_{periodo}"
    import hashlib
    base_serial=df_banco[["DESTRA","COLABORADOR","DNA"]].to_json(orient="records", force_ascii=False)
    base_fp=hashlib.sha256(base_serial.encode("utf-8")).hexdigest()
    if draft_key not in st.session_state or not isinstance(st.session_state.get(draft_key), pd.DataFrame):
        st.session_state[draft_key]=df_banco.copy()
        st.session_state[fp_key]=base_fp
        st.session_state[nonce_key]=0
    else:
        draft=st.session_state[draft_key]
        # Só recarrega do banco quando não há edição pendente e a base realmente mudou.
        if list(draft["COLABORADOR"]) != list(df_banco["COLABORADOR"]):
            st.session_state[draft_key]=df_banco.copy()
            st.session_state[fp_key]=base_fp
            st.session_state[nonce_key]=int(st.session_state.get(nonce_key,0))+1

    # Visualização rápida para cobrança/print dos DNAs pendentes.
    filtro_key=f"dna_filtro_pendentes_{periodo}"
    if filtro_key not in st.session_state:
        st.session_state[filtro_key]=False

    fb1, fb2, fb3 = st.columns([1.15, 1.0, 4.0])
    with fb1:
        if st.button("📋 Pendentes de DNA", key=f"dna_pendentes_{periodo}", use_container_width=True):
            st.session_state[filtro_key]=True
            st.session_state[nonce_key]=int(st.session_state.get(nonce_key,0))+1
            st.rerun()
    with fb2:
        if st.button("👥 Mostrar todos", key=f"dna_todos_{periodo}", use_container_width=True):
            st.session_state[filtro_key]=False
            st.session_state[nonce_key]=int(st.session_state.get(nonce_key,0))+1
            st.rerun()

    draft=st.session_state[draft_key].copy()

    # Exportação no mesmo padrão da planilha de DNA: DESTRA | COLABORADOR | DNA em X.
    # Ex.: quantidade 2 = XX; quantidade 4 = XXXX.
    def _excel_dna_bytes(df_origem):
        # Exporta como TABELA do Excel, no mesmo padrão visual da planilha de DNA enviada.
        out = BytesIO()
        wb = Workbook()
        ws = wb.active
        ws.title = "DNA"
        ws.append(["DESTRA", "COLABORADOR", "DNA"])

        for _, r in df_origem.iterrows():
            try:
                valor = pd.to_numeric(r.get("DNA"), errors="coerce")
                qtd = 0 if pd.isna(valor) else max(0, int(valor))
            except Exception:
                qtd = 0
            ws.append([r.get("DESTRA", ""), r.get("COLABORADOR", ""), "X" * qtd])

        # Tabela estruturada dinâmica: 1 linha de cabeçalho + quantidade real de colaboradores.
        # Ex.: 115 colaboradores => A1:C116. Não cria linha fictícia no fim.
        qtd_colaboradores = len(df_origem.index)
        ultima_linha = qtd_colaboradores + 1
        if qtd_colaboradores > 0:
            tabela = Table(displayName="TabelaDNA", ref=f"A1:C{ultima_linha}")
            estilo = TableStyleInfo(
                name="TableStyleMedium2",
                showFirstColumn=False,
                showLastColumn=False,
                showRowStripes=True,
                showColumnStripes=False,
            )
            tabela.tableStyleInfo = estilo
            ws.add_table(tabela)

        ws.freeze_panes = "A2"
        ws.column_dimensions["A"].width = 14.5546875
        ws.column_dimensions["B"].width = 58.21875
        ws.column_dimensions["C"].width = 13.77734375

        for row in ws.iter_rows(min_row=1, max_row=ws.max_row, min_col=1, max_col=3):
            for cell in row:
                cell.alignment = Alignment(vertical="center")
        for row in ws.iter_rows(min_row=2, min_col=3, max_col=3):
            row[0].alignment = Alignment(horizontal="left", vertical="center")

        wb.save(out)
        out.seek(0)
        return out.getvalue()

    exp1, exp2, exp3 = st.columns([1.15, 1.0, 4.0])
    with exp1:
        st.download_button(
            "📥 Exportar Excel",
            data=_excel_dna_bytes(draft),
            file_name=f"DNA_{meses[mes_d-1].upper()}_{int(ano_d)}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            key=f"dna_excel_{periodo}",
        )

    if st.session_state.get(filtro_key, False):
        st.markdown(f"### 📋 Pendências de DNA — {meses[mes_d-1]} / {int(ano_d)}")
        st.caption(f"Posição em {hoje.strftime('%d/%m/%Y')} • Exibindo somente colaboradores com menos de 2 DNAs.")
        exibido=draft[pd.to_numeric(draft["DNA"], errors="coerce").fillna(0) < 2].copy().reset_index(drop=True)
        if exibido.empty:
            st.success("✅ Todos os colaboradores atingiram o mínimo de 2 DNAs nesta competência.")
    else:
        exibido=draft.copy().reset_index(drop=True)

    editor_key=f"dna_editor_seg_{periodo}_{st.session_state.get(nonce_key,0)}"
    nomes_exibidos=list(exibido["COLABORADOR"])

    def _dna_editor_changed():
        estado=st.session_state.get(editor_key, {}) or {}
        edits=estado.get("edited_rows", {}) or {}
        draft=st.session_state[draft_key].copy()
        for ridx, mudancas in edits.items():
            try:
                pos=int(ridx)
                nome_linha=nomes_exibidos[pos]
            except Exception:
                continue
            alvo=draft.index[draft["COLABORADOR"].astype(str)==str(nome_linha)].tolist()
            if not alvo:
                continue
            i=alvo[0]
            if "DNA" in mudancas:
                try: q=max(0,int(mudancas.get("DNA") or 0))
                except Exception: q=0
                draft.at[i,"DNA"]=q
                draft.at[i,"STATUS GRATIFICAÇÃO"]="✅ APTO" if q>=2 else "❌ NÃO ATENDE"
        st.session_state[draft_key]=draft
        # recria o editor com o rascunho atualizado; assim o STATUS muda na hora
        st.session_state[nonce_key]=int(st.session_state.get(nonce_key,0))+1

    edit=st.data_editor(
        exibido,
        use_container_width=True,
        hide_index=True,
        disabled=["DESTRA","COLABORADOR","STATUS GRATIFICAÇÃO"] if pode else list(draft.columns),
        column_config={"DNA":st.column_config.NumberColumn("DNA",min_value=0,step=1,format="%d")},
        key=editor_key,
        on_change=_dna_editor_changed if pode else None,
        height=min(780,80+len(draft)*35),
    )

    if pode and st.button("💾 Salvar DNA", type="primary", key=f"dna_salvar_seg_{periodo}"):
        try:
            atual=st.session_state[draft_key].copy()
            alterados=0
            banco_por_nome={r["COLABORADOR"]:int(r["DNA"] or 0) for _,r in df_banco.iterrows()}
            for _,row in atual.iterrows():
                nome=row["COLABORADOR"]; novo=int(row["DNA"] or 0); antigo=int(banco_por_nome.get(nome,0))
                if novo!=antigo:
                    salvar_dna_mensal(id_por_nome[nome],int(ano_d),mes_d,novo,usr.get("nome") or usr.get("usuario")); alterados+=1
            # Após salvar, descarta o rascunho para a próxima execução vir do banco.
            st.session_state.pop(draft_key,None)
            st.session_state.pop(fp_key,None)
            st.session_state[nonce_key]=int(st.session_state.get(nonce_key,0))+1
            st.success(f"{alterados} alteração(ões) salva(s).")
            st.rerun()
        except Exception as e:
            st.error(f"Não foi possível salvar: {e}")

st.markdown("""
<style>
.block-container{padding-top:1.25rem;max-width:98%}
h1{margin-bottom:.1rem}
.rh-sub{color:#667085;margin-bottom:1rem}
div[data-testid="stDataEditor"]{border:1px solid #d0d5dd;border-radius:8px;overflow:hidden}
div[data-testid="stDataEditor"] [role="columnheader"]{font-weight:700!important}
</style>
""", unsafe_allow_html=True)

@st.dialog("❔ Como usar o Portal RH")
def abrir_ajuda_portal():
    st.markdown("""
### Visão geral
O **Portal RH — Aracruz** foi criado para registrar e acompanhar a frequência mensal dos colaboradores de forma simples e segura.

### 1. Resumo do mês
Na parte superior você acompanha os totais de **Faltas, Atestados, Folgas, Presenças, Liberados e Compensações**. A **Média de Colaboradores** considera somente os colaboradores classificados como **OPERACIONAL**, conforme a regra definida para o portal.

### 2. Colaboradores
O quadro **Colaboradores** mostra o total de pessoas cadastradas e a divisão entre **Operacionais** e **Outros**. Você pode usar **Buscar colaborador** para localizar rapidamente um nome e o filtro **STATUS** para visualizar TODOS, OPERACIONAL ou OUTROS.

### 3. Preenchimento da frequência
Cada coluna numerada representa um **dia do mês**. Selecione a ocorrência correspondente para cada colaborador.

- 🟧 **PENDENTE**: dia já disponível e ainda sem lançamento.
- **DEM**: colaborador demitido; aplicado automaticamente a partir do dia seguinte à data de desligamento e não entra nos indicadores.
- 🟧 **Alterado / não salvo**: lançamento feito na tela, mas ainda aguardando o botão **Salvar alterações**.
- 🟦 **Salvo**: lançamento já gravado no sistema.
- Dias futuros permanecem sem cobrança de preenchimento.

### 4. LB e COMP
Ao selecionar **LB** ou **COMP**, o sistema abre imediatamente uma janela de **observação obrigatória**. O lançamento somente é confirmado depois de preencher a informação exigida e clicar em **Confirmar observação**. Se a janela for fechada sem confirmar, o lançamento não deve permanecer.

### 5. Salvamento e alterações posteriores
Use **Salvar alterações** para gravar o que foi preenchido. É permitido salvar mesmo que ainda existam células pendentes, para que o RH possa continuar o trabalho depois. Depois que um lançamento estiver salvo, qualquer alteração exige **senha de autorização** e **motivo da alteração**, preservando o controle do histórico.

### 6. Análises de Frequência
Abra **📊 Análises de Frequência** para consultar o resumo por função e o gráfico comparativo de **Faltas x Atestados por colaborador**.

### 7. Ficha e ocorrências do colaborador
Use **Ficha / ocorrências do colaborador** para registrar advertências, suspensões, orientações, ocorrências de segurança/qualidade, reconhecimentos ou outros fatos relacionados ao colaborador. Esses registros ficam em um histórico separado e **não alteram a frequência nem a Média de Colaboradores**.

### 8. Exportação
O botão **Exportar Excel — BaseFuncionário / BaseFuncionário** gera o arquivo no modelo utilizado pelo RH com os lançamentos do período.

**Dica:** se estiver procurando uma pessoa específica, use a busca por nome antes de lançar. Ao apagar o texto da busca, a grade volta automaticamente a exibir todos os colaboradores permitidos pelo filtro de STATUS.
    """)
    if st.button("Entendi", use_container_width=True, type="primary"):
        st.rerun()



@st.dialog("👤 Ficha do Colaborador", width="large")
def abrir_ficha_colaborador(colaborador):
    cid = int(colaborador["id"])
    nome = _nome_colaborador(colaborador)
    st.markdown(f"### {nome}")
    _f1, _f2, _f3 = st.columns(3)
    _f1.caption(f"**Status:** {_classificacao_colaborador(colaborador)}")
    _f2.caption(f"**Função:** {str(colaborador.get('funcao') or colaborador.get('funcao_padrao') or '-')}")
    _f3.caption(f"**Empresa:** {_empresa_colaborador(colaborador, visual=True) or '-'}")

    if not _tabela_ocorrencias_disponivel():
        st.error(
            "A tabela de ocorrências individuais ainda não existe no Supabase. "
            "Execute uma única vez o arquivo SQL enviado junto com esta versão."
        )
        return

    st.markdown("#### ➕ Registrar ocorrência")
    _c1, _c2 = st.columns([1, 2])
    with _c1:
        _data_oc = st.date_input("Data da ocorrência", value=date.today(), key=f"oc_data_{cid}")
    with _c2:
        _tipo_oc = st.selectbox("Tipo", TIPOS_OCORRENCIA_COLABORADOR, key=f"oc_tipo_{cid}")
    _descricao_oc = st.text_area(
        "Descrição / motivo *",
        placeholder="Descreva de forma objetiva o que ocorreu...",
        key=f"oc_desc_{cid}",
        height=110,
    )
    _registrado_por = st.text_input(
        "Registrado por *",
        placeholder="Nome do responsável pelo registro",
        key=f"oc_resp_{cid}",
    )
    if st.button("💾 Registrar ocorrência", type="primary", use_container_width=True, key=f"oc_salvar_{cid}"):
        try:
            salvar_ocorrencia_colaborador(cid, _data_oc, _tipo_oc, _descricao_oc, _registrado_por)
            # Não alterar session_state do text_area depois que o widget foi instanciado.
            # O rerun atualiza a ficha e evita o erro StreamlitAPIException.
            st.success("Ocorrência registrada com sucesso.")
            st.rerun()
        except Exception as e:
            st.error(f"Não foi possível registrar: {e}")

    st.divider()
    st.markdown("#### 📚 Histórico de ocorrências")
    try:
        _hist = ler_ocorrencias_colaborador(cid)
    except Exception as e:
        st.error(f"Não foi possível carregar o histórico: {e}")
        _hist = []
    if _hist:
        for _oc in _hist:
            _oc_id = int(_oc.get("id") or 0)
            _data_txt = pd.to_datetime(_oc.get("data"), errors="coerce")
            _data_txt = _data_txt.strftime("%d/%m/%Y") if not pd.isna(_data_txt) else ""
            _tipo_txt = str(_oc.get("tipo") or "")
            _desc_txt = str(_oc.get("descricao") or "")
            _resp_txt = str(_oc.get("registrado_por") or "")

            _h1, _h2, _h3, _h4, _h5 = st.columns([1.0, 1.25, 2.2, 1.25, 0.65])
            _h1.write(_data_txt)
            _h2.write(_tipo_txt)
            _h3.write(_desc_txt)
            _h4.write(_resp_txt)
            if _h5.button("🗑️", key=f"excluir_oc_{cid}_{_oc_id}", help="Excluir ocorrência"):
                st.session_state[f"confirmar_exclusao_oc_{cid}"] = _oc_id

            if st.session_state.get(f"confirmar_exclusao_oc_{cid}") == _oc_id:
                st.warning(f"Excluir a ocorrência {_tipo_txt} de {_data_txt}? Esta ação também atualizará a apuração da gratificação.")
                _cf1, _cf2, _cf3 = st.columns([1, 1, 4])
                if _cf1.button("Sim, excluir", type="primary", key=f"conf_excluir_oc_{cid}_{_oc_id}"):
                    try:
                        sb("DELETE", "rh_colaborador_ocorrencias", f"id=eq.{_oc_id}", None, "return=minimal")
                        st.session_state.pop(f"confirmar_exclusao_oc_{cid}", None)
                        st.success("Ocorrência excluída com sucesso.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Não foi possível excluir a ocorrência: {e}")
                if _cf2.button("Cancelar", key=f"cancel_excluir_oc_{cid}_{_oc_id}"):
                    st.session_state.pop(f"confirmar_exclusao_oc_{cid}", None)
                    st.rerun()
            st.divider()
    else:
        st.caption("Nenhuma ocorrência individual registrada para este colaborador.")


# ==========================================================
# FECHAMENTO CMC BAHIA
# ==========================================================
def _normalizar_status_cmc(valor):
    if pd.isna(valor):
        return ""
    txt = str(valor).strip().upper()
    mapa = {
        "1": "OK", "1.0": "OK", "PRESENÇA": "OK", "PRESENCA": "OK", "OK": "OK",
        "FOLGA": "FO", "FO": "FO",
        "FALTA": "FA", "FA": "FA",
        "ATESTADO": "A", "A": "A",
        "FÉRIAS": "FE", "FERIAS": "FE", "FE": "FE",
        "LIBERADO": "LB", "LB": "LB",
        "COMPENSAÇÃO": "COMP", "COMPENSACAO": "COMP", "COMP": "COMP",
    }
    return mapa.get(txt, txt)

def _ler_ponto_cmc(arquivo):
    xls = pd.ExcelFile(arquivo)
    candidatas = [x for x in xls.sheet_names if "PONTO" in str(x).upper() and "DI" in str(x).upper()]
    aba = candidatas[0] if candidatas else xls.sheet_names[0]
    df = pd.read_excel(xls, sheet_name=aba)
    obrig = {"Dt. Ponto", "Nome", "STATUS"}
    if not obrig.issubset(set(df.columns)):
        raise ValueError(f"A aba {aba} não possui as colunas obrigatórias: Dt. Ponto, Nome e STATUS.")
    df = df.copy()
    df["Dt. Ponto"] = pd.to_datetime(df["Dt. Ponto"], errors="coerce")
    df = df[df["Dt. Ponto"].notna() & df["Nome"].notna()].copy()
    df["Nome"] = df["Nome"].astype(str).str.strip().str.upper()
    df["CODIGO"] = df["STATUS"].apply(_normalizar_status_cmc)
    return df, aba

def _montar_matriz_cmc(df):
    if df.empty:
        return pd.DataFrame(), None, None
    periodo = df["Dt. Ponto"].dt.to_period("M").mode().iloc[0]
    ano, mes = int(periodo.year), int(periodo.month)
    dias = calendar.monthrange(ano, mes)[1]
    base = df[(df["Dt. Ponto"].dt.year == ano) & (df["Dt. Ponto"].dt.month == mes)].copy()
    base["DIA"] = base["Dt. Ponto"].dt.day
    p = base.pivot_table(index="Nome", columns="DIA", values="CODIGO", aggfunc="first", fill_value="")
    p = p.reindex(columns=range(1, dias + 1), fill_value="")
    p.columns = [f"{d:02d}" for d in range(1, dias + 1)]
    p = p.reset_index().rename(columns={"Nome":"COLABORADOR"})
    return p, ano, mes

def _resumo_matriz_cmc(matriz):
    if matriz.empty:
        return matriz.copy()
    dias_cols = [c for c in matriz.columns if str(c).isdigit()]
    r = matriz.copy()
    for cod, nome in [("OK","PRESENTES"),("FA","FALTAS"),("A","ATESTADOS"),("FO","FOLGAS"),("FE","FÉRIAS")]:
        r[nome] = (r[dias_cols] == cod).sum(axis=1)
    # Para a média mensal do efetivo entram somente OK + FALTA + ATESTADO + FOLGA.
    # Férias e demais códigos não entram nessa conta.
    r["TOTAL CONTABILIZADO"] = r[["PRESENTES","FALTAS","ATESTADOS","FOLGAS"]].sum(axis=1)
    # A média individual representa a fração de 1 colaborador no mês:
    # (FO + FA + A + OK) / quantidade de dias da competência.
    dias_mes = len(dias_cols)
    r["MÉDIA CONTABILIZADA"] = (r["TOTAL CONTABILIZADO"] / dias_mes).round(2) if dias_mes else 0.0
    return r

def _excel_cmc(matriz, ano, mes):
    resumo = _resumo_matriz_cmc(matriz)
    wb = Workbook()
    ws = wb.active
    ws.title = "EFETIVO"
    headers = list(resumo.columns)
    for j,h in enumerate(headers,1):
        c=ws.cell(1,j,h); c.font=Font(bold=True,color="FFFFFF"); c.fill=PatternFill("solid",fgColor="1F4E78"); c.alignment=Alignment(horizontal="center")
    for i,row in enumerate(resumo.itertuples(index=False, name=None),2):
        for j,v in enumerate(row,1): ws.cell(i,j,v)
    ws.freeze_panes="B2"
    ws.column_dimensions["A"].width=38
    for j in range(2,len(headers)+1): ws.column_dimensions[get_column_letter(j)].width=10
    if len(resumo):
        tab=Table(displayName="TabelaFechamentoCMCBahia", ref=f"A1:{get_column_letter(len(headers))}{len(resumo)+1}")
        tab.tableStyleInfo=TableStyleInfo(name="TableStyleMedium2", showRowStripes=True, showFirstColumn=False, showLastColumn=False, showColumnStripes=False)
        ws.add_table(tab)
    ws2=wb.create_sheet("RESUMO")
    ws2.append(["FECHAMENTO CMC BAHIA", f"{mes:02d}/{ano}"])
    ws2.append(["INDICADOR","TOTAL"])
    for col in ["PRESENTES","FALTAS","ATESTADOS","FOLGAS","FÉRIAS","TOTAL CONTABILIZADO"]:
        ws2.append([col, int(resumo[col].sum()) if col in resumo else 0])
    dias_mes = calendar.monthrange(ano, mes)[1]
    total_contabilizado = int(resumo["TOTAL CONTABILIZADO"].sum()) if "TOTAL CONTABILIZADO" in resumo else 0
    media_colaboradores = total_contabilizado / dias_mes if dias_mes else 0
    ws2.append(["DIAS DO MÊS", dias_mes])
    ws2.append(["MÉDIA DE COLABORADORES", media_colaboradores])
    # Formata a linha da média sem depender de posição fixa.
    ws2.cell(ws2.max_row, 2).number_format = "0.00"
    ws2.column_dimensions["A"].width = 28
    ws2.column_dimensions["B"].width = 18
    bio=BytesIO(); wb.save(bio); bio.seek(0); return bio.getvalue()

def tela_fechamento_cmc_bahia():
    st.markdown("### 🏭 Fechamento CMC Bahia")
    st.caption("Importe a planilha do ponto eletrônico. O Portal monta automaticamente a matriz mensal por colaborador e dia, sem PROCV/PROCX.")
    arq = st.file_uploader("Planilha do ponto eletrônico — CMC Bahia", type=["xlsx","xls"], key="upload_ponto_cmc_bahia")
    if not arq:
        st.info("Envie a planilha do ponto eletrônico para iniciar a apuração.")
        return
    try:
        df, aba = _ler_ponto_cmc(arq)
        matriz, ano, mes = _montar_matriz_cmc(df)
        if matriz.empty:
            st.warning("Nenhum registro válido foi encontrado na planilha.")
            return
        st.success(f"{aba} lida com sucesso • Competência {mes:02d}/{ano} • {len(matriz)} colaboradores")
        dias_cols=[c for c in matriz.columns if str(c).isdigit()]
        opcoes=["", "OK", "FO", "FA", "A", "FE", "LB", "COMP"]
        cfg={"COLABORADOR": st.column_config.TextColumn("COLABORADOR", disabled=True)}
        for c in dias_cols: cfg[c]=st.column_config.SelectboxColumn(c, options=opcoes, required=False, width="small")
        edit = st.data_editor(matriz, use_container_width=True, hide_index=True, disabled=["COLABORADOR"], column_config=cfg, key=f"cmc_editor_{ano}_{mes}")
        resumo=_resumo_matriz_cmc(edit)
        st.markdown("#### Resumo do fechamento")
        st.dataframe(resumo[["COLABORADOR","PRESENTES","FALTAS","ATESTADOS","FOLGAS","FÉRIAS","TOTAL CONTABILIZADO","MÉDIA CONTABILIZADA"]], use_container_width=True, hide_index=True)

        dias_mes = calendar.monthrange(ano, mes)[1]
        total_contabilizado = int(resumo["TOTAL CONTABILIZADO"].sum())
        media_colaboradores = total_contabilizado / dias_mes if dias_mes else 0
        c1, c2, c3 = st.columns(3)
        c1.metric("Registros considerados", f"{total_contabilizado}")
        c2.metric("Dias do mês", f"{dias_mes}")
        c3.metric("Média de colaboradores", f"{media_colaboradores:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        st.caption("TOTAL CONTABILIZADO = OK + FA + A + FO. MÉDIA CONTABILIZADA = TOTAL CONTABILIZADO ÷ dias da competência. A Média de Colaboradores é a soma dessas médias individuais. FÉRIAS não entra na conta.")

        excel=_excel_cmc(edit,ano,mes)
        st.download_button("📥 Exportar fechamento CMC Bahia", data=excel, file_name=f"FECHAMENTO_CMC_BAHIA_{mes:02d}_{ano}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", type="primary")
        st.caption("Legenda: OK = Presença • FO = Folga • FA = Falta • A = Atestado • FE = Férias • LB = Liberado • COMP = Compensação")
    except Exception as e:
        st.error(f"Não foi possível processar o ponto eletrônico: {e}")

# ==========================================================
# LOGIN / ROTEAMENTO POR PERFIL
# ==========================================================
if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    st.error("Supabase ainda não configurado neste app. Adicione SUPABASE_URL e SUPABASE_SERVICE_KEY nos Secrets.")
    st.stop()

if not st.session_state.get("usuario_logado"):
    tela_login()
    st.stop()

if bool(st.session_state["usuario_logado"].get("trocar_senha", False)):
    st.markdown("<div style='height:5vh'></div>", unsafe_allow_html=True)
    c1,c2,c3=st.columns([1,1.15,1])
    with c2:
        modal_alterar_senha(True)
    st.stop()

_perfil_atual = str(st.session_state["usuario_logado"].get("perfil") or "").upper()
if _perfil_atual == "SEGURANCA":
    tela_dna_seguranca()
    st.stop()
if _perfil_atual not in ("RH", "ADMIN"):
    st.error("Seu perfil não possui acesso a este portal.")
    st.stop()

st.title("👥 Portal RH — Aracruz")
st.markdown('<div class="rh-sub">10 Sul • Controle mensal de presença e ocorrências</div>', unsafe_allow_html=True)

# Controles da sessão ficam DEPOIS do título/subtítulo.
# Assim não são capturados/empurrados pela área superior do Streamlit.
cabecalho_sessao(mostrar_ajuda=True)

# Módulo CMC Bahia: página exclusiva e disponível somente para ADMIN.
if _perfil_atual == "ADMIN" and st.session_state.get("pagina_portal_rh") == "CMC_BAHIA":
    if st.button("← Voltar ao Portal RH", key="voltar_portal_cmc_bahia"):
        st.session_state["pagina_portal_rh"] = "PRINCIPAL"
        st.rerun()
    st.markdown("---")
    tela_fechamento_cmc_bahia()
    st.stop()

if _perfil_atual == "ADMIN":
    if st.button("🏭 Fechamento CMC Bahia", key="abrir_cmc_bahia", type="primary"):
        st.session_state["pagina_portal_rh"] = "CMC_BAHIA"
        st.rerun()

with st.expander("💰 Regras de Gratificação", expanded=False):
    tela_regras_gratificacao()

with st.expander("🧮 :red-background[**APURAÇÃO DE GRATIFICAÇÃO**]", expanded=False):
    tela_apuracao_gratificacao()

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

# Inclui também colaboradores desligados que ainda pertenciam ao quadro em algum
# momento do mês selecionado. Após a data de desligamento, a grade mostra DEM.
try:
    _todos_cad = sb("GET", "rh_colaboradores", "select=*") or []
    _fim_mes_ref = date(int(ano), mes, calendar.monthrange(int(ano), mes)[1])
    _ids_ativos = {int(c["id"]) for c in colaboradores if c.get("id") is not None}
    for _c in _todos_cad:
        if _c.get("id") is None or int(_c["id"]) in _ids_ativos:
            continue
        _dd = pd.to_datetime(_c.get("data_desligamento"), errors="coerce")
        if pd.notna(_dd) and _dd.date() <= _fim_mes_ref:
            # Só é necessário exibir no mês em que ocorreu o desligamento.
            if _dd.year == int(ano) and _dd.month == mes:
                colaboradores.append(_c)
    colaboradores = sorted(colaboradores, key=lambda r: _nome_colaborador(r).upper())
except Exception:
    pass

ocorrencias = ler_ocorrencias()
ocorrencia_id_por_codigo = {str(x.get("codigo") or "").upper().strip(): int(x["id"]) for x in ocorrencias if x.get("codigo") and x.get("id") is not None}
ocorrencia_codigo_por_id = {v: k for k, v in ocorrencia_id_por_codigo.items()}
codigos = [str(x.get("codigo","")).upper().strip() for x in ocorrencias if x.get("codigo")]
codigos = list(dict.fromkeys(codigos))
# Marcador visual para células ainda não preenchidas.
# O valor é apenas visual: internamente continua sendo tratado como vazio.
PENDENTE_VISUAL = "🟧 PENDENTE"
DEM_VISUAL = "DEM"

def _codigo_grade(valor):
    texto = str(valor or "").strip()
    if texto.lower() in ("none", "nan") or texto == PENDENTE_VISUAL:
        return ""
    return texto.upper()

# O marcador laranja aparece como primeira opção nas células pendentes.
# DEM aparece apenas quando o sistema o aplica automaticamente.
# A validação abaixo impede que DEM seja usado manualmente em qualquer outra data.
opcoes = [PENDENTE_VISUAL] + codigos + [DEM_VISUAL]

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

# Filtros VISUAIS da grade. Não alteram cadastro, indicadores ou dados salvos.
# A busca pode ser feita por qualquer parte do nome do colaborador.
_colaboradores_todos = list(colaboradores)
_col_busca, _col_status = st.columns([2, 1], gap="medium")
with _col_busca:
    # Busca em tempo real: atualiza a grade a cada digitação (debounce curto),
    # sem exigir Enter. Ao apagar o texto, a lista completa volta automaticamente.
    if st_keyup is not None:
        _busca_colaborador = (st_keyup(
            "🔎 Buscar colaborador",
            value="",
            placeholder="Digite parte do nome...",
            key=f"rh_busca_colaborador_{int(ano)}_{mes}",
            debounce=180,
        ) or "").strip()
    else:
        st.error(
            "A busca instantânea precisa do pacote streamlit-keyup. "
            "Adicione `streamlit-keyup` ao requirements.txt do projeto."
        )
        _busca_colaborador = st.text_input(
            "🔎 Buscar colaborador",
            value="",
            placeholder="Digite parte do nome...",
            key=f"rh_busca_colaborador_{int(ano)}_{mes}_fallback",
        ).strip()
with _col_status:
    _filtro_status = st.selectbox(
        "Filtrar por STATUS",
        ["TODOS", "OPERACIONAL", "OUTROS"],
        index=0,
        key=f"rh_filtro_status_{int(ano)}_{mes}",
    )

_colaboradores_filtrados = _colaboradores_todos
if _filtro_status != "TODOS":
    _colaboradores_filtrados = [
        c for c in _colaboradores_filtrados
        if _classificacao_colaborador(c) == _filtro_status
    ]

if _busca_colaborador:
    _termo = _busca_colaborador.casefold()
    _colaboradores_filtrados = [
        c for c in _colaboradores_filtrados
        if _termo in _nome_colaborador(c).casefold()
    ]

colaboradores = _colaboradores_filtrados
if _busca_colaborador and not colaboradores:
    st.info(f'Nenhum colaborador encontrado para "{_busca_colaborador}" com o filtro selecionado.')


# Acesso rápido à ficha individual. O campo é pesquisável e não interfere no filtro da grade.
_ficha_col1, _ficha_col2 = st.columns([4, 1], gap="medium")
with _ficha_col1:
    _mapa_ficha = {_nome_colaborador(c): c for c in _colaboradores_todos}
    _nome_ficha = st.selectbox(
        "👤 Ficha / ocorrências do colaborador",
        options=list(_mapa_ficha.keys()),
        index=None,
        placeholder="Selecione ou digite o nome do colaborador...",
        key=f"rh_ficha_colaborador_{int(ano)}_{mes}",
    )
with _ficha_col2:
    st.write("")
    st.write("")
    if st.button("Abrir ficha", use_container_width=True, disabled=not bool(_nome_ficha), key=f"rh_abrir_ficha_{int(ano)}_{mes}"):
        abrir_ficha_colaborador(_mapa_ficha[_nome_ficha])

# Área de análises recolhível para manter a tela principal compacta.
_analises_expander = st.expander("📊 Análises de Frequência", expanded=False)
with _analises_expander:
    # Duas colunas: resumo compacto à esquerda e gráfico à direita.
    _col_resumo, _col_grafico = st.columns([1, 4], gap="large")
    with _col_resumo:
        st.markdown("##### Resumo por Função")
        # Este filtro é independente do filtro geral da grade. Por padrão, mostra OPERACIONAL.
        _filtro_status_resumo = st.selectbox(
            "Status do resumo",
            ["OPERACIONAL", "OUTROS", "TODOS"],
            index=0,
            key=f"rh_filtro_status_resumo_{int(ano)}_{mes}",
        )
        if _filtro_status_resumo == "TODOS":
            _colaboradores_resumo = _colaboradores_todos
        else:
            _colaboradores_resumo = [
                c for c in _colaboradores_todos
                if _classificacao_colaborador(c) == _filtro_status_resumo
            ]
        _resumo_funcoes = (
            pd.DataFrame({"FUNÇÃO": [str(c.get("funcao") or c.get("funcao_padrao") or "SEM FUNÇÃO").strip() or "SEM FUNÇÃO" for c in _colaboradores_resumo]})
            .value_counts("FUNÇÃO")
            .reset_index(name="QTD")
            .sort_values(["QTD", "FUNÇÃO"], ascending=[False, True])
            .reset_index(drop=True)
        )
        st.dataframe(_resumo_funcoes, use_container_width=True, hide_index=True, height=500)
    with _col_grafico:
        # O gráfico é preenchido depois da grade para considerar também alterações ainda não salvas.
        _rankings_topo = st.container()

linhas = []
ids = []
for c in colaboradores:
    cid = int(c["id"])
    ids.append(cid)
    row = {
        "COLABORADOR": _nome_colaborador(c),
        # Classificação usada na Média de Colaboradores. Apenas OPERACIONAL entra no cálculo.
        "STATUS": _classificacao_colaborador(c),
        "FUNÇÃO": str(c.get("funcao") or c.get("funcao_padrao") or ""),
        # Na grade usa a empresa real da BaseFuncionário e exibe o nome abreviado.
        "EMPRESA": _empresa_colaborador(c, visual=True),
    }
    _deslig = pd.to_datetime(c.get("data_desligamento"), errors="coerce")
    _deslig = _deslig.date() if pd.notna(_deslig) else None
    for dia in range(1, ultimo_visivel + 1):
        _data_cel = date(int(ano), mes, dia)
        if _deslig and _data_cel > _deslig:
            row[f"{dia:02d}"] = DEM_VISUAL
        else:
            row[f"{dia:02d}"] = mapa.get((cid, dia), "") or PENDENTE_VISUAL
    linhas.append(row)

df = pd.DataFrame(linhas)
colunas_dia = [f"{d:02d}" for d in range(1, ultimo_visivel + 1)]

# Mapa estável de nomes por ID. Modais não devem depender da posição/colunas
# do data_editor, pois o Streamlit pode reconstruir o editor durante um rerun.
_nomes_grade_por_id = {int(c["id"]): _nome_colaborador(c) for c in colaboradores}
_desligamento_por_id = {}
for _c in colaboradores:
    _dd = pd.to_datetime(_c.get("data_desligamento"), errors="coerce")
    _desligamento_por_id[int(_c["id"])] = _dd.date() if pd.notna(_dd) else None
def _nome_grade_por_cid(cid, fallback=""):
    return str(_nomes_grade_por_id.get(int(cid), fallback or "")).strip()

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
# A grade filtrada precisa ter estado próprio. Caso contrário, ao pesquisar um nome,
# o rascunho da grade completa pode ser reutilizado com índices diferentes e o
# salvamento deixa de identificar corretamente a célula alterada.
import hashlib
_escopo_visual = ",".join(str(x) for x in ids)
_escopo_hash = hashlib.sha1(_escopo_visual.encode("utf-8")).hexdigest()[:12]
_draft_key = f"rh_grade_draft_{_periodo_key}_{_escopo_hash}"
_nonce_key = f"rh_grade_nonce_{_periodo_key}_{_escopo_hash}"
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
        _draft.at[_row, _col] = _cancelar.get("antes", "") or PENDENTE_VISUAL
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
    key=f"rh_grade_{ano}_{mes}_{_escopo_hash}_{st.session_state[_nonce_key]}",
    height=min(820, 72 + max(1, len(df))*35),
)
# Mantém o que está visualmente na grade como rascunho oficial.
st.session_state[_draft_key] = editado.copy()

# Conta diretamente o que está aparecendo na grade, inclusive alterações ainda não salvas.
contagens = {"FA": 0, "A": 0, "FO": 0, "OK": 0, "LB": 0, "COMP": 0}
for coluna in colunas_dia:
    for valor in editado[coluna].tolist():
        codigo = _codigo_grade(valor)
        if codigo in contagens:
            contagens[codigo] += 1

# Ranking combinado por colaborador — Faltas x Atestados.
# Obedece ao filtro TODOS / OPERACIONAL / OUTROS e considera também alterações ainda não salvas.
_rank_ocorrencias = []
for _i in range(len(editado)):
    _nome = _nome_grade_por_cid(ids[_i], df.iloc[_i]["COLABORADOR"] if "COLABORADOR" in df.columns else "")
    _qtd_fa = 0
    _qtd_a = 0
    for _col in colunas_dia:
        _codigo = _codigo_grade(editado.iloc[_i][_col])
        if _codigo == "FA":
            _qtd_fa += 1
        elif _codigo == "A":
            _qtd_a += 1
    if (_qtd_fa + _qtd_a) > 0:
        _rank_ocorrencias.append({
            "COLABORADOR": _nome,
            "FALTAS": _qtd_fa,
            "ATESTADOS": _qtd_a,
            "TOTAL": _qtd_fa + _qtd_a,
        })

_rank_ocorrencias = pd.DataFrame(
    _rank_ocorrencias,
    columns=["COLABORADOR", "FALTAS", "ATESTADOS", "TOTAL"],
)
if not _rank_ocorrencias.empty:
    _rank_ocorrencias = (
        _rank_ocorrencias
        .sort_values(["TOTAL", "COLABORADOR"], ascending=[False, True])
        .head(10)
    )

with _rankings_topo:
    st.markdown("##### 📊 Faltas x Atestados por Colaborador")
    if _rank_ocorrencias.empty:
        st.caption("Nenhuma falta ou atestado registrado no período.")
    else:
        # Barras verticais realmente coladas por colaborador.
        # Usamos coordenadas contínuas (x/x2) para eliminar o espaço entre FALTA e ATESTADO.
        _ordem_rank = _rank_ocorrencias["COLABORADOR"].tolist()
        _linhas_chart = []
        for _idx, _r in _rank_ocorrencias.reset_index(drop=True).iterrows():
            _centro = float(_idx)
            _falta = int(_r["FALTAS"])
            _atestado = int(_r["ATESTADOS"])
            if _falta > 0:
                _linhas_chart.append({
                    "COLABORADOR": _r["COLABORADOR"], "TIPO": "FALTAS", "QTD": _falta,
                    "X0": _centro - 0.28, "X1": _centro, "XC": _centro - 0.14,
                })
            if _atestado > 0:
                _linhas_chart.append({
                    "COLABORADOR": _r["COLABORADOR"], "TIPO": "ATESTADOS", "QTD": _atestado,
                    "X0": _centro, "X1": _centro + 0.28, "XC": _centro + 0.14,
                })
        _grafico_rank = pd.DataFrame(_linhas_chart)
        _tick_vals = [float(i) for i in range(len(_ordem_rank))]
        _label_expr = "datum.value >= 0 && datum.value < %d ? %s[datum.value] : ''" % (
            len(_ordem_rank), repr(_ordem_rank).replace("'", '"')
        )
        _xscale = alt.Scale(domain=[-0.5, max(0.5, len(_ordem_rank) - 0.5)], nice=False)

        _barras_rank = alt.Chart(_grafico_rank).mark_bar().encode(
            x=alt.X("X0:Q", scale=_xscale, axis=alt.Axis(values=_tick_vals, labelExpr=_label_expr, labelAngle=-35, labelLimit=160, title=None)),
            x2="X1:Q",
            y=alt.Y("QTD:Q", title="Quantidade", axis=alt.Axis(tickMinStep=1, format="d")),
            color=alt.Color(
                "TIPO:N", title=None,
                scale=alt.Scale(domain=["FALTAS", "ATESTADOS"], range=["#E53935", "#FB8C00"]),
                legend=alt.Legend(orient="bottom"),
            ),
            tooltip=[
                alt.Tooltip("COLABORADOR:N", title="Colaborador"),
                alt.Tooltip("TIPO:N", title="Tipo"),
                alt.Tooltip("QTD:Q", title="Quantidade", format="d"),
            ],
        )
        _rotulos_rank = alt.Chart(_grafico_rank).mark_text(
            dy=-8, fontSize=13, fontWeight="bold", color="#333333"
        ).encode(
            x=alt.X("XC:Q", scale=_xscale, axis=None),
            y=alt.Y("QTD:Q"),
            text=alt.Text("QTD:Q", format="d"),
        )
        _chart_rank = (_barras_rank + _rotulos_rank).properties(height=300).configure_view(strokeWidth=0)
        st.altair_chart(_chart_rank, use_container_width=True)

# Média de Colaboradores — sempre considera TODOS os OPERACIONAIS, independentemente do filtro visual.
# Soma FO + FA + OK + A de todos os OPERACIONAIS em todos os dias até hoje e divide pelos dias transcorridos.
_codigos_recebiveis = {"FO", "FA", "OK", "A"}
_total_recebiveis = 0
# Mapa com o que está salvo; depois sobrepomos o que estiver visível/pendente na grade atual.
_mapa_media = dict(mapa)
for i, cid in enumerate(ids):
    for dia in range(1, ultimo_visivel + 1):
        _mapa_media[(cid, dia)] = _codigo_grade(editado.iloc[i][f"{dia:02d}"])
for _c in _colaboradores_todos:
    if _classificacao_colaborador(_c) != "OPERACIONAL":
        continue
    _cid = int(_c["id"])
    for _dia in range(1, ultimo_visivel + 1):
        if _codigo_grade(_mapa_media.get((_cid, _dia), "")) in _codigos_recebiveis:
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
    k7.metric("Média de Colaboradores", f"{_media_diaria:.2f}".replace(".", ","))

    # Quadro compacto do efetivo cadastrado. Independente do filtro visual da grade.
    _qtd_registrados = len(_colaboradores_todos)
    _qtd_operacionais = sum(1 for _c in _colaboradores_todos if _classificacao_colaborador(_c) == "OPERACIONAL")
    _qtd_outros = sum(1 for _c in _colaboradores_todos if _classificacao_colaborador(_c) == "OUTROS")
    st.markdown(
        f"**👥 Colaboradores** &nbsp;&nbsp; | &nbsp;&nbsp; "
        f"**Registrados:** {_qtd_registrados} &nbsp;&nbsp; "
        f"**Operacionais:** {_qtd_operacionais} &nbsp;&nbsp; "
        f"**Outros:** {_qtd_outros}",
        unsafe_allow_html=True,
    )

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
        antes = _codigo_grade(df.iloc[i][col])
        depois = _codigo_grade(editado.iloc[i][col])
        _data_cel = date(int(ano), mes, dia)
        _dd = _desligamento_por_id.get(int(cid))
        _deve_ser_dem = bool(_dd and _data_cel > _dd)
        if _deve_ser_dem:
            # DEM é automático e imutável.
            if depois != DEM_VISUAL:
                editado.at[i, col] = DEM_VISUAL
            continue
        if depois == DEM_VISUAL:
            # DEM nunca pode ser lançado manualmente.
            editado.at[i, col] = df.iloc[i][col]
            continue
        if antes != depois:
            alteracoes.append((i, cid, dia, antes, depois))

if alteracoes:
    st.markdown("#### Alterações pendentes")
    st.warning(
        f"⚠️ Existem **{len(alteracoes)} alteração(ões) ainda não gravada(s)**. "
        "Enquanto não clicar em **💾 Salvar alterações**, relatórios e a tela de Gratificação continuarão usando o valor anterior salvo no banco."
    )

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
                _draft.at[int(alvo["row"]), str(alvo["col"])] = alvo.get("antes", "") or PENDENTE_VISUAL
                st.session_state[_draft_key] = _draft
            st.session_state[_nonce_key] = int(st.session_state.get(_nonce_key, 0)) + 1

    @st.dialog("🔒 Alteração de lançamento salvo", on_dismiss=_cancelar_edicao_salva)
    def modal_senha_edicao(i, cid, dia, antes, depois, chave_reg):
        nome = _nome_grade_por_cid(cid)
        st.markdown(f"**{nome}**")
        st.caption(f"Dia {dia:02d} • {antes} → {depois or 'PENDENTE'}")
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
            nome = _nome_grade_por_cid(cid)
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
                valor_check = _codigo_grade(editado.iloc[i][col_check])
                if not valor_check:
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
                    trilha = f"ALTERAÇÃO {antes or 'PENDENTE'} -> {depois or 'PENDENTE'} | MOTIVO: {motivo_ed}"
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
            novo_destra = st.text_input("DESTRA")
            novo_salario = st.number_input("Salário base (R$)", min_value=0.0, step=0.01, value=0.0)
        with cc2:
            nova_funcao = st.text_input("Função")
            nova_empresa = st.text_input("Empresa", value="10 SUL")
            nova_frente = st.selectbox("Frente", ["", "REVISÃO", "ITR", "SOS", "CNP", "BORRACHARIA", "CAPD", "FABRICAÇÃO", "CRAVEJAMENTO"])
            nova_equipe = st.selectbox("Equipe da Revisão", ["", "EQUIPE 1", "EQUIPE 2"], help="Preencha somente para colaboradores da frente REVISÃO.")

        incluir = st.form_submit_button("➕ Cadastrar colaborador", type="primary")
        if incluir:
            try:
                cadastrar_colaborador(novo_nome, nova_funcao, novo_cracha, nova_empresa, novo_salario or None, nova_frente or None, novo_destra or None, nova_equipe or None)
                st.success("Colaborador cadastrado com sucesso.")
                st.rerun()
            except Exception as e:
                st.error(f"Não foi possível cadastrar: {e}")

    st.markdown("#### Gerenciar colaboradores")
    if st.session_state.get("rh_salarios_ref_erro"):
        st.warning("Salário-base ainda não disponível no banco. Execute o SQL de atualização do Supabase uma única vez e recarregue a página.")
    st.caption("Altere o status e/ou a data de desligamento diretamente na tabela. Se houver data de desligamento, ela prevalece: do dia seguinte em diante a frequência será DEM, mesmo que o status ainda esteja ATIVO.")

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
        if "salario_base" not in cadastro_df.columns:
            cadastro_df["salario_base"] = None
        if "frente" not in cadastro_df.columns:
            cadastro_df["frente"] = None
        if "destra" not in cadastro_df.columns:
            cadastro_df["destra"] = None
        if "equipe_revisao" not in cadastro_df.columns:
            cadastro_df["equipe_revisao"] = None

        cols_editor = [c for c in [
            "id", "cracha", "destra", "colaborador", "funcao", "empresa", "salario_base", "frente", "equipe_revisao",
            "status", "data_desligamento"
        ] if c in cadastro_df.columns]

        original_status = {
            str(r["id"]): str(r.get("status") or ("ATIVO" if r.get("ativo", True) else "INATIVO")).upper()
            for r in todos_cadastro
        }
        original_salario = {str(r["id"]): (float(r.get("salario_base")) if r.get("salario_base") not in (None, "") else None) for r in todos_cadastro}
        original_frente = {str(r["id"]): str(r.get("frente") or "").strip().upper() for r in todos_cadastro}
        original_destra = {str(r["id"]): str(r.get("destra") or "").strip() for r in todos_cadastro}
        original_equipe = {str(r["id"]): ("" if pd.isna(r.get("equipe_revisao")) else str(r.get("equipe_revisao") or "").strip().upper()) for r in todos_cadastro}
        original_desligamento = {}
        for r in todos_cadastro:
            _dd = pd.to_datetime(r.get("data_desligamento"), errors="coerce")
            original_desligamento[str(r["id"])] = _dd.date() if pd.notna(_dd) else None

        editado = st.data_editor(
            cadastro_df[cols_editor],
            use_container_width=True,
            hide_index=True,
            disabled=[c for c in cols_editor if c not in ("status", "data_desligamento", "salario_base", "frente", "equipe_revisao", "destra")],
            column_config={
                "id": st.column_config.NumberColumn("ID"),
                "cracha": st.column_config.TextColumn("Crachá"),
                "destra": st.column_config.TextColumn("DESTRA"),
                "colaborador": st.column_config.TextColumn("Colaborador"),
                "funcao": st.column_config.TextColumn("Função"),
                "empresa": st.column_config.TextColumn("Empresa"),
                "salario_base": st.column_config.NumberColumn("Salário base (R$)", min_value=0.0, step=0.01, format="R$ %.2f"),
                "frente": st.column_config.SelectboxColumn("Frente", options=["REVISÃO", "ITR", "SOS", "CNP", "BORRACHARIA", "CAPD", "FABRICAÇÃO", "CRAVEJAMENTO"], required=False),
                "equipe_revisao": st.column_config.SelectboxColumn("Equipe Revisão", options=["EQUIPE 1", "EQUIPE 2"], required=False),
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

            data_desl = linha.get("data_desligamento")
            _nova_dd = pd.to_datetime(data_desl, errors="coerce")
            nova_dd = _nova_dd.date() if pd.notna(_nova_dd) else None
            dd_antiga = original_desligamento.get(cid)

            # A data também é uma alteração válida mesmo que o status continue ATIVO.
            # Isso permite programar/registrar o desligamento e já aplicar DEM na frequência.
            salario_val = linha.get("salario_base")
            try:
                novo_salario = None if pd.isna(salario_val) else round(float(salario_val), 2)
            except Exception:
                novo_salario = None
            salario_antigo = original_salario.get(cid)
            nova_frente = str(linha.get("frente") or "").strip().upper()
            frente_antiga = original_frente.get(cid, "")
            nova_destra = str(linha.get("destra") or "").strip()
            destra_antiga = original_destra.get(cid, "")
            equipe_val = linha.get("equipe_revisao")
            nova_equipe = "" if pd.isna(equipe_val) else str(equipe_val or "").strip().upper()
            if nova_equipe in ("NAN", "NONE", "NULL"):
                nova_equipe = ""
            equipe_antiga = original_equipe.get(cid, "")
            if nova_frente != "REVISÃO":
                nova_equipe = ""
            # Informar data de desligamento torna o colaborador INATIVO automaticamente.
            if nova_dd is not None:
                novo_status = "INATIVO"
            mudou = (novo_status != status_antigo) or (nova_dd != dd_antiga) or (novo_salario != salario_antigo) or (nova_frente != frente_antiga) or (nova_destra != destra_antiga) or (nova_equipe != equipe_antiga)
            if mudou:
                if novo_status == "INATIVO" and nova_dd is None:
                    erros.append(str(linha.get("colaborador") or cid))
                else:
                    alteracoes.append((linha, novo_status, nova_dd, novo_salario, nova_frente, nova_destra, nova_equipe))

        if erros:
            st.warning(
                "Informe a data de desligamento para: " + ", ".join(erros)
            )

        revisao_sem_equipe = [str(linha.get("colaborador") or linha.get("id")) for linha, _, _, _, nova_frente, _, nova_equipe in alteracoes if nova_frente == "REVISÃO" and nova_equipe not in ("EQUIPE 1", "EQUIPE 2")]
        if revisao_sem_equipe:
            st.warning("Selecione EQUIPE 1 ou EQUIPE 2 para os colaboradores da frente REVISÃO: " + ", ".join(revisao_sem_equipe))

        if alteracoes:
            if st.button("💾 Salvar alterações do colaborador", type="primary", disabled=bool(revisao_sem_equipe)):
                try:
                    for linha, novo_status, data_desl, novo_salario, nova_frente, nova_destra, nova_equipe in alteracoes:
                        ativo_novo = novo_status == "ATIVO"
                        alterar_status_colaborador(linha["id"], ativo_novo, data_desl)
                        sb("PATCH", "rh_colaboradores", "id=eq." + urllib.parse.quote(str(linha["id"])), {"salario_base": novo_salario, "frente": nova_frente or None, "destra": nova_destra or None, "equipe_revisao": nova_equipe or None}, "return=minimal")
                    st.success("Cadastro atualizado com sucesso.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Não foi possível atualizar o cadastro: {e}")
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
