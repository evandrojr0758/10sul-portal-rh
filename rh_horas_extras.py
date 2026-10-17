"""Solicitação de horas extras com acesso restrito ao link do supervisor."""
from datetime import date, datetime, time, timedelta
from decimal import Decimal, ROUND_HALF_UP
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


def preparar_linhas(data, solicitante, selecionados, cadastro, solicitacao_id, finalidade_atuacao, lideranca_id=None):
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
    if lideranca_id is None or int(lideranca_id) not in mapa:
        raise ValueError('Selecione quem é a liderança à frente da equipe neste dia.')
    lideranca = mapa[int(lideranca_id)]
    linhas = []
    for cid in dict.fromkeys(selecionados):
        if int(cid) not in mapa:
            raise ValueError('Um colaborador não está mais ativo. Atualize a seleção.')
        c = mapa[int(cid)]
        linhas.append({'solicitacao_id': str(solicitacao_id), 'data': data.isoformat(),
                       'lideranca_id': int(lideranca_id), 'lideranca': str(lideranca['colaborador']).strip(),
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
    liderancas = list(dict.fromkeys(str(r.get('Liderança') or 'Não informada').strip() for r in validas))
    solicitantes = list(dict.fromkeys(str(r.get('Solicitação de quem?') or 'Não informado').strip() for r in validas))
    datas = list(dict.fromkeys(str(r.get('Data') or '') for r in validas))
    atuacoes = list(dict.fromkeys(str(r.get('Finalidade / Onde vai atuar?') or 'Não informado').strip() for r in validas))
    resumo = resumo_por_funcao(validas)
    partes = ['*Liderança:* ' + ', '.join(liderancas),
              '*Data:* ' + ', '.join(datas),
              '*Solicitado por:* ' + ', '.join(solicitantes),
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
        st.dataframe(pd.DataFrame(recibo['linhas']).assign(**{'Liderança': [r.get('Liderança') or 'Não informada' for r in recibo['linhas']], 'Finalidade / Onde vai atuar?': [r.get('Finalidade / Onde vai atuar?') or 'Não informado' for r in recibo['linhas']]})[['Liderança', 'Data', 'Solicitação de quem?', 'Colaborador', 'Função', 'Finalidade / Onde vai atuar?']],
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
            for key in ('he_recibo', 'he_data', 'he_solicitante', 'he_selecionados', 'he_protocolo', 'he_finalidade_atuacao', 'he_lideranca_id'):
                st.session_state.pop(key, None)
            st.rerun()
        return
    st.write('Informe a liderança à frente da equipe, a data e quem solicitou a hora extra. Depois, selecione os colaboradores.')
    data = st.date_input('Data', value=hoje(), format='DD/MM/YYYY', key='he_data')
    solicitante = st.text_input('Solicitação de quem?', max_chars=200, key='he_solicitante',
                               placeholder='Ex.: Suzano',
                               help='Quem solicitou a hora extra. A liderança da equipe é selecionada separadamente abaixo.')
    mapa = {int(c['id']): c for c in cadastro}
    lideranca_id = st.selectbox('Liderança do dia — quem está à frente da equipe', list(mapa),
        index=None, placeholder='Selecione a liderança responsável neste dia', key='he_lideranca_id',
        format_func=lambda cid: f"{mapa[cid]['colaborador']} • {mapa[cid].get('funcao') or 'Não cadastrada'} (#{cid})",
        help='Seleção obrigatória. A liderança não é incluída automaticamente na quantidade de colaboradores; selecione-a também na lista abaixo se for realizar hora extra.')
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
    st.caption('Após registrar a solicitação, use “Enviar resumo pelo WhatsApp” para compartilhar o resumo com o nome da liderança primeiro.')
    st.session_state.setdefault('he_protocolo', str(uuid.uuid4()))
    if st.button('Enviar solicitação ao RH', type='primary', use_container_width=True):
        try:
            # Relê o cadastro no envio: preserva o vínculo e a função atuais.
            atuais = sb('GET', 'rh_colaboradores',
                        'select=id,colaborador,funcao,ativo&ativo=eq.true&order=colaborador.asc') or []
            linhas = preparar_linhas(data, solicitante, selecionados, atuais, st.session_state['he_protocolo'], finalidade_atuacao, lideranca_id)
            novos = sb('POST', 'rh_horas_extras', 'on_conflict=data,colaborador_id', linhas,
                       'resolution=ignore-duplicates,return=representation') or []
            repetidos = len(linhas) - len(novos)
            mensagem = f'Solicitação registrada! {len(novos)} colaborador(es) enviado(s) ao RH.'
            if repetidos:
                mensagem += f' {repetidos} já estava(m) registrado(s) nesta data e não foi(ram) duplicado(s).'
            st.session_state['he_recibo'] = {'mensagem': mensagem,
                'protocolo': st.session_state['he_protocolo'],
                'linhas': [{'Liderança': r.get('lideranca') or 'Não informada', 'Data': data.strftime('%d/%m/%Y'), 'Solicitação de quem?': r['solicitante'],
                            'Colaborador': r['colaborador'], 'Função': r['funcao'],
                            'Finalidade / Onde vai atuar?': r.get('finalidade_atuacao') or 'Não informado'} for r in novos]}
            if not novos:
                st.session_state['he_recibo']['linhas'] = [{'Data': data.strftime('%d/%m/%Y'),
                    'Liderança': mapa[lideranca_id]['colaborador'], 'Solicitação de quem?': solicitante.strip(), 'Colaborador': 'Todos já registrados nesta data',
                    'Função': 'Nenhuma nova inclusão', 'Finalidade / Onde vai atuar?': finalidade_atuacao.strip()}]
            st.rerun()
        except ValueError as exc:
            st.warning(str(exc))
        except Exception:
            st.error('Não foi possível confirmar o envio. Seus dados foram mantidos; tente enviar novamente.')



TARIFAS_R10 = {'50': '116.90', '100': '155.87', '200': '311.74'}


def apurar_horas(data, entrada1='', saida1='', entrada2='', saida2='', especial=False, tarifas=None):
    """Apura minutos por dia/faixa, sem cobrar o intervalo e sem arredondar horas."""
    data = date.fromisoformat(data) if isinstance(data, str) else data
    tarifas = tarifas or TARIFAS_R10
    minutos = {'50': 0, '100': 0, '200': 0}
    sabado_antes = sabado_depois = 0
    anterior = None
    for entrada, saida in ((entrada1, saida1), (entrada2, saida2)):
        if not entrada and not saida:
            continue
        if not entrada or not saida:
            raise ValueError('Preencha a entrada e a saída de cada período utilizado.')
        try:
            ini_h = datetime.strptime(str(entrada).strip(), '%H:%M').time()
            fim_h = datetime.strptime(str(saida).strip(), '%H:%M').time()
        except ValueError:
            raise ValueError('Use horários no formato HH:MM, por exemplo 08:00.')
        dia = anterior.date() if anterior else data
        ini = datetime.combine(dia, ini_h)
        if anterior and ini < anterior:
            raise ValueError('A entrada 2 deve ser igual ou posterior à saída 1.')
        fim = datetime.combine(dia, fim_h)
        if fim == ini:
            raise ValueError('A entrada e a saída não podem ser iguais.')
        if fim < ini:
            fim += timedelta(days=1)
        if fim > datetime.combine(data + timedelta(days=1), time(23, 59)):
            raise ValueError('Confira os horários: a apuração excede o dia seguinte.')
        anterior = fim
        atual = ini
        while atual < fim:
            if atual.weekday() == 5:
                corte = datetime.combine(atual.date(), time(12))
                antes = atual < corte
                limite = corte if antes else datetime.combine(atual.date() + timedelta(days=1), time())
                faixa = '100' if antes else '200'
            else:
                limite = datetime.combine(atual.date() + timedelta(days=1), time())
                faixa = '200' if atual.weekday() == 6 else '50'
            trecho = min(fim, limite)
            qtd = int((trecho - atual).total_seconds() // 60)
            if atual.weekday() == 5:
                if antes:
                    sabado_antes += qtd
                else:
                    sabado_depois += qtd
            minutos['200' if especial else faixa] += qtd
            atual = trecho
    valores = {k: (Decimal(v) * Decimal(str(tarifas[k])) / 60).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
               for k, v in minutos.items()}
    return {'minutos': minutos, 'total_minutos': sum(minutos.values()),
            'sabado_ate_12': sabado_antes, 'sabado_apos_12': sabado_depois,
            'valores': valores, 'valor': sum(valores.values())}


def hhmm(minutos):
    return f'{minutos // 60:02d}:{minutos % 60:02d}'


def reais(valor):
    return 'R$ ' + f'{valor:,.2f}'.replace(',', '_').replace('.', ',').replace('_', '.')


def calculo_registro(r):
    a = r.get('apuracao') or {}
    c = apurar_horas(r['data'], *(a.get(k, '') for k in ('entrada1', 'saida1', 'entrada2', 'saida2')),
                     especial=a.get('especial', False), tarifas=a.get('tarifas'))
    c.update(calcular_desconto(c['valor'], a.get('desconto', '0'), a.get('desconto_total', False)))
    return c


def calcular_desconto(bruto, desconto='0', total=False):
    desconto = Decimal(str(desconto)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    if not desconto.is_finite() or desconto < 0:
        raise ValueError('O desconto deve ser um valor válido maior ou igual a zero.')
    if total:
        desconto = bruto
    if desconto > bruto:
        raise ValueError('O desconto não pode ultrapassar o valor bruto da hora extra.')
    return {'desconto': desconto, 'liquido': bruto - desconto}



def editar_apuracao(sb, registros):
    st.markdown('#### Conferência do ponto — editar horários e descontos')
    st.caption('Informe somente os períodos de hora extra. O intervalo entre os períodos não é cobrado. '
               'Saída menor que a entrada indica término no dia seguinte. Feriado ou folga trabalhada usa 200% em todas as horas informadas. '
               'Os quatro horários permanecem editáveis após salvar: selecione o colaborador e a data para corrigir conforme o ponto eletrônico.')
    mapa = {r['id']: r for r in registros}
    rid = st.selectbox('Colaborador / data para lançar ou editar horários', list(mapa),
        format_func=lambda k: f"{date.fromisoformat(mapa[k]['data']).strftime('%d/%m/%Y')} — {mapa[k]['colaborador']} — {mapa[k]['funcao']}")
    r = mapa[rid]
    a = r.get('apuracao') or {}
    with st.form(f'he_apuracao_{rid}_{r.get("apuracao_versao", 0)}'):
        cols = st.columns(4)
        campos = ('entrada1', 'saida1', 'entrada2', 'saida2')
        labels = ('Entrada 1', 'Saída 1', 'Entrada 2', 'Saída 2')
        horarios = [col.text_input(label, value=a.get(campo, ''), max_chars=5, placeholder='HH:MM')
                    for col, campo, label in zip(cols, campos, labels)]
        especial = st.checkbox('Feriado ou folga trabalhada (200% + DSR)', value=a.get('especial', False))
        desconto_total = st.checkbox('Desconto total — zerar o valor a cobrar', value=a.get('desconto_total', False),
            help='Mantém os horários e as horas apuradas, mas desconta 100% do valor bruto deste colaborador nesta data.')
        desconto = st.number_input('Desconto (R$)', min_value=0.0, value=float(a.get('desconto') or 0), step=0.01, format='%.2f',
            help='Para desconto parcial, informe o valor em reais. Com desconto total marcado, o sistema usa todo o valor bruto.')
        motivo_desconto = st.text_input('Motivo do desconto', value=a.get('motivo_desconto', ''), max_chars=1000,
            placeholder='Ex.: Ajuste após conferência no ponto eletrônico')
        salvar = st.form_submit_button('Calcular e salvar horários', type='primary')
    if salvar:
        try:
            calculo = apurar_horas(r['data'], *horarios, especial=especial, tarifas=a.get('tarifas'))
            calculo.update(calcular_desconto(calculo['valor'], desconto, desconto_total))
            if not calculo['total_minutos']:
                raise ValueError('Informe pelo menos um período de hora extra.')
            payload = dict(zip(campos, [h.strip() for h in horarios]))
            payload.update(especial=especial, tarifas=a.get('tarifas') or TARIFAS_R10.copy(),
                           desconto=str(Decimal(str(desconto))), desconto_total=desconto_total,
                           motivo_desconto=motivo_desconto.strip())
            versao = int(r.get('apuracao_versao') or 0)
            salvos = sb('PATCH', 'rh_horas_extras', f'id=eq.{rid}&apuracao_versao=eq.{versao}',
                {'apuracao': payload, 'apuracao_versao': versao + 1}, 'return=representation') or []
            if not salvos:
                st.warning('Este registro foi alterado em outra sessão. Atualize e confira antes de salvar novamente.')
            else:
                st.session_state['he_apuracao_salva'] = f"Horários salvos. Total: {hhmm(calculo['total_minutos'])} — Bruto: {reais(calculo['valor'])}; desconto: {reais(calculo['desconto'])}; valor final: {reais(calculo['liquido'])}."
                st.rerun()
        except ValueError as exc:
            st.warning(str(exc))
        except Exception:
            st.error('Não foi possível confirmar o salvamento. Os horários digitados foram mantidos; tente novamente.')
    if st.session_state.get('he_apuracao_salva'):
        st.success(st.session_state.pop('he_apuracao_salva'))
    with st.expander('🗑️ Excluir registro selecionado', expanded=False):
        data_registro = date.fromisoformat(r['data']).strftime('%d/%m/%Y')
        st.write(f"Colaborador: **{r['colaborador']}** • Data: **{data_registro}** • Função: **{r['funcao']}**")
        st.caption('Exclui somente a participação deste colaborador nesta data, incluindo horários e descontos. '
                   'O cadastro do colaborador e as demais solicitações permanecem salvos. Depois, você poderá lançar novamente nesta data.')
        versao = int(r.get('apuracao_versao') or 0)
        with st.form(f'he_excluir_{rid}_{versao}'):
            confirmar = st.checkbox('Confirmo a exclusão deste registro')
            excluir = st.form_submit_button('Excluir registro', type='secondary')
        if excluir:
            if not confirmar:
                st.warning('Marque a confirmação para excluir o registro selecionado.')
            else:
                try:
                    removidos = sb('DELETE', 'rh_horas_extras',
                        f'id=eq.{int(rid)}&apuracao_versao=eq.{versao}', prefer='return=representation') or []
                    if removidos:
                        st.session_state['he_exclusao_sucesso'] = f"Registro de {r['colaborador']} em {data_registro} excluído."
                        st.rerun()
                    else:
                        st.warning('O registro foi alterado ou já foi excluído em outra sessão. Atualize a lista antes de tentar novamente.')
                except Exception:
                    st.error('Não foi possível confirmar a exclusão. Atualize a lista para conferir e tente novamente.')


def tela_gestao(sb):
    st.subheader('⏱️ Solicitações de horas extras')
    if st.session_state.get('he_exclusao_sucesso'):
        st.success(st.session_state.pop('he_exclusao_sucesso'))
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
    editar_apuracao(sb, registros)
    st.markdown('#### Histórico de solicitações e apuração')
    tabela = pd.DataFrame([{'Data': date.fromisoformat(r['data']).strftime('%d/%m/%Y'),
        'Liderança': r.get('lideranca') or 'Não informada',
        'Solicitação de quem?': r['solicitante'], 'Colaborador': r['colaborador'],
        'Função': r['funcao'], 'Finalidade / Onde vai atuar?': r.get('finalidade_atuacao') or 'Não informado',
        'Protocolo': r['solicitacao_id'],
        'Registrado em': datetime.fromisoformat(r['criado_em']).astimezone(ZoneInfo('America/Sao_Paulo')).strftime('%d/%m/%Y %H:%M')}
        for r in registros])
    detalhes = []
    total = Decimal('0.00')
    bruto_total = desconto_periodo = Decimal('0.00')
    pendentes = 0
    for r in registros:
        a = r.get('apuracao') or {}
        c = calculo_registro(r)
        preenchido = c['total_minutos'] > 0
        if not preenchido:
            pendentes += 1
        bruto_total += c['valor']
        desconto_periodo += c['desconto']
        total += c['liquido']
        detalhes.append({
            'Entrada 1': a.get('entrada1', ''), 'Saída 1': a.get('saida1', ''),
            'Entrada 2': a.get('entrada2', ''), 'Saída 2': a.get('saida2', ''),
            'Total de horas': hhmm(c['total_minutos']) if preenchido else 'Pendente',
            'Horas sábado até 12h': hhmm(c['sabado_ate_12']),
            'Horas sábado após 12h': hhmm(c['sabado_apos_12']),
            'Horas 50%': hhmm(c['minutos']['50']),
            'Horas 100%': hhmm(c['minutos']['100']),
            'Horas 200%': hhmm(c['minutos']['200']),
            'Valor 50% (R$)': float(c['valores']['50']) if preenchido else None,
            'Valor 100% (R$)': float(c['valores']['100']) if preenchido else None,
            'Valor 200% (R$)': float(c['valores']['200']) if preenchido else None,
            'Valor bruto (R$)': float(c['valor']) if preenchido else None,
            'Desconto (R$)': float(c['desconto']) if preenchido else None,
            'Valor (R$)': float(c['liquido']) if preenchido else None,
            'Desconto total': 'Sim' if a.get('desconto_total') else 'Não',
            'Motivo do desconto': a.get('motivo_desconto', ''),
            'Feriado / Folga': 'Sim' if a.get('especial') else 'Não'})
    tabela = pd.concat([tabela, pd.DataFrame(detalhes)], axis=1)
    primeiras = ['Data', 'Colaborador', 'Função', 'Entrada 1', 'Saída 1', 'Entrada 2', 'Saída 2',
                 'Total de horas', 'Horas sábado até 12h', 'Horas sábado após 12h', 'Valor bruto (R$)', 'Desconto (R$)', 'Valor (R$)']
    tabela = tabela[primeiras + [col for col in tabela.columns if col not in primeiras]]
    bruto_card, desconto_card, liquido_card = st.columns(3)
    bruto_card.metric('Valor bruto no período', reais(bruto_total))
    desconto_card.metric('Descontos no período', reais(desconto_periodo))
    liquido_card.metric('Valor total apurado no período', reais(total))
    if pendentes:
        st.caption(f'{pendentes} registro(s) aguardando horários; não entram no valor total.')
    st.dataframe(tabela, hide_index=True, use_container_width=True,
        column_config={col: st.column_config.NumberColumn(col, format='R$ %.2f')
                       for col in tabela.columns if '(R$)' in col})
    excel = BytesIO()
    with pd.ExcelWriter(excel, engine='openpyxl') as writer:
        tabela.to_excel(writer, index=False, sheet_name='Horas extras')
        resumo.to_excel(writer, index=False, sheet_name='Resumo por função')
    st.download_button('📥 Exportar solicitações em Excel', excel.getvalue(),
        file_name=f'horas_extras_{inicio.isoformat()}_{fim.isoformat()}.xlsx',
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

