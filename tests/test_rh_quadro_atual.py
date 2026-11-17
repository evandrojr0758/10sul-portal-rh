import ast
import unittest
from datetime import date
from pathlib import Path
import pandas as pd

source = Path(__file__).resolve().parents[1] / 'portal_rh.py'
tree = ast.parse(source.read_text())
fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == '_quadro_colaboradores_agora')
ns = {'pd': pd}
exec(compile(ast.Module(body=[fn], type_ignores=[]), str(source), 'exec'), ns)
resumir = ns[fn.name]
HOJE = date(2026, 11, 17)

def pessoa(cid, tipo='OPERACIONAL', **extra):
    return dict(id=cid, colaborador=f'Pessoa {cid}', classificacao=tipo, ativo=True, **extra)

def resumo(pessoas, frequencia):
    return resumir(pessoas, frequencia, HOJE, lambda c: c['classificacao'])

class QuadroAtualTest(unittest.TestCase):
    def test_situacoes_e_tipos_sem_duplicar_spot_operacional(self):
        pessoas = [pessoa(1, tipo_contratacao='SPOT'), pessoa(2, 'OUTROS'), pessoa(3), pessoa(4)]
        r = resumo(pessoas, {1: 'AF', 2: 'AF', 3: 'FE', 4: 'FA'})
        self.assertEqual((r['registrados'], r['outros'], r['operacionais'], r['spot']), (4, 1, 3, 1))
        self.assertEqual([p['TIPO'] for p in r['situacoes']['AF']], ['SPOT', 'OUTROS'])
        self.assertEqual(len(r['situacoes']['FE']), 1)
        self.assertEqual(len(r['situacoes']['FA']), 1)
        self.assertEqual(r['pendentes'], 0)

    def test_vinculo_atual_nao_inclui_demissao_passada_ou_admissao_futura(self):
        pessoas = [pessoa(1, data_desligamento='2026-11-16'), pessoa(2, data_admissao='2026-11-18'),
                   pessoa(3, data_admissao='2026-11-17'), pessoa(4, data_desligamento='2026-11-17'),
                   dict(pessoa(5), ativo=False)]
        r = resumo(pessoas, {i: 'AF' for i in range(1, 6)})
        self.assertEqual(r['registrados'], 2)
        self.assertEqual([p['COLABORADOR'] for p in r['situacoes']['AF']], ['Pessoa 3', 'Pessoa 4'])

    def test_atestado_e_folga_nao_sao_afastamento_nem_pendencia(self):
        r = resumo([pessoa(i) for i in range(1, 5)], {1: 'A', 2: 'FO', 3: 'OK'})
        self.assertEqual(r['pendentes'], 1)
        self.assertEqual(sum(map(len, r['situacoes'].values())), 0)

    def test_cadastro_duplicado_conta_uma_pessoa_e_valores_normalizados(self):
        p = pessoa(1, tipo_contratacao=' spot ')
        r = resumo([p, p], {1: ' af '})
        self.assertEqual(r['registrados'], 1)
        self.assertEqual(r['spot'], 1)
        self.assertEqual(r['situacoes']['AF'][0]['TIPO'], 'SPOT')

if __name__ == '__main__':
    unittest.main()
