"""Sessões opacas persistentes; apenas hashes ficam no banco."""
import hashlib
import re
import secrets
from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components

_browser = components.declare_component('rh_sessao_browser', path=str(Path(__file__).parent / 'rh_session_component'))

def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()

def criar(sb, usuario):
    token = secrets.token_hex(32)
    rows = sb('GET', 'rh_usuarios', f'select=senha_hash&id=eq.{int(usuario["id"])}&limit=1')
    sb('POST', 'rh_sessoes', '', {'token_hash': token_hash(token), 'usuario_id': usuario['id'], 'senha_hash': rows[0]['senha_hash']}, 'return=minimal')
    st.session_state['rh_token'] = token
    _comando('write', token)

def recuperar(sb, token):
    if not isinstance(token, str) or not re.fullmatch(r'[a-f0-9]{64}', token):
        return None
    rows = sb('GET', 'rh_sessoes', 'select=usuario_id,senha_hash&token_hash=eq.' + token_hash(token) + '&limit=1') or []
    if not rows:
        return None
    sessao = rows[0]
    rows = sb('GET', 'rh_usuarios', f'select=id,usuario,nome,perfil,ativo,trocar_senha,senha_hash&id=eq.{int(sessao["usuario_id"])}&limit=1') or []
    if not rows or not rows[0].get('ativo') or not secrets.compare_digest(str(rows[0].get('senha_hash') or ''), sessao['senha_hash']):
        return None
    usuario = rows[0]
    usuario.pop('senha_hash', None)
    usuario['perfil'] = str(usuario.get('perfil') or '').upper()
    return usuario

def _comando(action, token=''):
    st.session_state['rh_browser_command'] = {'action': action, 'token': token, 'id': secrets.token_hex(12)}

def sair(sb):
    token = st.session_state.get('rh_token')
    if token:
        sb('DELETE', 'rh_sessoes', 'token_hash=eq.' + token_hash(token), prefer='return=minimal')
    st.session_state.clear()
    st.session_state['rh_browser_loaded'] = True
    _comando('clear')

def sincronizar(sb):
    command = st.session_state.get('rh_browser_command') or {'action': 'read', 'id': 'read'}
    result = _browser(command=command, key='rh_browser_session', default=None)
    if not result or result.get('id') != command['id']:
        st.caption('Restaurando acesso…' if command['action'] == 'read' else 'Atualizando acesso…')
        st.stop()
    if command['action'] != 'read':
        st.session_state.pop('rh_browser_command', None)
        st.session_state['rh_browser_loaded'] = True
        if result.get('error'):
            st.session_state['rh_storage_error'] = True
        st.rerun()
    if st.session_state.get('rh_browser_loaded'):
        return
    if result.get('error'):
        st.session_state['rh_storage_error'] = True
    token = result.get('token')
    if token and not st.session_state.get('usuario_logado'):
        try:
            usuario = recuperar(sb, token)
        except Exception:
            st.error('Não foi possível restaurar o acesso. Tente novamente.')
            if st.button('Tentar novamente'):
                st.rerun()
            st.stop()
        if usuario:
            st.session_state['usuario_logado'] = usuario
            st.session_state['rh_token'] = token
        else:
            _comando('clear')
            st.rerun()
    st.session_state['rh_browser_loaded'] = True
