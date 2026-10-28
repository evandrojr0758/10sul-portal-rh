"""Mapeamento preventivo de atividades, acessível pelo perfil Segurança."""
from datetime import date, datetime, timezone
import pandas as pd
import streamlit as st
import altair as alt

CONSEQUENCIAS = ["Fatalidade possível", "Amputação possível", "Afastamento possível", "Lesão sem afastamento possível", "Baixo potencial", "A validar"]
CORES = ["#dc2626", "#ef4444", "#eab308", "#facc15", "#16a34a", "#64748b"]


def severidade(consequencia):
    if consequencia in CONSEQUENCIAS[:2]:
        return "CRÍTICA"
    if consequencia in CONSEQUENCIAS[2:4]:
        return "MODERADA"
    if consequencia == "Baixo potencial":
        return "BAIXA"
    return "A VALIDAR"


def tela_riscos(sb, usuario):
    st.title("🦺 Mapa de riscos e plano preventivo")
    st.caption("Base: matriz de outubro/2026 e mapeamento completo EXEMPLO 2. As consequências importadas são triagens; a Segurança deve validar cada cenário em campo.")
    st.info("Vermelho: potencial de fatalidade/amputação • Amarelo: lesões com ou sem afastamento • Verde: baixo potencial • Cinza: a validar. A cor representa a consequência potencial, não uma nova avaliação da probabilidade.")
    try:
        regs = sb("GET", "rh_seguranca_riscos", "select=*&order=id.asc&limit=1000") or []
    except Exception as exc:
        st.error(f"Não foi possível carregar o mapeamento: {exc}")
        return
    if not regs:
        st.info("Nenhuma atividade cadastrada.")
        return
    linhas = [dict(r.get("dados") or {}, id=r["id"]) for r in regs]
    df = pd.DataFrame(linhas)
    df["consequencia"] = df["consequencia"].fillna("A validar")
    df["severidade"] = df["consequencia"].map(severidade)
    painel, plano, editar = st.tabs(["Painel e atividades", "Plano de ação", "Validar / editar atividade"])
    with painel:
        cols = st.columns(4)
        cols[0].metric("Atividades mapeadas", len(df))
        cols[1].metric("Potencial crítico", int(df["severidade"].eq("CRÍTICA").sum()))
        cols[2].metric("Potencial moderado", int(df["severidade"].eq("MODERADA").sum()))
        cols[3].metric("A validar em campo", int(df["validacao"].ne("Validada").sum()))
        f1, f2, f3 = st.columns(3)
        busca = f1.text_input("Buscar atividade ou risco", key="riscos_busca")
        categoria = f2.selectbox("Consequência potencial", ["TODAS"] + CONSEQUENCIAS, key="riscos_consequencia")
        validacao = f3.selectbox("Validação operacional", ["TODAS", "Pendente", "Validada"], key="riscos_validacao")
        view = df.copy()
        if busca:
            view = view[view["atividade"].str.contains(busca, case=False, regex=False, na=False) | view["riscos"].str.contains(busca, case=False, regex=False, na=False)]
        if categoria != "TODAS":
            view = view[view["consequencia"].eq(categoria)]
        if validacao != "TODAS":
            view = view[view["validacao"].eq(validacao)]
        contagem = view.groupby("consequencia").size().reset_index(name="atividades")
        if not view.empty:
            clique = alt.selection_point(name="categoria", fields=["consequencia"], on="click", clear="dblclick")
            grafico = alt.Chart(contagem).mark_bar(cornerRadiusEnd=5).encode(
                x=alt.X("atividades:Q", title="Quantidade de atividades", axis=alt.Axis(tickMinStep=1)),
                y=alt.Y("consequencia:N", title=None, sort=CONSEQUENCIAS),
                color=alt.Color("consequencia:N", scale=alt.Scale(domain=CONSEQUENCIAS, range=CORES), legend=None),
                opacity=alt.condition(clique, alt.value(1), alt.value(0.45)),
                tooltip=[alt.Tooltip("consequencia:N", title="Consequência"), alt.Tooltip("atividades:Q", title="Atividades")],
            ).add_params(clique).properties(height=280)
            evento = st.altair_chart(grafico, use_container_width=True, on_select="rerun", key="riscos_grafico")
            selecionadas = evento.get("selection", {}).get("categoria", [])
            if selecionadas:
                categorias = [p["consequencia"] for p in selecionadas if "consequencia" in p]
                if categorias:
                    view = view[view["consequencia"].isin(categorias)]
            st.caption("Clique em uma barra para abrir as atividades abaixo. Dê dois cliques no gráfico para limpar a seleção. Cada atividade é contada uma vez, pela consequência prioritária da triagem.")
        else:
            st.info("Nenhuma atividade para os filtros selecionados.")
        mostrar_atividades(view)
    with plano:
        st.subheader("Plano de ação preventivo")
        atrasadas = df.apply(lambda r: bool(r.get("prazo") and str(r["prazo"]) < date.today().isoformat() and r.get("status_acao") != "Concluída"), axis=1)
        st.metric("Ações com prazo vencido", int(atrasadas.sum()))
        status = st.selectbox("Status da ação", ["TODOS", "Não iniciada", "Em andamento", "Concluída"], key="riscos_status_plano")
        view_plano = df if status == "TODOS" else df[df["status_acao"].eq(status)]
        campos = ["atividade", "consequencia", "controles", "lacuna", "acao", "hierarquia", "responsavel", "prazo", "status_acao", "evidencia", "probabilidade_residual", "severidade_residual", "nivel_residual"]
        st.dataframe(view_plano[campos].rename(columns=ROTULOS), use_container_width=True, hide_index=True)
        st.caption("Atualize responsáveis, prazos, ações e evidências na aba Validar / editar atividade. Concluir uma ação não valida automaticamente a eficácia ou o risco residual.")
    with editar:
        ids = df["id"].tolist()
        alvo = st.selectbox("Atividade", ids, format_func=lambda i: str(df.loc[df["id"].eq(i), "atividade"].iloc[0]), key="riscos_editar_id")
        original = next(r for r in linhas if r["id"] == alvo)
        with st.form(f"risco_form_{alvo}"):
            st.caption(f"Classificação original: {original.get('classificacao_original') or '—'} • Severidade original: {original.get('severidade_original') or '—'}")
            dados = dict(original)
            for campo in ["riscos", "controles", "cenario", "lacuna", "acao"]:
                dados[campo] = st.text_area(ROTULOS[campo], value=str(original.get(campo) or ""))
            atual = original.get("consequencia") or "A validar"
            dados["consequencia"] = st.selectbox("Consequência prioritária", CONSEQUENCIAS, index=CONSEQUENCIAS.index(atual) if atual in CONSEQUENCIAS else 5)
            dados["validacao"] = st.selectbox("Validação operacional", ["Pendente", "Validada"], index=1 if original.get("validacao") == "Validada" else 0)
            dados["responsavel"] = st.text_input("Responsável", value=str(original.get("responsavel") or ""))
            dados["hierarquia"] = st.text_input("Hierarquia do controle (eliminação, substituição, engenharia, administrativo, EPI)", value=str(original.get("hierarquia") or ""))
            prazo = original.get("prazo")
            dados["prazo"] = st.date_input("Prazo", value=date.fromisoformat(prazo) if prazo else None)
            estados = ["Não iniciada", "Em andamento", "Concluída"]
            dados["status_acao"] = st.selectbox("Status da ação", estados, index=estados.index(original.get("status_acao")) if original.get("status_acao") in estados else 0)
            dados["evidencia"] = st.text_area("Evidência / reavaliação", value=str(original.get("evidencia") or ""))
            for campo in ["probabilidade_residual", "severidade_residual", "nivel_residual"]:
                dados[campo] = st.text_input(ROTULOS[campo], value=str(original.get(campo) or "Não avaliado"))
            salvar = st.form_submit_button("Salvar atividade e plano de ação", type="primary")
        if salvar:
            if dados["validacao"] == "Validada" and (dados["consequencia"] == "A validar" or not dados["cenario"].strip()):
                st.error("Para validar, informe o cenário e a consequência prioritária.")
            elif dados["status_acao"] == "Concluída" and not dados["evidencia"].strip():
                st.error("Informe a evidência antes de concluir a ação.")
            else:
                dados.pop("id", None)
                dados["prazo"] = dados["prazo"].isoformat() if dados["prazo"] else None
                autor = str(usuario.get("nome") or usuario.get("usuario") or "Segurança")
                quando = datetime.now(timezone.utc).isoformat()
                dados["historico"] = list(original.get("historico") or []) + [{"em": quando, "por": autor, "antes": {k: v for k, v in original.items() if k not in ("historico", "id")}}]
                try:
                    sb("PATCH", "rh_seguranca_riscos", f"id=eq.{int(alvo)}", {"dados": dados, "atualizado_em": quando, "atualizado_por": autor}, "return=minimal")
                    st.success("Atividade e plano de ação salvos.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Não foi possível salvar: {exc}")


ROTULOS = {"atividade": "Atividade", "riscos": "Perigos / riscos", "controles": "Controles atuais", "cenario": "Cenário de acidente / exposição", "consequencia": "Consequência potencial", "severidade": "Severidade", "validacao": "Validação operacional", "responsavel": "Responsável", "nr": "NR informada na matriz", "lacuna": "Lacuna identificada em campo", "acao": "Ação adicional proposta", "hierarquia": "Hierarquia do controle", "prazo": "Prazo", "status_acao": "Status da ação", "evidencia": "Evidência / reavaliação", "probabilidade_residual": "Probabilidade residual", "severidade_residual": "Severidade residual", "nivel_residual": "Nível residual"}


def mostrar_atividades(df):
    st.subheader(f"Atividades selecionadas ({len(df)})")
    campos = ["atividade", "consequencia", "severidade", "riscos", "controles", "responsavel", "nr", "validacao"]
    st.dataframe(df[campos].rename(columns=ROTULOS), use_container_width=True, hide_index=True)
    if not df.empty:
        st.download_button("Baixar atividades selecionadas (CSV)", df[campos].rename(columns=ROTULOS).to_csv(index=False, sep=";").encode("utf-8-sig"), "atividades_riscos.csv", "text/csv")
