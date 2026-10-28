import unittest
from datetime import date, datetime
from unittest.mock import Mock
from zoneinfo import ZoneInfo

from rh_agenda import listar, salvar, preparar, filtrar, vencida

ADMIN = {"id": 1, "perfil": "ADMIN", "nome": "Administrador"}
AGORA = datetime(2026, 10, 28, 20, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))


class AgendaTest(unittest.TestCase):
    def test_perfis_nao_autorizados_nao_acessam_banco(self):
        for usuario in (None, {}, {"id": 2, "perfil": "RH"}, {"id": 3, "perfil": "SEGURANCA"}):
            sb = Mock()
            with self.assertRaises(PermissionError):
                listar(sb, usuario)
            with self.assertRaises(PermissionError):
                salvar(sb, usuario, {"situacao": "Teste"})
            sb.assert_not_called()

    def test_ciclo_conclusao_edicao_reabertura(self):
        dados = {"situacao": "Regularizar documento", "status": "RESOLVIDO", "solucao": "Documento recebido"}
        concluido = preparar(dados, agora=AGORA)
        self.assertEqual(concluido["resolvido_em"], AGORA.isoformat())
        editado = preparar({**dados, "solucao": "Conferido"}, concluido, agora=AGORA.replace(day=29))
        self.assertEqual(editado["resolvido_em"], concluido["resolvido_em"])
        reaberto = preparar({**dados, "status": "PENDENTE"}, editado, agora=AGORA.replace(day=30))
        self.assertIsNone(reaberto["resolvido_em"])
        self.assertEqual(reaberto["solucao"], dados["solucao"])

    def test_prazo_opcional_e_data_atual_nao_atrasada(self):
        self.assertIsNone(preparar({"situacao": "Teste"})["prazo"])
        for status, prazo, esperado in (("PENDENTE", "2026-10-27", True),
                                        ("PENDENTE", "2026-10-28", False),
                                        ("RESOLVIDO", "2026-10-27", False),
                                        ("PENDENTE", None, False)):
            self.assertEqual(vencida({"status": status, "prazo": prazo}, AGORA.date()), esperado)

    def test_validacao(self):
        for dados in ({"situacao": " "}, {"situacao": "a" * 201},
                      {"situacao": "Teste", "status": "OUTRO"},
                      {"situacao": "Teste", "prazo": "31/10/2026"}):
            with self.assertRaises(ValueError):
                preparar(dados)

    def test_concorrencia_nao_sobrescreve_silenciosamente(self):
        sb = Mock(return_value=[])
        with self.assertRaisesRegex(ValueError, "Outra pessoa"):
            salvar(sb, ADMIN, {"situacao": "Teste"}, anterior={"id": "uuid", "versao": 3})
        self.assertEqual(sb.call_args.args[2], "id=eq.uuid&versao=eq.3")
        self.assertEqual(sb.call_args.args[3]["versao"], 4)

    def test_novo_formulario_reutiliza_id_ao_repetir(self):
        sb = Mock(return_value=[])
        salvar(sb, ADMIN, {"situacao": "Teste"}, novo_id="mesmo-id")
        self.assertEqual(sb.call_args.args[3]["id"], "mesmo-id")
        self.assertIn("ignore-duplicates", sb.call_args.args[4])

    def test_lista_nao_trunca_apos_limite_api(self):
        sb = Mock(side_effect=[[{"id": n} for n in range(500)], [{"id": 501}]])
        self.assertEqual(len(listar(sb, ADMIN)), 501)
        self.assertIn("offset=500", sb.call_args.args[2])

    def test_filtros_ordem_e_busca_acentos(self):
        def r(id, status, prazo):
            return dict(id=id, status=status, prazo=prazo, situacao="Revisão de cadastro", responsavel="João")
        registros = [r("r", "RESOLVIDO", "2026-10-20"), r("s", "PENDENTE", None),
                     r("f", "PENDENTE", "2026-11-01"), r("a", "PENDENTE", "2026-10-20")]
        self.assertEqual([x["id"] for x in filtrar(registros, AGORA.date())], ["a", "f", "s", "r"])
        self.assertEqual(len(filtrar(registros, AGORA.date(), busca="revisao")), 4)
        self.assertEqual([x["id"] for x in filtrar(registros, AGORA.date(), busca="joao", atrasadas=True)], ["a"])


class AgendaInterfaceTest(unittest.TestCase):
    @staticmethod
    def app():
        import streamlit as st
        from rh_agenda import tela
        from urllib.parse import parse_qs
        st.session_state.setdefault("usuario_logado", {"id": 1, "perfil": "ADMIN", "nome": "Teste"})
        st.session_state.setdefault("registros_teste", [])
        def sb(method, tabela, params="", payload=None, prefer=None):
            registros = st.session_state["registros_teste"]
            if method == "GET":
                return [dict(r) for r in registros]
            if method == "POST":
                registro = {"versao": 1, **payload}
                if not any(r["id"] == registro["id"] for r in registros):
                    registros.append(registro)
                    return [dict(registro)]
                return []
            if method == "PATCH":
                p = parse_qs(params)
                for r in registros:
                    if r["id"] == p["id"][0][3:] and str(r["versao"]) == p["versao"][0][3:]:
                        r.update(payload)
                        return [dict(r)]
                return []
            raise AssertionError(method)
        tela(sb)

    def test_interface_cria_resolve_e_reabre(self):
        from streamlit.testing.v1 import AppTest
        at = AppTest.from_function(self.app).run()
        self.assertFalse(at.exception)
        at.text_input[0].set_value("Resolver documentação")
        at.text_input[1].set_value("Evandro")
        next(b for b in at.button if b.label == "Registrar pendência").click().run()
        self.assertFalse(at.exception)
        self.assertEqual(len(at.session_state["registros_teste"]), 1)
        next(s for s in at.selectbox if s.label == "Status da situação").set_value("RESOLVIDO")
        next(t for t in at.text_area if t.label == "Observação / solução").set_value("Recebido e conferido")
        next(b for b in at.button if b.label == "Salvar alterações").click().run()
        self.assertFalse(at.exception)
        self.assertEqual(at.session_state["registros_teste"][0]["status"], "RESOLVIDO")
        self.assertTrue(at.session_state["registros_teste"][0]["resolvido_em"])
        next(s for s in at.selectbox if s.label == "Status da situação").set_value("PENDENTE")
        next(b for b in at.button if b.label == "Salvar alterações").click().run()
        self.assertFalse(at.exception)
        self.assertEqual(at.session_state["registros_teste"][0]["status"], "PENDENTE")
        self.assertIsNone(at.session_state["registros_teste"][0]["resolvido_em"])

    def test_interface_bloqueia_rh(self):
        from streamlit.testing.v1 import AppTest
        at = AppTest.from_function(self.app)
        at.session_state["usuario_logado"] = {"id": 2, "perfil": "RH"}
        at.run()
        self.assertFalse(at.exception)
        self.assertEqual(len(at.text_input), 0)
        self.assertIn("Administrador", at.error[0].value)


if __name__ == "__main__":
    unittest.main()
