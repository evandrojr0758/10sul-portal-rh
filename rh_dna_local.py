import json
from datetime import datetime,timezone
from urllib.parse import quote
from rh_riscos_local import canon
from rh_dna_offline import prazo
from datetime import date

class DNALocal:
    def __init__(self,base):
        self.base=base
        with base.db() as c:
            c.execute('CREATE TABLE IF NOT EXISTS dna (chave TEXT PRIMARY KEY,registro TEXT NOT NULL,remoto TEXT,pendente INTEGER NOT NULL DEFAULT 0)')
            c.execute('CREATE TABLE IF NOT EXISTS colaboradores (id INTEGER PRIMARY KEY,registro TEXT NOT NULL)')
    def importar(self,data):
        with self.base.db() as c:
            for r in data['colabs']:c.execute('INSERT OR REPLACE INTO colaboradores VALUES (?,?)',(r['id'],canon(r)))
            for r in data['dna']:
                k=f"{r['colaborador_id']}:{r['competencia']}"
                c.execute('INSERT OR IGNORE INTO dna VALUES (?,?,?,0)',(k,canon(r),canon(r)))
    def colaboradores(self):
        with self.base.db() as c:return [json.loads(r[0]) for r in c.execute('SELECT registro FROM colaboradores ORDER BY id')]
    def dna(self,comp):
        with self.base.db() as c:return [json.loads(r[0]) for r in c.execute('SELECT registro FROM dna') if json.loads(r[0])['competencia']==comp]
    def dna_versao(self):
        with self.base.db() as c:
            import hashlib
            return hashlib.sha256(str(c.execute('SELECT registro FROM dna ORDER BY chave').fetchall()).encode()).hexdigest()[:12]
    def salvar_dna(self,linhas,comp,autor):
        ano,mes=map(int,comp[:7].split('-'))
        if date.today()>=prazo(ano,mes):raise ValueError('Competência fechada.')
        n=0
        with self.base.db() as c:
            for r in linhas:
                q=r['DNA']
                if isinstance(q,bool) or int(q)!=q or not 0<=q<=1000:raise ValueError('Informe quantidade inteira entre 0 e 1000.')
                k=f"{int(r['ID'])}:{comp}";old=c.execute('SELECT registro FROM dna WHERE chave=?',(k,)).fetchone()
                if (json.loads(old[0])['quantidade'] if old else 0)==q:continue
                v={'colaborador_id':int(r['ID']),'competencia':comp,'quantidade':int(q),'atualizado_por':autor,'atualizado_em':datetime.now(timezone.utc).isoformat()}
                c.execute('INSERT INTO dna VALUES (?,?,NULL,1) ON CONFLICT(chave) DO UPDATE SET registro=excluded.registro,pendente=1',(k,canon(v)));n+=1
        return n
    def pendentes(self):
        with self.base.db() as c:return c.execute('SELECT COUNT(*) FROM dna WHERE pendente=1').fetchone()[0]
    def sincronizar(self,remote):
        enviados=0;conflitos=[]
        with self.base.db() as c:filas=c.execute('SELECT chave,registro,remoto FROM dna WHERE pendente=1').fetchall()
        for k,texto,anterior in filas:
            r=json.loads(texto);p=f"select=*&colaborador_id=eq.{r['colaborador_id']}&competencia=eq.{r['competencia']}"
            atual=(remote('GET','rh_dna_mensal',p) or [None])[0]
            esperado=json.loads(anterior) if anterior else None
            if atual and atual['quantidade']==r['quantidade'] and atual.get('atualizado_em')==r.get('atualizado_em'):resultado=[atual]
            elif atual and (not esperado or atual.get('atualizado_em')!=esperado.get('atualizado_em') or atual['quantidade']!=esperado['quantidade']):conflitos.append(k);continue
            elif atual:
                stamp=atual.get('atualizado_em');f=f"id=eq.{atual['id']}&atualizado_em="+('eq.'+quote(stamp,safe='') if stamp else 'is.null')
                resultado=remote('PATCH','rh_dna_mensal',f,r)
            else:resultado=remote('POST','rh_dna_mensal','',r)
            if not resultado:conflitos.append(k);continue
            with self.base.db() as c:
                row=c.execute('SELECT registro FROM dna WHERE chave=?',(k,)).fetchone()
                if row and row[0]==texto:c.execute('UPDATE dna SET registro=?,remoto=?,pendente=0 WHERE chave=?',(canon(resultado[0]),canon(resultado[0]),k))
                else:c.execute('UPDATE dna SET remoto=? WHERE chave=?',(canon(resultado[0]),k))
            enviados+=1
        return enviados,conflitos
