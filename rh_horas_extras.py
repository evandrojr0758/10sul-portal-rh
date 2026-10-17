"""Solicitação de horas extras com acesso restrito ao link do supervisor."""
from datetime import date, datetime
import calendar
from io import BytesIO
from urllib.parse import quote
from zoneinfo import ZoneInfo
import secrets
import uuid

import pandas as pd
import streamlit as st

BASE_URL = 'https://10sul-app-rh-jacpdfktaczhihbjnuucm2.streamlit.app/'


def hoje():
    return datetime.now(ZoneInfo('America/Sao_Paulo')).date()


def link_supervisor(sb):
    rows = sb('GET', 'rh_horas_extras_links', 'select=token&ativo=eq.true&order=criado_em.desc&limit=1') or []
    if not rows:
        token = secrets.token_urlsafe(32)
        rows = sb('POST', 'rh_horas_extras_links', '', {'token': token}, 'return=representation') or []
    return BASE_URL + '?horas_extras=' + quote(rows[0]['token'], safe='')


def preparar_linhas(data, solicitante, selecionados, cadastro, solicitacao_id, finalidade_atuacao):
    solicitante = str(solicitante or '').strip()
    if not solicitante:
        raise ValueError('Informe de quem é a solicitação.')
    if len(solicitante) > 200:
        raise ValueError('O nome do solicitante deve ter até 200 caracteres.')
    if not selecionados:
        raise ValueError('Selecione pelo menos um colaborador.')
    finalidade_atuacao = str(finalidade_atuacao or '').strip()
    if not finalidade_atuacao:
        raise ValueError('Informe a finalidade da hora extra e onde o colaborador vai atuar.')
    if len(finalidade_atuacao) > 2000:
        raise ValueError('A finalidade e o local devem ter até 2000 caracteres.')
    mapa = {int(c['id']): c for c in cadastro if c.get('ativo', True)}
    linhas = []
    for cid in dict.fromkeys(selecionados):
        if int(cid) not in mapa:
            raise ValueError('Um colaborador não está mais ativo. Atualize a seleção.')
        c = mapa[int(cid)]
        linhas.append({'solicitacao_id': str(solicitacao_id), 'data': data.isoformat(),
                       'solicitante': solicitante, 'finalidade_atuacao': finalidade_atuacao, 'colaborador_id': int(cid),
                       'colaborador': str(c['colaborador']).strip(),
                       'funcao': str(c.get('funcao') or '').strip() or 'Não cadastrada'})
    return linhas


def resumo_por_funcao(registros):
    """Conta pessoas distintas e participações por dia sem misturar os dois totais."""
    colunas = ['Função', 'Colaboradores', 'Participações (colaborador/dia)']
    if not registros:
        return pd.DataFrame(columns=colunas)
    linhas = [{'Função': str(r.get('funcao') or r.get('Função') or 'Não cadastrada').strip().upper() or 'NÃO CADASTRADA',
               'Pessoa': str(r.get('colaborador_id') or r.get('id') or r.get('colaborador') or r.get('Colaborador') or '')}
              for r in registros]
    base = pd.DataFrame(linhas)
    resumo = base.groupby('Função', as_index=False).agg(
        **{'Colaboradores': ('Pessoa', 'nunique'),
           'Participações (colaborador/dia)': ('Pessoa', 'size')})
    return resumo.sort_values(['Colaboradores', 'Função'], ascending=[False, True]).reset_index(drop=True)


def texto_resumo_envio(linhas):
    """Resumo dos colaboradores efetivamente registrados, pronto para compartilhar."""
    validas = [r for r in linhas if r.get('Função') != 'Nenhuma nova inclusão']
    if not validas:
        return ''
    liderancas = list(dict.fromkeys(str(r.get('Solicitação de quem?') or '').strip() for r in validas))
    datas = list(dict.fromkeys(str(r.get('Data') or '') for r in validas))
    atuacoes = list(dict.fromkeys(str(r.get('Finalidade / Onde vai atuar?') or 'Não informado').strip() for r in validas))
    resumo = resumo_por_funcao(validas)
    partes = ['*Liderança:* ' + ', '.join(liderancas),
              '*Data:* ' + ', '.join(datas),
              '', '*Colaboradores por função:*']
    partes.extend(f"• {r['Função']}: {int(r['Colaboradores'])}" for r in resumo.to_dict('records'))
    partes.extend(['*Total de colaboradores:* ' + str(int(resumo['Colaboradores'].sum())),
                   '', '*Atuando em:* ' + '; '.join(atuacoes)])
    return '\n'.join(partes)


def tela_supervisor(sb, token):
    st.title('⏱️ Solicitação de hora extra')
    st.caption('10 Sul • Portal RH • Supervisor')
    if not isinstance(token, str) or not 20 <= len(token) <= 100:
        st.error('Link de solicitação inválido. Solicite o link atualizado ao RH.')
        return
    try:
        permitido = sb('GET', 'rh_horas_extras_links',
                       'select=id&ativo=eq.true&token=eq.' + quote(token, safe='') + '&limit=1') or []
    except Exception:
        st.error('Não foi possível validar o acesso. Tente novamente em instantes.')
        return
    if not permitido:
        st.error('Este link não está disponível. Solicite o link atualizado ao RH.')
        return
    try:
        cadastro = sb('GET', 'rh_colaboradores',
                      'select=id,colaborador,funcao,ativo&ativo=eq.true&order=colaborador.asc') or []
    except Exception:
        st.error('Não foi possível carregar os colaboradores. Tente novamente.')
        return
    if not cadastro:
        st.info('Não há colaboradores ativos cadastrados no Portal RH.')
        return
    if st.session_state.get('he_recibo'):
        recibo = st.session_state['he_recibo']
        st.success(recibo['mensagem'])
        st.caption('Protocolo: ' + recibo['protocolo'])
        st.markdown('#### Resumo por função')
        st.dataframe(resumo_por_funcao([r for r in recibo['linhas'] if r.get('Função') != 'Nenhuma nova inclusão'])[['Função', 'Colaboradores']].rename(
            columns={'Colaboradores': 'Quantidade'}), hide_index=True, use_container_width=True)
        st.dataframe(pd.DataFrame(recibo['linhas']).assign(**{'Finalidade / Onde vai atuar?': [r.get('Finalidade / Onde vai atuar?') or 'Não informado' for r in recibo['linhas']]})[['Data', 'Solicitação de quem?', 'Colaborador', 'Função', 'Finalidade / Onde vai atuar?']],
                     hide_index=True, use_container_width=True)
        texto_envio = texto_resumo_envio(recibo['linhas'])
        if texto_envio:
            st.markdown('#### Resumo para envio')
            st.text(texto_envio.replace('*', ''))
            st.link_button('📲 Enviar resumo pelo WhatsApp',
                'https://wa.me/?text=' + quote(texto_envio, safe=''),
                type='primary', use_container_width=True)
            st.caption('Escolha o contato ou grupo no WhatsApp e confirme o envio.')
        if st.button('Nova solicitação', type='primary'):
            for key in ('he_recibo', 'he_data', 'he_solicitante', 'he_selecionados', 'he_protocolo', 'he_finalidade_atuacao'):
                st.session_state.pop(key, None)
            st.rerun()
        return
    st.write('Informe a data e o solicitante. Digite o nome para buscar e selecionar os colaboradores.')
    data = st.date_input('Data', value=hoje(), format='DD/MM/YYYY', key='he_data')
    solicitante = st.text_input('Solicitação de quem?', max_chars=200, key='he_solicitante',
                               placeholder='Nome de quem solicitou a hora extra')
    mapa = {int(c['id']): c for c in cadastro}
    selecionados = st.multiselect('Colaboradores — busque pelo nome', list(mapa),
        format_func=lambda cid: f"{mapa[cid]['colaborador']} • {mapa[cid].get('funcao') or 'Não cadastrada'} (#{cid})",
        key='he_selecionados', placeholder='Digite para buscar um ou mais colaboradores')
    if selecionados:
        st.markdown('#### Resumo por função')
        st.metric('Total de colaboradores selecionados', len(selecionados))
        st.dataframe(resumo_por_funcao([mapa[cid] for cid in selecionados])[['Função', 'Colaboradores']].rename(
            columns={'Colaboradores': 'Quantidade'}), hide_index=True, use_container_width=True)
        st.markdown('#### Colaboradores selecionados')
        st.dataframe(pd.DataFrame([{'Colaborador': mapa[cid]['colaborador'],
                                   'Função': mapa[cid].get('funcao') or 'Não cadastrada'}
                                  for cid in selecionados]), hide_index=True, use_container_width=True)
        st.caption(f'{len(selecionados)} colaborador(es) selecionado(s).')
    finalidade_atuacao = st.text_area('Finalidade da hora extra / Onde vai atuar?',
        key='he_finalidade_atuacao', max_chars=2000,
        placeholder='Ex.: Manutenção das carretas na oficina de Aracruz — revisão e troca de lonas.',
        help='Informe o serviço e o local de atuação dos colaboradores selecionados nesta solicitação.')
    st.caption('Após registrar a solicitação, use “Enviar resumo pelo WhatsApp” para compartilhar com a liderança primeiro.')
    st.session_state.setdefault('he_protocolo', str(uuid.uuid4()))
    if st.button('Enviar solicitação ao RH', type='primary', use_container_width=True):
        try:
            # Relê o cadastro no envio: preserva o vínculo e a função atuais.
            atuais = sb('GET', 'rh_colaboradores',
                        'select=id,colaborador,funcao,ativo&ativo=eq.true&order=colaborador.asc') or []
            linhas = preparar_linhas(data, solicitante, selecionados, atuais, st.session_state['he_protocolo'], finalidade_atuacao)
            novos = sb('POST', 'rh_horas_extras', 'on_conflict=data,colaborador_id', linhas,
                       'resolution=ignore-duplicates,return=representation') or []
            repetidos = len(linhas) - len(novos)
            mensagem = f'Solicitação registrada! {len(novos)} colaborador(es) enviado(s) ao RH.'
            if repetidos:
                mensagem += f' {repetidos} já estava(m) registrado(s) nesta data e não foi(ram) duplicado(s).'
            st.session_state['he_recibo'] = {'mensagem': mensagem,
                'protocolo': st.session_state['he_protocolo'],
                'linhas': [{'Data': data.strftime('%d/%m/%Y'), 'Solicitação de quem?': r['solicitante'],
                            'Colaborador': r['colaborador'], 'Função': r['funcao'],
                            'Finalidade / Onde vai atuar?': r.get('finalidade_atuacao') or 'Não informado'} for r in novos]}
            if not novos:
                st.session_state['he_recibo']['linhas'] = [{'Data': data.strftime('%d/%m/%Y'),
                    'Solicitação de quem?': solicitante.strip(), 'Colaborador': 'Todos já registrados nesta data',
                    'Função': 'Nenhuma nova inclusão', 'Finalidade / Onde vai atuar?': finalidade_atuacao.strip()}]
            st.rerun()
        except ValueError as exc:
            st.warning(str(exc))
        except Exception:
            st.error('Não foi possível confirmar o envio. Seus dados foram mantidos; tente enviar novamente.')


def tela_gestao(sb):
    st.subheader('⏱️ Solicitações de horas extras')
    st.caption('Os registros permanecem salvos. Consulte qualquer período nas datas abaixo, inclusive meses anteriores.')
    st.markdown('#### Valores de hora extra — Proposta Comercial R10')
    st.caption('Referência: Proposta Comercial 030724 — Revisão 10, página 18, seção “Preço”. Valores com DSR incluído.')
    st.dataframe(pd.DataFrame([
        {'Tipo de hora extra': '50% + DSR',
         'Quando se aplica': 'Excedente de jornada de segunda a sexta-feira',
         'Valor': 'R$ 116,90'},
        {'Tipo de hora extra': '100% + DSR',
         'Quando se aplica': 'Excedente de jornada no sábado trabalhado até as 12h',
         'Valor': 'R$ 155,87'},
        {'Tipo de hora extra': '200% + DSR',
         'Quando se aplica': 'Sábado após as 12h, domingos, feriados e folgas trabalhadas',
         'Valor': 'R$ 311,74'},
    ]), hide_index=True, use_container_width=True)
    st.info('Cobrança para horas extras solicitadas pela contratante para serviços fora da programação gerados pela contratante. '
            'A autorização e a validação da responsabilidade devem ocorrer durante a execução das atividades, pela contratante e pela contratada.')

    with st.expander('🔗 Link para o supervisor', expanded=False):
        try:
            link = link_supervisor(sb)
            st.code(link, language=None)
            st.link_button('Abrir tela do supervisor', link)
        except Exception:
            st.error('Não foi possível carregar o link do supervisor.')
    a, b = st.columns(2)
    inicio = a.date_input('De', value=hoje().replace(day=1), format='DD/MM/YYYY', key='he_filtro_inicio')
    fim = b.date_input('Até', value=hoje().replace(day=calendar.monthrange(hoje().year, hoje().month)[1]), format='DD/MM/YYYY', key='he_filtro_fim')
    if inicio > fim:
        st.warning('A data inicial deve ser anterior ou igual à data final.')
        return
    st.button('Atualizar solicitações', key='he_atualizar')
    try:
        registros, offset = [], 0
        while True:
            pagina = sb('GET', 'rh_horas_extras',
                f'select=*&data=gte.{inicio.isoformat()}&data=lte.{fim.isoformat()}'
                f'&order=data.desc,colaborador.asc,id.asc&limit=1000&offset={offset}') or []
            registros.extend(pagina)
            if len(pagina) < 1000:
                break
            offset += len(pagina)
    except Exception:
        st.error('Não foi possível consultar as solicitações salvas. Tente atualizar novamente.')
        return
    pessoas = len({r['colaborador_id'] for r in registros})
    a, b = st.columns(2)
    a.metric('Colaboradores distintos no período', pessoas)
    b.metric('Participações (colaborador/dia)', len(registros))
    st.caption('Cada colaborador conta uma vez por função. Se trabalhar em vários dias, cada dia soma uma participação.')
    if not registros:
        st.info('Nenhuma solicitação registrada neste período.')
        return
    resumo = resumo_por_funcao(registros)
    st.markdown('#### Resumo por função — período selecionado')
    st.dataframe(resumo, hide_index=True, use_container_width=True)
    st.markdown('#### Histórico de solicitações')
    tabela = pd.DataFrame([{'Data': date.fromisoformat(r['data']).strftime('%d/%m/%Y'),
        'Solicitação de quem?': r['solicitante'], 'Colaborador': r['colaborador'],
        'Função': r['funcao'], 'Finalidade / Onde vai atuar?': r.get('finalidade_atuacao') or 'Não informado',
        'Protocolo': r['solicitacao_id'],
        'Registrado em': datetime.fromisoformat(r['criado_em']).astimezone(ZoneInfo('America/Sao_Paulo')).strftime('%d/%m/%Y %H:%M')}
        for r in registros])
    st.dataframe(tabela, hide_index=True, use_container_width=True)
    excel = BytesIO()
    with pd.ExcelWriter(excel, engine='openpyxl') as writer:
        tabela.to_excel(writer, index=False, sheet_name='Horas extras')
        resumo.to_excel(writer, index=False, sheet_name='Resumo por função')
    st.download_button('📥 Exportar solicitações em Excel', excel.getvalue(),
        file_name=f'horas_extras_{inicio.isoformat()}_{fim.isoformat()}.xlsx',
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

