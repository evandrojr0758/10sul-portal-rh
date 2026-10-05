import os, json, urllib.request, urllib.error
from datetime import datetime, date
import pandas as pd
import streamlit as st

st.set_page_config(page_title='Inspeções | 10 Sul', page_icon='⏱️', layout='wide')

def segredo(nome):
    try: return str(st.secrets[nome]).strip()
    except Exception: return os.getenv(nome, '').strip()

SUPABASE_URL=segredo('SUPABASE_URL').rstrip('/')
SUPABASE_SERVICE_KEY=segredo('SUPABASE_SERVICE_KEY')

def sb(method,tabela,params='',payload=None,prefer=None):
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise RuntimeError('Configure SUPABASE_URL e SUPABASE_SERVICE_KEY nos Secrets deste aplicativo.')
    url=f'{SUPABASE_URL}/rest/v1/{tabela}' + (('?' + params) if params else '')
    data=None if payload is None else json.dumps(payload,ensure_ascii=False,allow_nan=False).encode('utf-8')
    req=urllib.request.Request(url,data=data,method=method)
    req.add_header('apikey',SUPABASE_SERVICE_KEY); req.add_header('Authorization',f'Bearer {SUPABASE_SERVICE_KEY}'); req.add_header('Content-Type','application/json')
    if prefer: req.add_header('Prefer',prefer)
    try:
        with urllib.request.urlopen(req,timeout=30) as resp:
            raw=resp.read(); return json.loads(raw.decode('utf-8')) if raw else None
    except urllib.error.HTTPError as e:
        detalhe=e.read().decode('utf-8',errors='replace'); raise RuntimeError(f'Supabase HTTP {e.code}: {detalhe}') from e

def _impacto_para_horas(txt):
    partes=str(txt or '00:00').strip().split(':')
    if len(partes)!=2: raise ValueError('Informe o tempo de impacto no formato HH:MM.')
    hh=int(partes[0]); mm=int(partes[1])
    if hh < 0 or mm < 0 or mm > 59: raise ValueError('Informe o tempo de impacto no formato HH:MM.')
    return hh + mm/60

def salvar(carreta,equipe,inicio,fim,observacao,impacto_horas,registro_id=None):
    carreta=str(carreta or '').strip().upper()
    if not carreta: raise ValueError('Informe a carreta.')
    impacto=max(float(impacto_horas or 0),0)
    payload={'carreta':carreta,'equipe':equipe,'inicio':inicio.isoformat(),'observacao':str(observacao or '').strip() or None,'impacto_horas':round(impacto,6),'usuario_registro':'LANÇAMENTO INSPEÇÕES'}
    if fim is None:
        payload.update({'fim':None,'duracao_horas':None,'duracao_liquida_horas':None})
        horas=liquido=None
    else:
        if fim <= inicio: raise ValueError('O FIM deve ser posterior ao INÍCIO.')
        horas=(fim-inicio).total_seconds()/3600
        if impacto > horas: raise ValueError('O tempo de impacto não pode ser maior que o tempo total da inspeção.')
        liquido=horas-impacto
        payload.update({'fim':fim.isoformat(),'duracao_horas':round(horas,6),'duracao_liquida_horas':round(liquido,6)})
    if registro_id is None:
        sb('POST','rh_inspecoes_carretas','',payload,'return=minimal')
    else:
        sb('PATCH','rh_inspecoes_carretas',f'id=eq.{int(registro_id)}',payload,'return=minimal')
    return horas,liquido

def ler(ano,mes):
    ini=f'{ano:04d}-{mes:02d}-01T00:00:00'; prox=(pd.Timestamp(ano,mes,1)+pd.offsets.MonthBegin(1)).strftime('%Y-%m-%dT00:00:00')
    return sb('GET','rh_inspecoes_carretas',f'select=*&inicio=gte.{ini}&inicio=lt.{prox}&order=inicio.desc') or []

def excluir(i): sb('DELETE','rh_inspecoes_carretas',f'id=eq.{int(i)}')

def hhmm(v):
    if v is None: return '—'
    m=int(round(float(v)*60)); return f'{m//60:02d}:{m%60:02d}'

st.title('⏱️ Lançamento de Inspeções — Revisão 60 mil km')
st.caption('Registre a carreta, a equipe responsável e o início/fim da inspeção. As médias são enviadas automaticamente ao Portal RH.')
hoje=date.today(); meses=['Janeiro','Fevereiro','Março','Abril','Maio','Junho','Julho','Agosto','Setembro','Outubro','Novembro','Dezembro']

with st.form('nova',clear_on_submit=True):
    a,b=st.columns(2)
    carreta=a.text_input('CARRETA',placeholder='Ex.: 13633')
    equipe=b.selectbox('EQUIPE',['EQUIPE 1','EQUIPE 2'])
    c1,c2=st.columns(2)
    di=c1.date_input('INÍCIO — Data',value=hoje); hi=c2.time_input('INÍCIO — Hora')
    observacao=st.text_area('OBSERVAÇÃO / DESVIO',placeholder='Ex.: Aguardando peça, liberação, equipamento indisponível...')
    impacto_txt=st.text_input('TEMPO DE IMPACTO (HH:MM)',value='00:00',placeholder='Ex.: 02:30')
    st.caption('O FIM não é obrigatório na abertura. Depois, use ✏️ Editar lançamento para atualizar observações, impactos e finalizar a inspeção.')
    ok=st.form_submit_button('💾 Abrir inspeção',type='primary',use_container_width=True)
if ok:
    try:
        impacto_h=_impacto_para_horas(impacto_txt)
        salvar(carreta,equipe,datetime.combine(di,hi),None,observacao,impacto_h)
        st.success(f'Carreta {carreta.upper()} aberta como EM ANDAMENTO.'); st.rerun()
    except Exception as e: st.error(str(e))

st.divider(); st.subheader('📊 Acompanhamento')
a,b,c=st.columns([1.2,.8,2])
mes=a.selectbox('Mês',range(1,13),index=hoje.month-1,format_func=lambda x: meses[x-1]); ano=int(b.number_input('Ano',2025,2100,hoje.year,1)); c.markdown(f'### {meses[mes-1].upper()} / {ano}')
try: regs=ler(ano,mes)
except Exception as e: st.error(f'Não foi possível consultar os lançamentos: {e}'); st.stop()

for eq,col in zip(['EQUIPE 1','EQUIPE 2'],st.columns(2)):
    vals=[]
    for r in regs:
        if str(r.get('equipe','')).upper()==eq:
            try: vals.append(float(r.get('duracao_liquida_horas') if r.get('duracao_liquida_horas') is not None else r.get('duracao_horas')))
            except: pass
    with col:
        x,y=st.columns(2); x.metric(f'{eq} — Inspeções',len(vals)); y.metric('Média',hhmm(sum(vals)/len(vals) if vals else None))

if not regs: st.info('Nenhuma inspeção lançada nesta competência.')
else:
    dados=[]
    for r in regs:
        ini=pd.to_datetime(r.get('inicio'),errors='coerce'); fim=pd.to_datetime(r.get('fim'),errors='coerce')
        finalizada=pd.notna(fim)
        try: h=float(r.get('duracao_horas')) if r.get('duracao_horas') is not None else None
        except: h=(fim-ini).total_seconds()/3600 if pd.notna(ini) and pd.notna(fim) else None
        impacto=float(r.get('impacto_horas') or 0)
        try: liquido=float(r.get('duracao_liquida_horas')) if r.get('duracao_liquida_horas') is not None else (h-impacto if h is not None else None)
        except: liquido=None
        dados.append({'ID':r.get('id'),'CARRETA':r.get('carreta'),'EQUIPE':r.get('equipe'),'INÍCIO':ini.strftime('%d/%m/%Y %H:%M') if pd.notna(ini) else '','FIM':fim.strftime('%d/%m/%Y %H:%M') if finalizada else '','STATUS':'🟢 FINALIZADA' if finalizada else '🟡 EM ANDAMENTO','TEMPO TOTAL':hhmm(h),'IMPACTO':hhmm(impacto),'TEMPO LÍQUIDO':hhmm(liquido),'OBSERVAÇÃO / DESVIO':r.get('observacao') or '', '_raw':r})
    st.dataframe(pd.DataFrame([{k:v for k,v in x.items() if k not in ('ID','_raw')} for x in dados]),use_container_width=True,hide_index=True)

    with st.expander('✏️ Editar lançamento / finalizar inspeção', expanded=False):
        op={f"{x['CARRETA']} | {x['EQUIPE']} | {x['STATUS']} | {x['INÍCIO']}":x for x in dados}
        esc=st.selectbox('Lançamento para editar',list(op),key='editar_sel')
        item=op[esc]; raw=item['_raw']
        ini0=pd.to_datetime(raw.get('inicio'))
        fim0=pd.to_datetime(raw.get('fim'),errors='coerce')
        with st.form('editar_inspecao'):
            e1,e2=st.columns(2)
            car=e1.text_input('CARRETA',value=str(raw.get('carreta') or ''))
            eq=e2.selectbox('EQUIPE',['EQUIPE 1','EQUIPE 2'],index=0 if str(raw.get('equipe')).upper()=='EQUIPE 1' else 1)
            i1,i2=st.columns(2)
            edi=i1.date_input('INÍCIO — Data',value=ini0.date()); ehi=i2.time_input('INÍCIO — Hora',value=ini0.time().replace(second=0,microsecond=0))
            obs=st.text_area('OBSERVAÇÃO / DESVIO',value=str(raw.get('observacao') or ''),placeholder='Atualize os desvios ao longo da manutenção...')
            imp=st.text_input('TEMPO DE IMPACTO (HH:MM)',value=hhmm(float(raw.get('impacto_horas') or 0)).replace('—','00:00'))
            finalizar=st.checkbox('🟢 Informar FIM e finalizar esta inspeção',value=pd.notna(fim0))
            if finalizar:
                f1,f2=st.columns(2)
                base_fim=fim0 if pd.notna(fim0) else pd.Timestamp.now()
                edf=f1.date_input('FIM — Data',value=base_fim.date()); ehf=f2.time_input('FIM — Hora',value=base_fim.time().replace(second=0,microsecond=0))
            salvar_ed=st.form_submit_button('💾 Salvar alterações',type='primary',use_container_width=True)
        if salvar_ed:
            try:
                impacto_h=_impacto_para_horas(imp)
                fim_edit=datetime.combine(edf,ehf) if finalizar else None
                h,liq=salvar(car,eq,datetime.combine(edi,ehi),fim_edit,obs,impacto_h,registro_id=item['ID'])
                if fim_edit is None: st.success('Alterações salvas. A inspeção continua EM ANDAMENTO.')
                else: st.success(f'Inspeção FINALIZADA. Tempo total: {hhmm(h)} | Impacto: {hhmm(impacto_h)} | Tempo líquido: {hhmm(liq)}.')
                st.rerun()
            except Exception as e: st.error(str(e))

    with st.expander('🗑️ Excluir lançamento incorreto'):
        op_del={f"{x['CARRETA']} | {x['EQUIPE']} | {x['STATUS']} | {x['INÍCIO']}":x['ID'] for x in dados}
        esc_del=st.selectbox('Lançamento',list(op_del),key='excluir_sel')
        if st.button('Excluir lançamento'):
            try: excluir(op_del[esc_del]); st.success('Lançamento excluído.'); st.rerun()
            except Exception as e: st.error(str(e))

