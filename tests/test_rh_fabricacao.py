import unittest
from rh_fabricacao import METAS, calcular, resumo_estoque


class FabricacaoTest(unittest.TestCase):
    def apurar(self, **alteracoes):
        args = dict(salario=3119, faltas=0, atestados=0, dna=2,
                    horas=0, medias=dict(METAS), conferido=True, regra={})
        args.update(alteracoes)
        return calcular(**args)

    def test_termo_atestados(self):
        for dias, valor in [(0, 1091.65), (1, 818.74), (2, 545.83), (3, 0)]:
            with self.subTest(dias=dias):
                self.assertEqual(self.apurar(atestados=dias)[1], valor)

    def test_limite_he_estrito(self):
        self.assertEqual(self.apurar(horas=5)[1], 1091.65)
        self.assertEqual(self.apurar(horas=5.01)[1], 0)

    def test_falta_dna(self):
        self.assertEqual(self.apurar(faltas=1)[1], 0)
        self.assertEqual(self.apurar(dna=1)[1], 0)

    def test_estoque_descontos_acumulados(self):
        medias = {**METAS, "Chapa RMT": 3, "Chapa de Dimensão": 2}
        self.assertEqual(self.apurar(medias=medias)[1], 982.49)
        self.assertEqual(self.apurar(medias=medias, atestados=1)[1], 709.57)

    def test_dados_pendentes_nao_liberam_valor(self):
        for mudanca in [dict(horas=None), dict(conferido=False), dict(salario=None),
                        dict(medias={}), dict(atestados=0.5), dict(atestados=1.5)]:
            with self.subTest(mudanca=mudanca):
                self.assertIsNone(self.apurar(**mudanca)[1])

    def test_fracao_acima_de_dois_zera(self):
        self.assertEqual(self.apurar(atestados=2.5)[1], 0)

    def test_media_e_reconferencia(self):
        regs = [{"data": "2026-10-01", "quantidades": {**METAS, "Chapa RMT": 2}},
                {"data": "2026-10-02", "quantidades": {**METAS, "Chapa RMT": 6}}]
        medias, assinatura = resumo_estoque(regs, METAS)
        self.assertEqual(medias["Chapa RMT"], 4)
        self.assertEqual(resumo_estoque(list(reversed(regs)), METAS)[1], assinatura)
        regs[0]["quantidades"]["Chapa RMT"] = 0
        self.assertNotEqual(resumo_estoque(regs, METAS)[1], assinatura)
        self.assertNotEqual(resumo_estoque(regs, {**METAS, "Chapa RMT": 8})[1], assinatura)

    def test_configuracao_zero_respeitada(self):
        self.assertEqual(self.apurar(regra={"percentual_salario": 0})[1], 0)
        self.assertEqual(self.apurar(dna=0, regra={"dna_minimo": 0})[1], 1091.65)


if __name__ == "__main__":
    unittest.main()
