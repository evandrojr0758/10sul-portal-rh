"""Importação conferida e alertas de ASO e integrações do Portal RH."""
import hashlib
import io
import secrets
import unicodedata
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import pandas as pd
import streamlit as st

CAMPOS = {'venc_aso': 'Venc. ASO', 'venc_integracao_fabrica': 'Venc. integração fábrica', 'venc_integracao_unf': 'Venc. integração UNF Florestal'}

def nome_chave(value):
    return ' '.join(''.join(c for c in unicodedata.normalize('NFD', str(value or '')) if not unicodedata.combining(c)).upper().split())

def data_iso(value):
    if value is None or pd.isna(value) or str(value).strip() == '':
        return None
    if isinstance(value, (int, float)):
        return (date(1899, 12, 30) + timedelta(days=float(value))).isoformat()
    if isinstance(value, (date, datetime)):
        return value.strftime('%Y-%m-%d')
    return pd.to_datetime(str(value).strip(), dayfirst=not str(value).startswith(('19', '20')) or '/' in str(value), errors='raise').date().isoformat()

def ler_importacao(arquivos, colaboradores):
    indice = {}
    for c in colaboradores:
        indice.setdefault(nome_chave(c.get('colaborador')), []).append(c)
    grupos, problemas = {}, []
    for arquivo in arquivos:
        engine = 'xlrd' if arquivo.name.lower().endswith('.xls') else 'openpyxl'
        for aba, df in pd.read_excel(io.BytesIO(arquivo.getvalue()), sheet_name=None, engine=engine).items():
            cols = {nome_chave(c): c for c in df.columns}
            nome_col = cols.get('FUNCIONARIO') or cols.get('COLABORADOR')
            if not nome_col:
                problemas.append({'Arquivo': arquivo.name, 'Problema': f'Aba {aba}: coluna Funcionário ausente'})
                continue
            mapa = {}
            for chave, col in cols.items():
                if 'VENC' in chave and 'ASO' in chave: mapa[col] = 'venc_aso'
                elif 'VENC' in chave and 'UNF' in chave: mapa[col] = 'venc_integracao_unf'
                elif 'VENC' in chave and ('INT' in chave) and 'FABRICA' in chave: mapa[col] = 'venc_integracao_fabrica'
            if not mapa:
                problemas.append({'Arquivo': arquivo.name, 'Problema': f'Aba {aba}: vencimentos não reconhecidos'})
            for _, r in df.iterrows():
                if pd.isna(r[nome_col]): continue
                nome = str(r[nome_col]).strip()
                candidatos = indice.get(nome_chave(nome), [])
                if len(candidatos) != 1:
                    problemas.append({'Colaborador': nome, 'Problema': 'Nome não encontrado' if not candidatos else 'Nome ambíguo no cadastro'})
                    continue
                c = candidatos[0]
                for col, campo in mapa.items():
                    try: valor = data_iso(r[col])
                    except (ValueError, TypeError, OverflowError):
                        problemas.append({'Colaborador': nome, 'Problema': f'{CAMPOS[campo]}: data inválida ({r[col]})'})
                        continue
                    if valor:
                        g = grupos.setdefault((c['id'], campo), {'cadastro': c, 'valores': set()})
                        g['valores'].add(valor)
    propostas = []
    for (cid, campo), g in grupos.items():
        c = g['cadastro']; valores = sorted(g['valores'])
        propostas.append({'Importar': len(valores) == 1, 'ID': cid, 'Colaborador': c['colaborador'], 'Documento': CAMPOS[campo], 'Campo': campo, 'Atual': data_iso(c.get(campo)), 'Nova data': date.fromisoformat(valores[0]) if len(valores) == 1 else None, 'Conferência': 'Datas conflitantes: ' + ', '.join(date.fromisoformat(v).strftime('%d/%m/%Y') for v in valores) if len(valores) > 1 else 'Atualizar' if c.get(campo) != valores[0] else 'Sem alteração'})
    return propostas, problemas

def tela_importacao(sb):
    with st.expander('📥 Importar ASO e integrações (.xls / .xlsx)'):
        st.caption('Importe as duas planilhas juntas. Apenas as datas selecionadas serão atualizadas. Nomes não encontrados não criam colaboradores e células vazias não apagam datas existentes.')
        arquivos = st.file_uploader('Planilhas de vencimentos', type=['xls', 'xlsx'], accept_multiple_files=True, key='rh_import_venc')
        if not arquivos: return
        try:
            propostas, problemas = ler_importacao(arquivos, sb('GET', 'rh_colaboradores', 'select=*') or [])
        except Exception as exc:
            st.error(f'Não foi possível ler as planilhas: {exc}'); return
        if problemas:
            st.warning('Registros pendentes de conferência. Eles não serão importados automaticamente.')
            st.dataframe(pd.DataFrame(problemas).drop_duplicates(), hide_index=True, use_container_width=True)
        if not propostas: return
        df = pd.DataFrame(propostas)
        df['Nova data'] = pd.to_datetime(df['Nova data']).dt.date
        chave = hashlib.sha256(b''.join(a.getvalue() for a in arquivos)).hexdigest()
        ed = st.data_editor(df, hide_index=True, use_container_width=True, disabled=['ID', 'Colaborador', 'Documento', 'Campo', 'Atual', 'Conferência'], column_config={'Campo': None, 'Nova data': st.column_config.DateColumn('Nova data', format='DD/MM/YYYY'), 'Atual': st.column_config.TextColumn('Data atual'), 'Importar': st.column_config.CheckboxColumn('Importar')}, key='rh_venc_preview_' + chave)
        selecionados = ed[ed['Importar'] == True]
        invalidos = selecionados['Nova data'].isna().any()
        if invalidos: st.warning('Escolha uma data para cada registro selecionado, inclusive os conflitantes.')
        if st.button('Salvar vencimentos conferidos', disabled=selecionados.empty or invalidos, key='rh_venc_salvar'):
            feitos = 0
            try:
                # Reconsulta antes de escrever: não recria colaboradores excluídos.
                ids = {str(c['id']) for c in (sb('GET', 'rh_colaboradores', 'select=id') or [])}
                for cid, linhas in selecionados.groupby('ID'):
                    if str(cid) not in ids: raise ValueError(f'Colaborador ID {cid} não existe mais; confira novamente.')
                    payload = {r['Campo']: data_iso(r['Nova data']) for _, r in linhas.iterrows()}
                    sb('PATCH', 'rh_colaboradores', f'id=eq.{int(cid)}', payload, 'return=minimal')
                    feitos += len(payload)
                st.success(f'{feitos} vencimentos salvos. Reimportar o arquivo não duplica colaboradores.')
                st.rerun()
            except Exception as exc:
                st.error(f'{feitos} vencimentos salvos antes da interrupção. É seguro tentar novamente. Erro: {exc}')

def tela_alertas(sb, colaboradores):
    hoje = datetime.now(ZoneInfo('America/Sao_Paulo')).date()
    alertas = []
    for c in colaboradores:
        if not c.get('ativo') or str(c.get('status') or '').upper() == 'INATIVO': continue
        if c.get('data_desligamento') and data_iso(c['data_desligamento']) < hoje.isoformat(): continue
        for campo, label in CAMPOS.items():
            venc = data_iso(c.get(campo))
            if not venc: continue
            dias = (date.fromisoformat(venc) - hoje).days
            if dias <= 30:
                alertas.append({'Colaborador': c['colaborador'], 'Documento': label, 'Vencimento': date.fromisoformat(venc), 'Dias': dias, 'Situação': 'VENCIDO' if dias < 0 else 'VENCE HOJE' if dias == 0 else 'VENCE EM ATÉ 30 DIAS'})
    with st.expander(f'🔔 ASO e integrações — {len(alertas)} vencimento(s) em atenção', expanded=bool(alertas) or st.query_params.get('vencimentos') == '1'):
        st.caption('Posição atual, independente do mês da frequência. Alertas a partir de 30 dias antes do vencimento, incluindo vencidos e vencimentos de hoje. Somente colaboradores ativos.')
        if alertas:
            tabela = pd.DataFrame(alertas).sort_values(['Dias', 'Colaborador'])
            st.warning(f"{sum(a['Dias'] < 0 for a in alertas)} vencido(s) · {sum(a['Dias'] == 0 for a in alertas)} vence(m) hoje · {sum(a['Dias'] > 0 for a in alertas)} próximo(s) de vencer")
            st.dataframe(tabela, hide_index=True, use_container_width=True, column_config={'Vencimento': st.column_config.DateColumn(format='DD/MM/YYYY')})
        else: st.success('Nenhum vencimento informado está em atenção.')
        st.caption('Para receber com o portal fechado, ative os alertas neste celular e permita notificações no navegador. O aviso de 30 dias é enviado uma vez por documento/data, com novo aviso no vencimento.')
        if st.button('Preparar ativação de notificações no celular', key='rh_venc_push'):
            token = secrets.token_hex(32)
            try:
                sb('POST', 'rh_push_autorizacoes', '', {'token_hash': hashlib.sha256(token.encode()).hexdigest(), 'usuario_id': st.session_state['usuario_logado']['id'], 'expira_em': (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat()}, 'return=minimal')
                st.session_state['rh_venc_push_link'] = 'https://central-10sul.peachycrown16.chatgpt.site/#rh=' + token
            except Exception as exc: st.error(f'Não foi possível gerar a ativação: {exc}')
        if st.session_state.get('rh_venc_push_link'):
            st.link_button('Ativar alertas do Portal RH neste celular', st.session_state['rh_venc_push_link'])
            st.caption('Abra este link no celular, toque em “Ativar alertas do Portal RH” e aceite a permissão. O link expira em 30 minutos.')
