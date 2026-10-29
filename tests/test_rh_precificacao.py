import unittest
from decimal import Decimal
from unittest.mock import Mock
from uuid import uuid4

from rh_precificacao import calcular, normalizar, listar, salvar

ADMIN = {"id": 1, "perfil": "ADMIN", "nome": "Administrador"}


class PrecificacaoTest(unittest.TestCase):
    def test_margem_sobre_venda_e_custo_de_equipe(self):
        # 2h × 2 profissionais × R$50 + R$80 de peças + R$20 = R$300.
        c = calcular(dict(servico="Revisão", horas=2, profissionais=2, custo_hora=50,
                          materiais=80, outros=20, despesas_pct=10, margem_pct=30))
        self.assertEqual(c["mao_obra"], Decimal("200.00"))
        self.assertEqual(c["custo"], Decimal("300.00"))
        self.assertEqual(c["sugerido"], Decimal("500.00"))
        self.assertEqual(c["despesas"], Decimal("50.00"))
        self.assertEqual(c["lucro"], Decimal("150.00"))
        self.assertEqual(c["margem"], Decimal("30"))

    def test_preco_manual_mostra_prejuizo(self):
        c = calcular(dict(servico="Teste", materiais=100, despesas_pct=10, margem_pct=30, preco_manual=90))
        self.assertEqual(c["preco"], Decimal("90.00"))
        self.assertEqual(c["lucro"], Decimal("-19.00"))
        self.assertLess(c["margem"], 0)

    def test_preco_manual_zero_nao_vira_automatico(self):
        c = calcular(dict(servico="Cortesia", materiais=10, preco_manual=0))
        self.assertEqual(c["preco"], 0)
        self.assertIsNone(c["margem"])
        self.assertEqual(c["lucro"], -10)

    def test_centavos_sem_erro_de_float(self):
        c = calcular(dict(servico="Teste", materiais="0.10", outros="0.20", margem_pct=30))
        self.assertEqual(c["custo"], Decimal("0.30"))
        self.assertEqual(c["sugerido"], Decimal("0.43"))

    def test_custo_zero(self):
        c = calcular(dict(servico="Teste"))
        self.assertEqual(c["preco"], 0)
        self.assertIsNone(c["margem"])

    def test_nao_permite_valores_invalidos(self):
        for dado in (dict(servico=" "), dict(servico="x"*201), dict(horas=-1),
                     dict(custo_hora="NaN"), dict(materiais="Infinity"), dict(outros=None),
                     dict(profissionais=0), dict(profissionais=1.5), dict(profissionais=101),
                     dict(despesas_pct=50, margem_pct=50), dict(despesas_pct=101),
                     dict(preco_manual=-1)):
            with self.subTest(dado=dado), self.assertRaises(ValueError):
                normalizar({"servico": "Teste", **dado})

    def test_perfis_nao_autorizados_nunca_consultam_banco(self):
        for usuario in (None, {}, {"id": 2, "perfil": "RH"}, {"id": 3, "perfil": "SEGURANCA"}):
            sb = Mock()
            with self.assertRaises(PermissionError):
                listar(sb, usuario)
            with self.assertRaises(PermissionError):
                salvar(sb, usuario, {"servico": "Teste"})
            sb.assert_not_called()

    def test_concorrencia_impede_sobrescrita(self):
        sb = Mock(return_value=[])
        anterior = dict(id=str(uuid4()), versao=2)
        with self.assertRaisesRegex(ValueError, "Outro administrador"):
            salvar(sb, ADMIN, {"servico": "Teste"}, anterior=anterior)
        self.assertIn("versao=eq.2", sb.call_args.args[2])
        self.assertEqual(sb.call_args.args[3]["versao"], 3)

    def test_serializacao_e_id_estavel(self):
        sb = Mock(return_value=[])
        rid = str(uuid4())
        salvar(sb, ADMIN, dict(servico="Teste", materiais="1.23"), novo_id=rid)
        payload = sb.call_args.args[3]
        self.assertEqual(payload["materiais"], "1.23")
        self.assertEqual(payload["id"], rid)
        self.assertIsNone(payload["preco_manual"])
        self.assertIn("ignore-duplicates", sb.call_args.args[4])


class PrecificacaoInterfaceTest(unittest.TestCase):
    @staticmethod
    def app():
        import streamlit as st
        from urllib.parse import parse_qs
        from rh_precificacao import tela
        st.session_state.setdefault("usuario_logado", {"id": 1, "perfil": "ADMIN", "nome": "Teste"})
        st.session_state.setdefault("registros_teste", [])
        def sb(method, tabela, params="", payload=None, prefer=None):
            registros = st.session_state["registros_teste"]
            if method == "GET":
                return [dict(r) for r in registros]
            if method == "POST":
                if any(r["id"] == payload["id"] for r in registros):
                    return []
                registro = {"versao": 1, **payload}
                registros.append(registro)
                return [dict(registro)]
            if method == "PATCH":
                p = parse_qs(params)
                for r in registros:
                    if r["id"] == p["id"][0][3:] and str(r["versao"]) == p["versao"][0][3:]:
                        r.update(payload)
                        return [dict(r)]
                return []
            raise AssertionError(method)
        tela(sb)

    def test_simular_salvar_editar_e_inativar(self):
        from streamlit.testing.v1 import AppTest
        at = AppTest.from_function(self.app).run()
        self.assertFalse(at.exception)
        next(x for x in at.text_input if x.label == "Serviço *").set_value("Revisão")
        next(x for x in at.number_input if x.label == "Tempo estimado (horas)").set_value(2.0)
        next(x for x in at.number_input if x.label == "Quantidade de profissionais").set_value(2)
        next(x for x in at.number_input if x.label == "Custo por hora / profissional (R$)").set_value(50.0)
        next(x for x in at.number_input if x.label == "Peças e materiais (R$)").set_value(80.0)
        next(x for x in at.number_input if x.label == "Outros custos (R$)").set_value(20.0)
        next(x for x in at.number_input if x.label == "Impostos e despesas sobre a venda (%)").set_value(10.0)
        next(x for x in at.number_input if x.label == "Margem desejada sobre a venda (%)").set_value(30.0)
        at.run()
        self.assertFalse(at.exception)
        self.assertEqual(next(x for x in at.metric if x.label == "Preço sugerido").value, "R$ 500,00")
        next(x for x in at.button if x.label == "Salvar serviço").click().run()
        self.assertFalse(at.exception)
        self.assertEqual(len(at.session_state["registros_teste"]), 1)
        rid = at.session_state["registros_teste"][0]["id"]
        next(x for x in at.selectbox if x.label == "Cadastrar / editar serviço").set_value(rid).run()
        next(x for x in at.checkbox if x.label == "Usar automaticamente o preço sugerido").uncheck().run()
        next(x for x in at.number_input if x.label == "Preço praticado (R$)").set_value(450.0)
        next(x for x in at.checkbox if x.label == "Serviço ativo").uncheck()
        next(x for x in at.button if x.label == "Salvar serviço").click().run()
        self.assertFalse(at.exception)
        r = at.session_state["registros_teste"][0]
        self.assertEqual(r["preco_manual"], "450.00")
        self.assertFalse(r["ativo"])
        self.assertEqual(r["versao"], 2)
        next(x for x in at.selectbox if x.label == "Exibir").set_value("Inativos").run()
        self.assertEqual(len(at.dataframe), 1)
        self.assertFalse(at.exception)

    def test_soma_percentuais_invalida_bloqueia_salvamento(self):
        from streamlit.testing.v1 import AppTest
        at = AppTest.from_function(self.app).run()
        next(x for x in at.number_input if x.label == "Impostos e despesas sobre a venda (%)").set_value(50.0)
        next(x for x in at.number_input if x.label == "Margem desejada sobre a venda (%)").set_value(50.0)
        at.run()
        self.assertFalse(at.exception)
        self.assertTrue(next(x for x in at.button if x.label == "Salvar serviço").disabled)

    def test_rh_nao_visualiza_campos(self):
        from streamlit.testing.v1 import AppTest
        at = AppTest.from_function(self.app)
        at.session_state["usuario_logado"] = {"id": 2, "perfil": "RH"}
        at.run()
        self.assertFalse(at.exception)
        self.assertEqual(len(at.text_input), 0)
        self.assertIn("Administrador", at.error[0].value)


if __name__ == "__main__":
    unittest.main()
