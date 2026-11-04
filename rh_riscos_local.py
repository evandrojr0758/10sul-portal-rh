"""Base principal local SQLite, publicação no online com detecção de conflitos."""
import json, sqlite3, uuid, threading
from pathlib import Path
from datetime import datetime, timezone

TABELA = 'rh_seguranca_riscos'
def canon(v):
    return json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':'))

class BaseLocal:
    def __init__(self, path, seed=None):
        self.path = str(path)
        Path(path).parent.mkdir(parents=True,exist_ok=True)
        with self.db() as c:
            c.execute('CREATE TABLE IF NOT EXISTS atividades (id INTEGER PRIMARY KEY, registro TEXT NOT NULL, remoto TEXT, pendente INTEGER NOT NULL DEFAULT 0)')
            c.execute('CREATE TABLE IF NOT EXISTS meta (chave TEXT PRIMARY KEY, valor TEXT)')
            # Seed is applied once, including an intentionally empty base.
            if not c.execute("SELECT 1 FROM meta WHERE chave='iniciada'").fetchone():
                for r in seed or []:
                    c.execute('INSERT INTO atividades VALUES (?,?,?,0)',(int(r['id']),canon(r),canon(r)))
                c.execute("INSERT INTO meta VALUES ('iniciada','1')")
    def db(self):
        c=sqlite3.connect(self.path,timeout=20)
        c.execute('PRAGMA journal_mode=WAL')
        return c
    def __call__(self, method, tabela, params='', payload=None, prefer=None):
        if tabela != TABELA:
            if method=='GET': return []
            raise ValueError('A edição offline desta versão é exclusiva do mapa de riscos.')
        with self.db() as c:
            if method=='GET':
                return [json.loads(r[0]) for r in c.execute('SELECT registro FROM atividades ORDER BY id')]
            if method=='POST':
                cid = min(-1,c.execute('SELECT COALESCE(MIN(id),0)-1 FROM atividades').fetchone()[0])
                r=dict(payload,id=cid)
                r['dados']=dict(r['dados'],sync_uuid=str(uuid.uuid4()))
                c.execute('INSERT INTO atividades VALUES (?,?,NULL,1)',(cid,canon(r)))
                return [r]
            if method=='PATCH':
                cid=int(params.split('id=eq.',1)[1].split('&',1)[0])
                row=c.execute('SELECT registro FROM atividades WHERE id=?',(cid,)).fetchone()
                if not row: raise ValueError('Atividade local não encontrada.')
                r=dict(json.loads(row[0]),**payload)
                c.execute('UPDATE atividades SET registro=?,pendente=1 WHERE id=?',(canon(r),cid))
                return [r]
            raise ValueError('Operação não suportada.')
    def pendentes(self):
        with self.db() as c:
            return c.execute('SELECT COUNT(*) FROM atividades WHERE pendente=1').fetchone()[0]
    def sincronizar(self, remote):
        # A write can occur during network I/O; the final local compare prevents lost edits.
        import urllib.parse
        enviados,conflitos=0,[]
        with self.db() as c:
            filas=c.execute('SELECT id,registro,remoto FROM atividades WHERE pendente=1').fetchall()
        for cid,texto,base_texto in filas:
            r=json.loads(texto)
            body={k:v for k,v in r.items() if k!='id'}
            if cid<0:
                token=r['dados']['sync_uuid']
                existente=remote('GET',TABELA,'select=*&dados->>sync_uuid=eq.'+urllib.parse.quote(token,safe='')) or []
                resultado=existente or remote('POST',TABELA,'',body,'return=representation')
            else:
                atuais=remote('GET',TABELA,f'select=*&id=eq.{cid}') or []
                if not atuais:
                    conflitos.append(cid);continue
                atual=atuais[0]
                esperado=json.loads(base_texto) if base_texto else None
                # A previous successful send whose response was lost is safe to acknowledge.
                if canon(atual.get('dados'))==canon(r.get('dados')) and atual.get('atualizado_em')==r.get('atualizado_em'):
                    resultado=[atual]
                elif not esperado or canon(atual.get('dados'))!=canon(esperado.get('dados')) or atual.get('atualizado_em')!=esperado.get('atualizado_em'):
                    conflitos.append(cid);continue
                else:
                    versao=atual.get('atualizado_em')
                    filtro=f'id=eq.{cid}&atualizado_em='+('eq.'+urllib.parse.quote(versao,safe='') if versao else 'is.null')
                    resultado=remote('PATCH',TABELA,filtro,body,'return=representation')
                    if not resultado:
                        conflitos.append(cid);continue
            if not resultado: raise RuntimeError('Online não confirmou a gravação.')
            salvo=resultado[0]
            with self.db() as c:
                corrente=c.execute('SELECT registro FROM atividades WHERE id=?',(cid,)).fetchone()
                if not corrente:continue
                igual=corrente[0]==texto
                novo=json.loads(corrente[0]);novo['id']=salvo['id']
                c.execute('DELETE FROM atividades WHERE id=?',(cid,))
                c.execute('INSERT INTO atividades VALUES (?,?,?,?)',(salvo['id'],canon(salvo if igual else novo),canon(salvo),0 if igual else 1))
            enviados+=1
        return enviados,conflitos
