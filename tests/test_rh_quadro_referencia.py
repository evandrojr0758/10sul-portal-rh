import ast
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import Mock

source=Path(__file__).resolve().parents[1]/'portal_rh.py'
tree=ast.parse(source.read_text())
block=next(n for n in tree.body if isinstance(n,ast.With) and any(isinstance(i.context_expr,ast.Name) and i.context_expr.id=='resumo_topo' for i in n.items))
start=next(i for i,n in enumerate(block.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='_quadro_frequencia' for t in n.targets))
end=next(i for i,n in enumerate(block.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='_quadro' for t in n.targets))
code=compile(ast.Module(body=block.body[start:end],type_ignores=[]),str(source),'exec')

class ReferenciaTest(unittest.TestCase):
    def run_case(self,last,preview,month=11):
        sb=Mock(side_effect=([[{'data':last}] if last else []][0], [{'colaborador_id':1,'ocorrencia_id':5}] if last else []))
        ns=dict(sb=sb,_quadro_base=[{'id':1}],hoje=date(2026,11,17),ano=2026,mes=month,ids=[1],_mapa_media={(1,17):preview},_codigo_grade=lambda v:str(v or '').strip().upper(),ocorrencia_codigo_por_id={5:'FE'})
        exec(code,ns)
        return ns,sb
    def test_sem_hoje_usa_ultimo_preenchido(self):
        ns,sb=self.run_case('2026-11-05','')
        self.assertEqual(ns['_quadro_referencia'],'2026-11-05')
        self.assertEqual(ns['_quadro_frequencia'],{1:'FE'})
        self.assertIn('data=eq.2026-11-05',sb.call_args.args[2])
    def test_hoje_editado_tem_prioridade(self):
        ns,_=self.run_case('2026-11-05','AF')
        self.assertEqual(ns['_quadro_referencia'],'2026-11-17')
        self.assertEqual(ns['_quadro_frequencia'],{1:'AF'})
    def test_mes_historico_nao_troca_referencia_para_mes_escolhido(self):
        ns,_=self.run_case('2026-11-05','AF',month=10)
        self.assertEqual(ns['_quadro_referencia'],'2026-11-05')
    def test_sem_registros_nao_inventa_zero_atual(self):
        ns,_=self.run_case(None,'')
        self.assertIsNone(ns['_quadro_referencia'])
        self.assertFalse(ns['_quadro_erro'])
        self.assertEqual(ns['_quadro_frequencia'],{})
