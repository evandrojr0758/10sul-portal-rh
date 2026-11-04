import sys,tempfile,json,copy
from pathlib import Path
from datetime import date
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from rh_riscos_local import BaseLocal,TABELA
from rh_dna_local import DNALocal
from rh_dna_offline import prazo,excel
import pandas as pd
with tempfile.TemporaryDirectory() as tmp:
    b=BaseLocal(Path(tmp)/'db.sqlite',[{'id':1,'dados':{'atividade':'A'},'atualizado_em':'v1'}]);d=DNALocal(b)
    d.importar({'colabs':[{'id':2,'colaborador':'TESTE','ativo':True}],'dna':[]})
    comp=date.today().replace(day=1).isoformat()
    assert d.salvar_dna([{'ID':2,'DNA':2}],comp,'Teste')==1
    assert DNALocal(BaseLocal(Path(tmp)/'db.sqlite')).dna(comp)[0]['quantidade']==2
    assert d.pendentes()==1 and b.pendentes()==0
    online=[]
    def remote(method,table,params='',payload=None,prefer=None):
        if method=='GET':return copy.deepcopy(online)
        if method=='POST':online.append(dict(payload,id=4));return copy.deepcopy(online)
        if method=='PATCH':online[0].update(payload);return copy.deepcopy(online)
    assert d.sincronizar(remote)==(1,[]) and d.pendentes()==0
    d.salvar_dna([{'ID':2,'DNA':3}],comp,'Teste');online[0]['quantidade']=9
    assert d.sincronizar(remote)==(0,['2:'+comp]) and d.pendentes()==1
    assert d.dna(comp)[0]['quantidade']==3
    b('PATCH',TABELA,'id=eq.1',{'dados':{'atividade':'B'},'atualizado_em':'v2'})
    assert b.pendentes()==1
    result=b.sincronizar(lambda *args:[{'id':1,'dados':{'atividade':'Online'},'atualizado_em':'v3'}])
    assert result==(0,[1]) and b('GET',TABELA)[0]['dados']['atividade']=='B'
assert prazo(2026,12)==date(2027,1,10)
assert excel(pd.DataFrame([{'DESTRA':'1','COLABORADOR':'Teste','DNA':2}])).startswith(b'PK')
print('OK: DNA + riscos, persistência local, sync e conflitos, prazo e Excel.')
