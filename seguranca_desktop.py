"""Interface local dos dois módulos. Credencial de sincronização restrita, nunca service_role."""
import os,json,hashlib,hmac,base64,secrets,urllib.request,ctypes
from pathlib import Path
import streamlit as st
from rh_riscos_local import BaseLocal
from rh_dna_local import DNALocal
ENDPOINT='https://rpkbosftqdtbubrqrtjq.supabase.co/functions/v1/seguranca-offline'
ROOT=Path(os.environ.get('LOCALAPPDATA') or Path.home())/'10Sul'/'Seguranca'
ROOT.mkdir(parents=True,exist_ok=True)

def protect(data,decode=False):
    if os.name!='nt':return data
    from ctypes import wintypes
    class BLOB(ctypes.Structure):_fields_=[('cbData',wintypes.DWORD),('pbData',ctypes.POINTER(ctypes.c_byte))]
    buf=ctypes.create_string_buffer(data);source=BLOB(len(data),ctypes.cast(buf,ctypes.POINTER(ctypes.c_byte)));target=BLOB()
    fn=ctypes.windll.crypt32.CryptUnprotectData if decode else ctypes.windll.crypt32.CryptProtectData
    ok=fn(ctypes.byref(source),None,None,None,None,1,ctypes.byref(target))
    if not ok:raise OSError('Não foi possível proteger a ativação neste usuário Windows.')
    try:return ctypes.string_at(target.pbData,target.cbData)
    finally:ctypes.windll.kernel32.LocalFree(target.pbData)

def call(body,token=''):
    req=urllib.request.Request(ENDPOINT,data=json.dumps(body,ensure_ascii=False,allow_nan=False).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+token},method='POST')
    try:
        with urllib.request.urlopen(req,timeout=30) as r:return json.load(r)
    except urllib.error.HTTPError as e:
        try:msg=json.loads(e.read())['error']
        except Exception:msg='Conexão não autorizada.'
        raise RuntimeError(msg) from None

st.set_page_config(page_title='10 SUL • Portal da Segurança Offline',page_icon='🦺',layout='wide')
st.title('10 SUL | Portal da Segurança do Trabalho')
st.caption('Base principal neste computador • DNA e Mapa de riscos • Sincronização offline → online')
config_path=ROOT/'ativacao.dat'
try:cfg=json.loads(protect(config_path.read_bytes(),True)) if config_path.exists() else None
except Exception:cfg=None
if not st.session_state.get('desktop_auth'):
    st.subheader('Entrar no sistema instalado')
    st.caption('Na primeira ativação, conecte à internet e use o mesmo usuário e senha do Portal da Segurança. Depois, o acesso funciona sem internet neste computador.')
    with st.form('acesso_local'):
        username=st.text_input('Usuário',value=cfg['usuario']['usuario'] if cfg else '')
        password=st.text_input('Senha',type='password')
        renovar=st.checkbox('Renovar ativação / sessão de sincronização pela internet',value=not bool(cfg))
        enter=st.form_submit_button('Entrar',type='primary')
    if enter:
        try:
            if not cfg or renovar:
                dados=call({'action':'login','usuario':username,'senha':password})
                salt=secrets.token_bytes(16);digest=hashlib.pbkdf2_hmac('sha256',password.encode(),salt,300000).hex()
                new={'usuario':dados['usuario'],'token':dados['token'],'salt':salt.hex(),'hash':digest}
                b=BaseLocal(ROOT/'seguranca.sqlite3',dados['riscos']);dna=DNALocal(b);dna.importar(dados)
                # Existing local records remain primary when renewing activation.
                config_path.write_bytes(protect(json.dumps(new).encode()));os.chmod(config_path,0o600);cfg=new
            elif username.strip().lower()!=cfg['usuario']['usuario'].lower() or not hmac.compare_digest(hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(cfg['salt']),300000).hex(),cfg['hash']):
                raise ValueError('Usuário ou senha inválidos.')
            st.session_state['desktop_auth']=cfg;st.rerun()
        except Exception as e:st.error(str(e))
    st.stop()
cfg=st.session_state['desktop_auth'];base=BaseLocal(ROOT/'seguranca.sqlite3');dna=DNALocal(base)
def remote(method,tabela,params='',payload=None,prefer=None):
    return call({'action':'data','method':method,'tabela':tabela,'params':params,'payload':payload},cfg['token'])['result']
@st.fragment(run_every=30)
def sync():
    total=base.pendentes()+dna.pendentes();a,b=st.columns([4,1]);a.caption(f"{cfg['usuario']['nome']} • {total} alteração(ões) aguardando publicação")
    manual=b.button('Sincronizar agora')
    if total or manual:
        try:
            n,c=base.sincronizar(remote);nd,cd=dna.sincronizar(remote)
            if c or cd:st.warning('Conflitos preservados localmente: '+', '.join(map(str,c+cd))+'. O online foi alterado separadamente; nenhum desses registros foi sobrescrito.')
            elif n+nd:st.success(f'{n+nd} alterações publicadas no online.')
            elif manual:st.info('Sem alterações pendentes.')
        except Exception as e:st.warning('Salvo neste computador. Publicação pendente: '+str(e)+'. Nova tentativa em 30 segundos com o aplicativo aberto. Se a sessão expirou, saia e marque Renovar ativação.')
sync()
if st.sidebar.button('Sair'):st.session_state.clear();st.rerun()
st.sidebar.caption('Banco local: '+str(ROOT))
area=st.sidebar.radio('Área da Segurança',['Controle de DNA','Mapa de riscos e plano preventivo'])
if area=='Controle de DNA':
    from rh_dna_offline import tela
    tela(dna,cfg['usuario'])
else:
    from rh_riscos import tela_riscos
    tela_riscos(base,cfg['usuario'])
