"""Confirmação obrigatória antes de salvar desligamentos no cadastro."""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import urllib.parse
import pandas as pd
import streamlit as st

def data_iso(value):
    if value is None or pd.isna(value): return None
    return pd.to_datetime(value).date().isoformat()

def exige_motivo(novo_status, nova_data, anterior):
    return novo_status == 'INATIVO' and (
        bool(anterior.get('ativo', True)) or
        str(anterior.get('status') or 'ATIVO').upper() != 'INATIVO' or
        data_iso(nova_data) != data_iso(anterior.get('data_desligamento'))
    )

def validar_motivos(alteracoes, originais, motivos):
    for linha, status, data, *_ in alteracoes:
        cid = str(linha['id'])
        if exige_motivo(status, data, originais[cid]):
            info = motivos.get(cid, {})
            if not str(info.get('motivo') or '').strip():
                raise ValueError(f"Informe o motivo do desligamento de {linha['colaborador']}.")
            if not info.get('data'):
                raise ValueError(f"Informe a data de desligamento de {linha['colaborador']}.")

def abrir_modal(alteracoes, originais, salvar):
    pendentes = [a for a in alteracoes if exige_motivo(a[1], a[2], originais[str(a[0]['id'])])]

    @st.dialog('Registrar desligamento', width='large')
    def modal():
        st.caption('O desligamento só será salvo após confirmar o motivo. Fechar ou cancelar mantém o cadastro salvo anteriormente.')
        infos = {}
        with st.form('rh_form_desligamentos'):
            for linha, status, data, *_ in pendentes:
                cid = str(linha['id'])
                st.markdown(f"**{linha['colaborador']}**")
                d = st.date_input('Data de desligamento *', value=data or datetime.now(ZoneInfo('America/Sao_Paulo')).date(), key='rh_desl_data_' + cid)
                motivo = st.text_area('Motivo do desligamento *', key='rh_desl_motivo_' + cid, max_chars=2000)
                obs = st.text_area('Observações adicionais', key='rh_desl_obs_' + cid, max_chars=4000)
                infos[cid] = {'data': d, 'motivo': motivo.strip(), 'observacao': obs.strip()}
            c1, c2 = st.columns(2)
            confirmar = c1.form_submit_button('Confirmar e salvar alterações', type='primary')
            cancelar = c2.form_submit_button('Cancelar')
        if cancelar:
            st.rerun()
        if confirmar:
            try:
                validar_motivos(alteracoes, originais, infos)
                salvar(infos)
            except Exception as exc:
                st.error(f'Não foi possível salvar: {exc}')
    modal()

def payload_desligamento(info, usuario_id):
    return {
        'ativo': False, 'status': 'INATIVO', 'data_desligamento': data_iso(info['data']),
        'motivo_desligamento': info['motivo'].strip(),
        'observacao_desligamento': info.get('observacao', '').strip() or None,
        'desligamento_registrado_em': datetime.now(timezone.utc).isoformat(),
        'desligamento_registrado_por': usuario_id,
    }
