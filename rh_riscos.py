"""Mapeamento preventivo de atividades, acessível pelo perfil Segurança."""
from datetime import date, datetime, timezone
import pandas as pd
import streamlit as st
import altair as alt

CONSEQUENCIAS = ["Fatalidade possível", "Amputação possível", "Afastamento possível", "Lesão sem afastamento possível", "Baixo potencial", "A validar"]
NIVEIS_RISCO = ["Alto", "Médio", "Baixo", "A validar"]
CORES_NIVEIS = ["#dc2626", "#eab308", "#16a34a", "#64748b"]

CORES = ["#dc2626", "#ef4444", "#eab308", "#facc15", "#16a34a", "#64748b"]


def severidade(consequencia):
    if consequencia in CONSEQUENCIAS[:2]:
        return "CRÍTICA"
    if consequencia in CONSEQUENCIAS[2:4]:
        return "MODERADA"
    if consequencia == "Baixo potencial":
        return "BAIXA"
    return "A VALIDAR"


def nivel_risco(valor):
    texto = str(valor or "").strip().casefold()
    return {"alto": "Alto", "médio": "Médio", "medio": "Médio", "baixo": "Baixo"}.get(texto, "A validar")


def grafico_niveis(df):
    contagem = (df.groupby("nivel_risco").size()
                .reindex(NIVEIS_RISCO, fill_value=0)
                .rename_axis("nivel_risco").reset_index(name="atividades"))
    clique = alt.selection_point(
        name="nivel", fields=["nivel_risco"], on="click",
        clear="dblclick", toggle="true",
    )
    base = alt.Chart(contagem).encode(
        x=alt.X("atividades:Q", title="Quantidade de atividades", axis=alt.Axis(tickMinStep=1),
                scale=alt.Scale(domain=[0, max(1, int(contagem["atividades"].max())) * 1.15])),
        y=alt.Y("nivel_risco:N", title="Nível de risco", sort=NIVEIS_RISCO),
        tooltip=[alt.Tooltip("nivel_risco:N", title="Nível de risco"),
                 alt.Tooltip("atividades:Q", title="Atividades", format="d")],
    )
    barras = base.mark_bar(cornerRadiusEnd=5).encode(
        color=alt.Color("nivel_risco:N", scale=alt.Scale(domain=NIVEIS_RISCO, range=CORES_NIVEIS), legend=None),
        opacity=alt.condition(clique, alt.value(1), alt.value(0.45)),
    ).add_params(clique)
    rotulos = base.mark_text(align="left", baseline="middle", dx=6, fontWeight="bold").encode(
        text=alt.Text("atividades:Q", format="d"),
    )
    return (barras + rotulos).properties(height=220)


def tela_riscos(sb, usuario):
    if str((usuario or {}).get("perfil") or "").strip().upper() != "SEGURANCA":
        st.error("O mapa de riscos está disponível somente no acesso da Segurança.")
        return
    st.title("🦺 Mapa de riscos e plano preventivo")
    st.caption("Base: matriz de outubro/2026 e mapeamento completo EXEMPLO 2. As severidades importadas são triagens; a Segurança deve validar cada cenário em campo.")
    st.info("Vermelho: potencial de fatalidade/amputação • Amarelo: lesões com ou sem afastamento • Verde: baixo potencial • Cinza: a validar. A cor representa a severidade selecionada. O nível de risco pode ser editado na tabela.")
    try:
        regs = sb("GET", "rh_seguranca_riscos", "select=*&order=id.asc&limit=1000") or []
    except Exception as exc:
        st.error(f"Não foi possível carregar o mapeamento: {exc}")
        return
    linhas = [dict(r.get("dados") or {}, id=r["id"]) for r in regs if not (r.get("dados") or {}).get("excluido")]
    df = pd.DataFrame(linhas, columns=list(PADRAO) + ["id"])
    df["consequencia"] = df["consequencia"].fillna("A validar")
    df["severidade"] = df["consequencia"].map(severidade)
    df["nivel_risco"] = df["nivel_risco"].where(df["nivel_risco"].notna() & df["nivel_risco"].ne(""), df["classificacao_original"]).map(nivel_risco)
    painel, plano, editar = st.tabs(["Painel e atividades", "Plano de ação", "Validar / editar atividade"])
    with painel:
        cols = st.columns(4)
        cols[0].metric("Atividades mapeadas", len(df))
        cols[1].metric("Potencial crítico", int(df["severidade"].eq("CRÍTICA").sum()))
        cols[2].metric("Potencial moderado", int(df["severidade"].eq("MODERADA").sum()))
        cols[3].metric("A validar em campo", int(df["validacao"].ne("Validada").sum()))
        f1, f2, f3 = st.columns(3)
        busca = f1.text_input("Buscar atividade ou risco", key="riscos_busca")
        categoria = f2.selectbox("Severidade", ["TODAS"] + CONSEQUENCIAS, key="riscos_consequencia")
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
            clique = alt.selection_point(name="categoria", fields=["consequencia"], on="click", clear="dblclick", toggle="true")
            grafico = alt.Chart(contagem).mark_bar(cornerRadiusEnd=5).encode(
                x=alt.X("atividades:Q", title="Quantidade de atividades", axis=alt.Axis(tickMinStep=1)),
                y=alt.Y("consequencia:N", title=None, sort=CONSEQUENCIAS),
                color=alt.Color("consequencia:N", scale=alt.Scale(domain=CONSEQUENCIAS, range=CORES), legend=None),
                opacity=alt.condition(clique, alt.value(1), alt.value(0.45)),
                tooltip=[alt.Tooltip("consequencia:N", title="Severidade"), alt.Tooltip("atividades:Q", title="Atividades")],
            ).add_params(clique).properties(height=280)
            evento = st.altair_chart(grafico, use_container_width=True, on_select="rerun", key="riscos_grafico")
            selecionadas = evento.get("selection", {}).get("categoria", [])
            if selecionadas:
                categorias = [p["consequencia"] for p in selecionadas if "consequencia" in p]
                if categorias:
                    view = view[view["consequencia"].isin(categorias)]
            st.caption("Clique em uma barra para filtrar as atividades. Clique novamente na mesma barra para remover a seleção e mostrar todas. Cada atividade é contada uma vez, pela severidade selecionada.")
        else:
            st.info("Nenhuma atividade para os filtros selecionados.")
        st.subheader("Atividades por nível de risco")
        st.caption("Nível de risco salvo para cada atividade: Alto, Médio ou Baixo. A classificação inicial vem da matriz e pode ser editada na tabela.")
        evento_nivel = st.altair_chart(
            grafico_niveis(view), use_container_width=True,
            on_select="rerun", key="riscos_grafico_niveis",
        )
        niveis_selecionados = [
            p["nivel_risco"] for p in evento_nivel.get("selection", {}).get("nivel", [])
            if "nivel_risco" in p
        ]
        if niveis_selecionados:
            view = view[view["nivel_risco"].isin(niveis_selecionados)]
        st.caption("Clique em uma barra para filtrar as atividades por nível. Clique novamente para remover a seleção.")
        st.subheader("Exportar relatório")
        st.caption("PDF ou Excel formatado com indicadores, gráficos, atividades e plano de ação da seleção atual. Salve as edições da tabela antes de exportar.")
        if not view.empty:
            from rh_riscos_export import gerar_pdf_riscos
            filtros_pdf = f"Busca: {busca or 'Todas'} | Severidade: {categoria} | Validação: {validacao}"
            if selecionadas:
                filtros_pdf += " | Gráfico: " + ", ".join(categorias)
            if niveis_selecionados:
                filtros_pdf += " | Nível de risco: " + ", ".join(niveis_selecionados)
            st.download_button(
                "📄 Baixar relatório com gráficos (PDF)",
                data=gerar_pdf_riscos(view, filtros_pdf),
                file_name=f"mapa_de_riscos_{date.today():%Y-%m-%d}.pdf",
                mime="application/pdf", key="riscos_baixar_pdf",
            )
        if not view.empty:
            from rh_riscos_excel import gerar_excel_riscos
            st.download_button(
                "📊 Baixar Excel formatado com gráficos",
                data=gerar_excel_riscos(view, filtros_pdf),
                file_name=f"mapa_de_riscos_{date.today():%Y-%m-%d}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="riscos_baixar_excel",
            )
        mostrar_atividades(view, sb, usuario, linhas)
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
        if df.empty:
            st.info("Acrescente a primeira atividade na tabela da aba Painel e atividades.")
            return
        ids = df["id"].tolist()
        alvo = st.selectbox("Atividade", ids, format_func=lambda i: str(df.loc[df["id"].eq(i), "atividade"].iloc[0]), key="riscos_editar_id")
        original = next(r for r in linhas if r["id"] == alvo)
        with st.form(f"risco_form_{alvo}"):
            st.caption(f"Classificação original: {original.get('classificacao_original') or '—'} • Severidade original: {original.get('severidade_original') or '—'}")
            dados = dict(original)
            dados["atividade"] = st.text_input("Nome da atividade", value=str(original.get("atividade") or ""))
            dados["nr"] = st.text_input("NR informada na matriz", value=str(original.get("nr") or ""))
            for campo in ["riscos", "controles", "cenario", "lacuna", "acao"]:
                dados[campo] = st.text_area(ROTULOS[campo], value=str(original.get(campo) or ""))
            atual = original.get("consequencia") or "A validar"
            dados["consequencia"] = st.selectbox("Severidade", CONSEQUENCIAS, index=CONSEQUENCIAS.index(atual) if atual in CONSEQUENCIAS else 5)
            nivel_atual = nivel_risco(original.get("nivel_risco") or original.get("classificacao_original"))
            dados["nivel_risco"] = st.selectbox("Nível de risco", NIVEIS_RISCO, index=NIVEIS_RISCO.index(nivel_atual))
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
            if not dados["atividade"].strip():
                st.error("Informe o nome da atividade.")
            elif dados["validacao"] == "Validada" and (dados["consequencia"] == "A validar" or not dados["cenario"].strip()):
                st.error("Para validar, informe o cenário e a severidade.")
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


ROTULOS = {"nivel_risco": "Nível de risco", "atividade": "Atividade", "riscos": "Perigos / riscos", "controles": "Controles atuais", "cenario": "Cenário de acidente / exposição", "consequencia": "Severidade", "severidade": "Severidade", "validacao": "Validação operacional", "responsavel": "Responsável", "nr": "NR informada na matriz", "lacuna": "Lacuna identificada em campo", "acao": "Ação adicional proposta", "hierarquia": "Hierarquia do controle", "prazo": "Prazo", "status_acao": "Status da ação", "evidencia": "Evidência / reavaliação", "probabilidade_residual": "Probabilidade residual", "severidade_residual": "Severidade residual", "nivel_residual": "Nível residual"}


PADRAO = {
    "atividade": "", "riscos": "", "controles": "", "responsavel": "", "nr": "",
    "consequencia": "A validar", "validacao": "Pendente", "cenario": "",
    "lacuna": "", "acao": "", "hierarquia": "", "prazo": None,
    "status_acao": "Não iniciada", "evidencia": "",
    "probabilidade_residual": "Não avaliada", "severidade_residual": "Não avaliada",
    "nivel_residual": "Não avaliado", "nivel_risco": None, "classificacao_original": "", "severidade_original": "",
}
CAMPOS_GRADE = ["nivel_risco", "atividade", "consequencia", "riscos", "controles", "responsavel", "nr"]


def preparar_alteracoes(editado, visiveis, originais):
    """Compara somente IDs da seleção atual; remoção é lógica, com histórico."""
    por_id = {int(r["id"]): r for r in originais}
    permitidos = set(int(i) for i in visiveis)
    vistos = set()
    alteracoes = []
    for linha in editado.to_dict(orient="records"):
        valor_id = linha.get("id")
        novo = pd.isna(valor_id)
        cid = None if novo else int(valor_id)
        if cid is not None and (cid not in permitidos or cid in vistos):
            raise ValueError("Identificação inválida na tabela. Atualize a página.")
        if cid is not None:
            vistos.add(cid)
        nome = str(linha.get("atividade") or "").strip()
        # A linha vazia de inclusão do editor não gera cadastro.
        if novo and not any(str(linha.get(c) or "").strip() for c in CAMPOS_GRADE if not pd.isna(linha.get(c))):
            continue
        if not nome or pd.isna(linha.get("atividade")):
            raise ValueError("Toda atividade precisa de um nome.")
        anterior = por_id.get(cid)
        dados = dict(anterior) if anterior else dict(PADRAO)
        for campo in CAMPOS_GRADE:
            valor = linha.get(campo)
            dados[campo] = "" if pd.isna(valor) else str(valor).strip()
        dados["consequencia"] = dados["consequencia"] or "A validar"
        if dados["consequencia"] not in CONSEQUENCIAS:
            raise ValueError("Selecione uma severidade válida.")
        dados["nivel_risco"] = dados["nivel_risco"] or "A validar"
        if dados["nivel_risco"] not in NIVEIS_RISCO:
            raise ValueError("Selecione um nível de risco válido.")
        anterior_nivel = nivel_risco((anterior or {}).get("nivel_risco") or (anterior or {}).get("classificacao_original"))
        if novo or any(dados.get(c) != (anterior_nivel if c == "nivel_risco" else anterior.get(c)) for c in CAMPOS_GRADE):
            dados["validacao"] = "Pendente"
            alteracoes.append((cid, dados, anterior))
    for cid in permitidos - vistos:
        anterior = por_id[cid]
        dados = dict(anterior, excluido=True)
        alteracoes.append((cid, dados, anterior))
    return alteracoes


def mostrar_atividades(df, sb, usuario, originais):
    import hashlib
    st.subheader(f"Atividades selecionadas ({len(df)})")
    st.caption("Edite as células, use a última linha para acrescentar e selecione uma linha para excluir. Clique em Salvar alterações. A severidade e o nível de risco podem ser editados diretamente; alterações voltam para validação pendente.")
    campos = ["id", "atividade", "nivel_risco", "consequencia", "riscos", "controles", "responsavel", "nr", "validacao"]
    base = df[campos].copy()
    # Uma seleção ou gravação diferente nunca reutiliza deltas de outras linhas.
    assinatura = hashlib.sha256(base.to_json(orient="records").encode()).hexdigest()[:16]
    editado = st.data_editor(
        base, use_container_width=True, hide_index=True, num_rows="dynamic",
        disabled=["id", "validacao"],
        column_config={
            "id": None,
            "nivel_risco": st.column_config.SelectboxColumn("Nível de risco", options=NIVEIS_RISCO),
            **{c: st.column_config.TextColumn(ROTULOS[c]) for c in ["atividade", "riscos", "controles", "responsavel", "nr"]},
            "atividade": st.column_config.TextColumn("Atividade", required=True),
            "consequencia": st.column_config.SelectboxColumn("Severidade", options=CONSEQUENCIAS),
            "validacao": st.column_config.TextColumn("Validação operacional"),
        },
        key=f"riscos_grade_{assinatura}_{st.session_state.get('riscos_grade_versao', 0)}",
    )
    try:
        alteracoes = preparar_alteracoes(editado, base["id"].tolist(), originais)
    except ValueError as exc:
        st.error(str(exc))
        alteracoes = None
    excluidas = sum(bool(d.get("excluido")) for _, d, _ in (alteracoes or []))
    confirmar = not excluidas
    if excluidas:
        confirmar = st.checkbox(f"Confirmar exclusão de {excluidas} atividade(s) do painel", key=f"riscos_excluir_{assinatura}")
    if st.button("💾 Salvar alterações das atividades", type="primary", disabled=not alteracoes or not confirmar, key=f"riscos_salvar_{assinatura}"):
        autor = str(usuario.get("nome") or usuario.get("usuario") or "Segurança")
        quando = datetime.now(timezone.utc).isoformat()
        try:
            for cid, dados, anterior in alteracoes:
                dados = dict(dados)
                dados.pop("id", None)
                dados["historico"] = list(dados.get("historico") or []) + [{
                    "em": quando, "por": autor,
                    "operacao": "exclusao" if dados.get("excluido") else ("inclusao" if cid is None else "edicao"),
                    "antes": {k: v for k, v in (anterior or {}).items() if k not in ("historico", "id")},
                }]
                payload = {"dados": dados, "atualizado_em": quando, "atualizado_por": autor}
                if cid is None:
                    sb("POST", "rh_seguranca_riscos", "", payload, "return=minimal")
                else:
                    sb("PATCH", "rh_seguranca_riscos", f"id=eq.{cid}", payload, "return=minimal")
            st.session_state["riscos_grade_versao"] = st.session_state.get("riscos_grade_versao", 0) + 1
            st.success("Alterações salvas. O gráfico será atualizado.")
            st.rerun()
        except Exception as exc:
            st.error(f"Não foi possível concluir todas as alterações. Atualize a página antes de tentar novamente: {exc}")
    if not df.empty:
        exportar = df[[c for c in campos if c != "id"]].rename(columns=ROTULOS)
        st.download_button("Baixar atividades selecionadas (CSV)", exportar.to_csv(index=False, sep=";").encode("utf-8-sig"), "atividades_riscos.csv", "text/csv")
