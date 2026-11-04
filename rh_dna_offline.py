from datetime import date,datetime,timezone
from io import BytesIO
import pandas as pd
import streamlit as st

def prazo(ano,mes):return date(ano+1,1,10) if mes==12 else date(ano,mes+1,10)
def excel(df):
    from openpyxl import Workbook
    from openpyxl.styles import Font,PatternFill
    from openpyxl.worksheet.table import Table,TableStyleInfo
    w=Workbook();s=w.active;s.title='DNA';s.append(['DESTRA','COLABORADOR','DNA'])
    for r in df.to_dict('records'):s.append([r['DESTRA'],r['COLABORADOR'],'X'*int(r['DNA'])])
    if len(df):
        t=Table(displayName='TabelaDNA',ref=f'A1:C{len(df)+1}');t.tableStyleInfo=TableStyleInfo(name='TableStyleMedium2',showRowStripes=True);s.add_table(t)
    s.column_dimensions['A'].width=16;s.column_dimensions['B'].width=60;s.column_dimensions['C'].width=15;s.freeze_panes='A2'
    out=BytesIO();w.save(out);return out.getvalue()
def tela(base,usuario):
    st.subheader('Controle de DNA')
    a,b,c=st.columns([1,1,2]);mes=a.selectbox('Mês',range(1,13),index=date.today().month-1);ano=int(b.number_input('Ano',2025,2100,date.today().year));comp=f'{ano:04d}-{mes:02d}-01'
    fechado=date.today()>=prazo(ano,mes)
    st.caption(f'Mínimo: 2 DNAs por colaborador. Prazo: {prazo(ano,mes):%d/%m/%Y}.')
    if fechado:st.warning('Competência fechada. Liberação excepcional deve ser feita no Portal RH com autorização do RH/Administrador; não é liberada automaticamente no offline.')
    colabs=base.colaboradores();regs=base.dna(comp);qtd={r['colaborador_id']:r['quantidade'] for r in regs}
    rows=[{'ID':r['id'],'DESTRA':str(r.get('destra') or ''),'COLABORADOR':r['colaborador'],'DNA':qtd.get(r['id'],0),'STATUS':'APTO' if qtd.get(r['id'],0)>=2 else 'NÃO ATENDE'} for r in colabs if r.get('ativo',True)]
    if not rows:st.info('Ative o computador com internet para carregar os colaboradores.');return
    df=pd.DataFrame(rows)
    x,y,z=st.columns(3);x.metric('Colaboradores',len(df));y.metric('Aptos',int((df.DNA>=2).sum()));z.metric('Pendentes',int((df.DNA<2).sum()))
    busca=st.text_input('Buscar colaborador');pendentes=st.checkbox('Somente pendentes de DNA')
    view=df[df.COLABORADOR.str.contains(busca,case=False,regex=False)].copy()
    if pendentes:view=view[view.DNA<2]
    with st.form('dna_'+comp):
        ed=st.data_editor(view,hide_index=True,use_container_width=True,disabled=list(df.columns) if fechado else ['ID','DESTRA','COLABORADOR','STATUS'],column_config={'ID':None,'DNA':st.column_config.NumberColumn('DNA',min_value=0,max_value=1000,step=1,required=True)},key='dna_editor_'+comp+'_'+str(base.dna_versao()))
        salvar=st.form_submit_button('Salvar DNA neste computador',disabled=fechado)
    if salvar:
        try:
            n=base.salvar_dna(ed.to_dict('records'),comp,usuario['nome']);st.success(f'{n} alterações salvas no computador.');st.rerun()
        except Exception as e:st.error(str(e))
    st.download_button('Exportar Excel',excel(df),'DNA_'+comp[:7]+'.xlsx','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
