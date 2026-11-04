"""Executar localmente: python -m streamlit run seguranca_offline.py"""
import json, os, urllib.request
from pathlib import Path
import streamlit as st
from rh_riscos_local import BaseLocal

st.set_page_config(page_title='10 Sul • Segurança Offline',page_icon='🦺',layout='wide')
raiz=Path(__file__).resolve().parent
seed=json.loads((raiz/'base_inicial.json').read_text(encoding='utf-8')) if (raiz/'base_inicial.json').exists() else []
base=BaseLocal(raiz/'dados'/'seguranca.sqlite3',seed)

def config(nome):
    try:return str(st.secrets[nome]).strip()
    except Exception:return os.environ.get(nome,'').strip()

def remote(method,tabela,params='',payload=None,prefer=None):
    url,key=config('SUPABASE_URL'),config('SUPABASE_SERVICE_KEY')
    if not url or not key:raise RuntimeError('Configure a conexão em .streamlit/secrets.toml para publicar no online. O trabalho local continua disponível.')
    req=urllib.request.Request(url.rstrip('/')+'/rest/v1/'+tabela+('?' + params if params else ''),
        data=json.dumps(payload,ensure_ascii=False,allow_nan=False).encode() if payload is not None else None,method=method,
        headers={'apikey':key,'Authorization':'Bearer '+key,'Content-Type':'application/json',**({'Prefer':prefer} if prefer else {})})
    with urllib.request.urlopen(req,timeout=10) as r:
        b=r.read();return json.loads(b) if b else None

st.title('🦺 Segurança do Trabalho — base principal offline')
st.caption('Salva primeiro neste computador. O online recebe as alterações; dados locais não são substituídos automaticamente por dados do online.')
nome=st.text_input('Responsável por este computador / lançamentos',key='operador_local')
@st.fragment(run_every=30)
def sync():
    st.write(f'Alterações pendentes de publicação: {base.pendentes()}')
    manual=st.button('Sincronizar offline → online agora')
    if (config('SUPABASE_URL') and config('SUPABASE_SERVICE_KEY') and base.pendentes()) or manual:
        try:
            n,conflitos=base.sincronizar(remote)
            if conflitos:st.warning('Conflito no online. Alterações mantidas localmente. IDs: '+', '.join(map(str,conflitos))+'. Não houve sobrescrita. Revise com o responsável antes de sincronizar esses itens.')
            elif n:st.success(f'{n} alterações publicadas no online.')
            else:st.info('Nenhuma alteração pendente.')
        except Exception:
            st.warning('Online indisponível ou conexão não configurada. Alterações continuam salvas neste computador; nova tentativa em 30 segundos enquanto o aplicativo estiver aberto.')
sync()
if not nome.strip():
    st.info('Informe o responsável para abrir o mapa local.')
    st.stop()
from rh_riscos import tela_riscos
tela_riscos(base,{'perfil':'SEGURANCA','nome':nome.strip()})
