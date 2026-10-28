import unittest
from rh_fabricacao import METAS, calcular, resumo_estoque, dias_pendentes, validar_link


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

    def test_diario_completo_media_tres(self):
        regs = [{"data": f"2026-10-{dia:02d}", "quantidades": dict(METAS)} for dia in range(1, 32)]
        self.assertEqual(dias_pendentes(regs, 2026, 10, METAS), [])
        self.assertEqual(resumo_estoque(regs, METAS)[0]["Chapa de Dimensão"], 3)

        regs.pop()
        self.assertEqual(len(dias_pendentes(regs, 2026, 10, METAS)), 1)
        self.assertEqual(resumo_estoque(regs, METAS)[0]["Chapa de Dimensão"], 3)

    def test_estoque_atendido_ignora_faltantes_e_desconto(self):
        integral, valor, motivo = self.apurar(estoque_atendido=True, medias={}, conferido=False)
        self.assertEqual(valor, integral)
        self.assertIn("considerado atendido", motivo)
        self.assertEqual(self.apurar(estoque_atendido=True, medias={i:0 for i in METAS})[1], 1091.65)
        self.assertIsNone(self.apurar(estoque_atendido=False, medias={}, conferido=False)[1])

    def test_estoque_atendido_preserva_demais_criterios(self):
        for mudanca in [dict(faltas=1), dict(dna=1), dict(horas=6), dict(atestados=3)]:
            self.assertEqual(self.apurar(estoque_atendido=True, **mudanca)[1], 0)
        self.assertEqual(self.apurar(estoque_atendido=True, atestados=1)[1], 818.74)
        self.assertIsNone(self.apurar(estoque_atendido=True, horas=None)[1])

    def test_link_invalido_nao_consulta_banco(self):
        def sb(*args):
            self.fail("Link inválido não deve consultar o banco")
        for token in (None, "", "'or true", "a" * 65):
            self.assertFalse(validar_link(sb, token))


if __name__ == "__main__":
    unittest.main()
