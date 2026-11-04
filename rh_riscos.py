"""Mapeamento preventivo de atividades, acessível pelo perfil Segurança."""
from datetime import date, datetime, timezone
import pandas as pd
import streamlit as st
import altair as alt

CONSEQUENCIAS = ["1 — Leve", "2 — Moderada", "3 — Grave / Crítica", "A validar"]
PROBABILIDADES = ["1 — Baixa", "2 — Média", "3 — Alta", "A avaliar"]
FREQUENCIAS = ["Diária", "Semanal", "Mensal", "Sob demanda"]
NIVEIS_RISCO = ["Alto", "Médio", "Baixo", "A validar"]
CORES_NIVEIS = ["#dc2626", "#eab308", "#16a34a", "#64748b"]

CORES = ["#16a34a", "#eab308", "#dc2626", "#64748b"]


def normalizar_severidade(valor):
    texto = str(valor or "").strip()
    if texto in CONSEQUENCIAS:
        return texto
    return {
        "Fatalidade possível": "3 — Grave / Crítica",
        "Amputação possível": "3 — Grave / Crítica",
        "Afastamento possível": "2 — Moderada",
        "Lesão sem afastamento possível": "1 — Leve",
        "Baixo potencial": "1 — Leve",
    }.get(texto, "A validar")


def normalizar_frequencia(valor):
    texto = str(valor or "").strip()
    return texto or "Diária"


def normalizar_probabilidade(valor):
    return valor if isinstance(valor, str) and valor in PROBABILIDADES else "A avaliar"


def severidade(consequencia):
    return {"1 — Leve": "BAIXA", "2 — Moderada": "MODERADA",
            "3 — Grave / Crítica": "CRÍTICA"}.get(normalizar_severidade(consequencia), "A VALIDAR")


def calcular_risco(probabilidade, consequencia):
    """Matriz aprovada: 1–2 Baixo, 3–4 Médio, 6–9 Alto."""
    p = normalizar_probabilidade(probabilidade)
    s = normalizar_severidade(consequencia)
    if p not in PROBABILIDADES[:3] or s not in CONSEQUENCIAS[:3]:
        return None, "A validar"
    pontos = (PROBABILIDADES.index(p) + 1) * (CONSEQUENCIAS.index(s) + 1)
    return pontos, "Baixo" if pontos <= 2 else "Médio" if pontos <= 4 else "Alto"


def aplicar_risco(dados):
    dados["pontuacao_risco"], dados["nivel_risco"] = calcular_risco(
        dados.get("probabilidade"), dados.get("consequencia"),
    )
    return dados


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
        x=alt.X("atividades:Q", title=None, axis=None,
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


def tela_riscos(sb, usuario, somente_consulta=False):
    if str((usuario or {}).get("perfil") or "").strip().upper() != "SEGURANCA":
        st.error("O mapa de riscos está disponível somente no acesso da Segurança.")
        return
    st.title("🦺 Mapa de riscos e plano preventivo")
    somente_consulta = somente_consulta or str(st.query_params.get("consulta_riscos", "")) == "1"
    if not somente_consulta:
        st.link_button("🔎 Abrir link somente para consulta", "?seguranca=1&consulta_riscos=1")
    else:
        st.info("Modo consulta: edição, inclusão e exclusão desabilitadas. Mantém o acesso autenticado da Segurança.")
    st.caption("Base: matriz de outubro/2026 e mapeamento completo EXEMPLO 2. As severidades importadas são triagens; a Segurança deve validar cada cenário em campo.")
    st.info("Severidade: 1 — Leve (sem afastamento); 2 — Moderada (com afastamento ou danos materiais relevantes); 3 — Grave / Crítica (morte, mutilação ou danos catastróficos). Nível de risco = P × S: 1–2 Baixo; 3–4 Médio; 6–9 Alto. Preencha P e S para calcular.")
    with st.expander("Critérios de Probabilidade e Severidade"):
        st.markdown("""
**Probabilidade (P)**
- **1 — Baixa:** atividade com risco controlado e pouca chance de acidente.
- **2 — Média:** risco conhecido; a atividade exige atenção e eventos podem ocorrer.
- **3 — Alta:** alto potencial de falha, exposição direta ao risco ou histórico de acidentes.

**Severidade (S)**
- **1 — Leve:** lesões simples, sem afastamento.
- **2 — Moderada:** lesões com afastamento ou danos materiais relevantes.
- **3 — Grave / Crítica:** morte, mutilação ou danos catastróficos.
""")
    try:
        regs = sb("GET", "rh_seguranca_riscos", "select=*&order=id.asc&limit=1000") or []
    except Exception as exc:
        st.error(f"Não foi possível carregar o mapeamento: {exc}")
        return
    if not somente_consulta:
        from rh_riscos_offline_pack import pacote_offline
        st.download_button("📦 Baixar sistema offline — mapa de riscos", pacote_offline(regs), "10Sul_Seguranca_Offline.zip", "application/zip")
        st.caption("Base principal no computador. O pacote inclui cópia atual do mapa e instruções de instalação e conexão. Não inclui senhas ou chaves. A primeira instalação e configuração da sincronização precisam ser feitas no computador autorizado.")
    linhas = [dict(r.get("dados") or {}, id=r["id"]) for r in regs if not (r.get("dados") or {}).get("excluido")]
    preliminares = sum(bool(r.get("probabilidade_preliminar")) and r.get("validacao") != "Validada" for r in linhas)
    if preliminares:
        st.caption(f"{preliminares} atividade(s) com probabilidade preliminar, pendente de revisão em campo pela Segurança. A justificativa está na aba Validar / editar atividade.")
    df = pd.DataFrame(linhas, columns=list(PADRAO) + ["id"])
    df["frequencia_atividade"] = df["frequencia_atividade"].fillna("Diária").replace("", "Diária")
    df["consequencia"] = df["consequencia"].map(normalizar_severidade)
    df["probabilidade"] = df["probabilidade"].map(normalizar_probabilidade)
    df["severidade"] = df["consequencia"].map(severidade)
    calculados = [calcular_risco(p, s) for p, s in zip(df["probabilidade"], df["consequencia"])]
    df["pontuacao_risco"] = pd.Series([r[0] for r in calculados], index=df.index, dtype=object)
    df["nivel_risco"] = [r[1] for r in calculados]
    if somente_consulta:
        consulta = st.text_input("Buscar atividade ou risco")
        visao = df
        if consulta:
            visao = df[df["atividade"].str.contains(consulta, case=False, regex=False, na=False) | df["riscos"].str.contains(consulta, case=False, regex=False, na=False)]
        st.altair_chart(grafico_niveis(visao), use_container_width=True)
        st.dataframe(visao.drop(columns=["id"], errors="ignore").rename(columns=ROTULOS), hide_index=True, use_container_width=True)
        mostrar_evolucao(regs)
        return
    mostrar_evolucao(regs)
    painel, plano, editar, frequencia_monitor = st.tabs(["Painel e atividades", "Plano de ação", "Validar / editar atividade", "Frequência no Monitor"])
    with painel:
        cols = st.columns(4)
        cols[0].metric("Atividades mapeadas", len(df))
        cols[1].metric("Potencial crítico", int(df["severidade"].eq("CRÍTICA").sum()))
        cols[2].metric("Potencial moderado", int(df["severidade"].eq("MODERADA").sum()))
        cols[3].metric("A validar em campo", int(df["validacao"].ne("Validada").sum()))
        with st.expander("Como a probabilidade foi preenchida — mapa de critérios"):
            st.markdown("**Preenchimento preliminar por inferência a partir das atividades, perigos e controles cadastrados.** Frequência, duração da exposição, eficácia dos controles e histórico de acidentes não foram conferidos em campo.")
            st.table(pd.DataFrame([
                {"Probabilidade proposta": "1 — Baixa", "Atividades consideradas": "Serviços administrativos em escritório; pedido e entrega de materiais (PCM)", "Critério usado na triagem": "Rotinas com controles descritos: organização, carrinho, cadeira ergonômica e pausas."},
                {"Probabilidade proposta": "2 — Média", "Atividades consideradas": "Demais atividades da triagem inicial", "Critério usado na triagem": "Perigos conhecidos e controles cadastrados, sem dados suficientes sobre a exposição real."},
                {"Probabilidade proposta": "3 — Alta", "Atividades consideradas": "Socorro mecânico; trabalho em altura", "Critério usado na triagem": "Condições externas variáveis e exposição a quedas, consideradas como hipótese para revisão prioritária."},
            ]))
            st.info("O perigo da atividade, sozinho, não comprova uma probabilidade alta. As propostas devem ser revistas pela Segurança considerando a exposição e a eficácia dos controles. O quadro descreve a triagem inicial; as classificações atuais aparecem no detalhamento abaixo.")
            st.markdown("**Justificativa por atividade**")
            justificativas = [{
                "Atividade": r.get("atividade") or "",
                "Probabilidade atual": normalizar_probabilidade(r.get("probabilidade")),
                "Justificativa da triagem": r.get("justificativa_probabilidade") or "Sem justificativa de triagem registrada.",
                "Validação operacional": r.get("validacao") or "Pendente",
            } for r in linhas]
            st.dataframe(pd.DataFrame(justificativas), use_container_width=True, hide_index=True)
            st.caption("Referência: NR-1, item 1.5.4.4.5.4 — exposição ao perigo e eficácia das medidas de prevenção.")
        f1, f2, f3, f4 = st.columns(4)
        busca = f1.text_input("Buscar atividade ou risco", key="riscos_busca")
        categoria = f2.selectbox("Severidade", ["TODAS"] + CONSEQUENCIAS, key="riscos_consequencia")
        validacao = f3.selectbox("Validação operacional", ["TODAS", "Pendente", "Validada"], key="riscos_validacao")
        probabilidade_filtro = f4.selectbox("Probabilidade", ["TODAS"] + PROBABILIDADES, key="riscos_probabilidade")
        view = df.copy()
        if probabilidade_filtro != "TODAS":
            view = view[view["probabilidade"].eq(probabilidade_filtro)]
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
                x=alt.X("atividades:Q", title=None, axis=None,
                        scale=alt.Scale(domain=[0, max(1, int(contagem["atividades"].max())) * 1.15])),
                y=alt.Y("consequencia:N", title=None, sort=CONSEQUENCIAS),
                color=alt.Color("consequencia:N", scale=alt.Scale(domain=CONSEQUENCIAS, range=CORES), legend=None),
                opacity=alt.condition(clique, alt.value(1), alt.value(0.45)),
                tooltip=[alt.Tooltip("consequencia:N", title="Severidade"), alt.Tooltip("atividades:Q", title="Atividades")],
            ).add_params(clique).properties(height=280)
            rotulos = alt.Chart(contagem).mark_text(
                align="left", baseline="middle", dx=6, fontWeight="bold",
            ).encode(
                x=alt.X("atividades:Q", title=None, axis=None),
                y=alt.Y("consequencia:N", title=None, sort=CONSEQUENCIAS),
                text=alt.Text("atividades:Q", format="d"),
            )
            grafico = grafico + rotulos
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
        st.caption("Nível calculado por P × S: 1–2 Baixo; 3–4 Médio; 6–9 Alto. Sem probabilidade ou severidade, fica A validar.")
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
            import importlib
            gerar_pdf_riscos = importlib.reload(importlib.import_module("rh_riscos_export")).gerar_pdf_riscos
            filtros_pdf = f"Probabilidade: {probabilidade_filtro} | Busca: {busca or 'Todas'} | Severidade: {categoria} | Validação: {validacao}"
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
            import importlib
            gerar_excel_riscos = importlib.reload(importlib.import_module("rh_riscos_excel")).gerar_excel_riscos
            st.download_button(
                "📊 Baixar Excel formatado com gráficos",
                data=gerar_excel_riscos(view, filtros_pdf),
                file_name=f"mapa_de_riscos_{date.today():%Y-%m-%d}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="riscos_baixar_excel",
            )
        editar_lote(view, sb, usuario, linhas)
        mostrar_atividades(view, sb, usuario, linhas)
    with frequencia_monitor:
        import importlib
        monitor = importlib.reload(importlib.import_module("rh_riscos_monitor"))
        monitor.tela(sb, linhas)
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
            if original.get("probabilidade_preliminar"):
                st.info("Probabilidade preliminar: " + str(original.get("justificativa_probabilidade") or "Revisar em campo."))
            dados = dict(original)
            dados["atividade"] = st.text_input("Nome da atividade", value=str(original.get("atividade") or ""))
            freq_atual = normalizar_frequencia(original.get("frequencia_atividade"))
            dados["frequencia_atividade"] = st.selectbox("Frequência da atividade", FREQUENCIAS, index=FREQUENCIAS.index(freq_atual) if freq_atual in FREQUENCIAS else 0)
            from rh_riscos_monitor import regra_atividade
            termos_padrao, _ = regra_atividade(original)
            dados["termos_monitor"] = st.text_area(
                "Termos para localizar na descrição ASN (um por linha)",
                value=original.get("termos_monitor") if isinstance(original.get("termos_monitor"), str) else "\n".join(termos_padrao),
                help="A busca ignora acentos e maiúsculas. A regra ITR/Revisão para mapeamento e calibração é aplicada separadamente.",
            )
            dados["nr"] = st.text_input("NR informada na matriz", value=str(original.get("nr") or ""))
            for campo in ["riscos", "controles", "cenario", "lacuna", "acao"]:
                dados[campo] = st.text_area(ROTULOS[campo], value=str(original.get(campo) or ""))
            atual = normalizar_severidade(original.get("consequencia"))
            prob_atual = normalizar_probabilidade(original.get("probabilidade"))
            dados["probabilidade"] = st.selectbox("Probabilidade (P)", PROBABILIDADES, index=PROBABILIDADES.index(prob_atual))
            dados["consequencia"] = st.selectbox("Severidade", CONSEQUENCIAS, index=CONSEQUENCIAS.index(atual) if atual in CONSEQUENCIAS else 3)
            st.caption("O nível de risco será calculado ao salvar: P × S. 1–2 Baixo; 3–4 Médio; 6–9 Alto.")
            dados["validacao"] = st.selectbox("Validação operacional", ["Pendente", "Validada"], index=1 if original.get("validacao") == "Validada" else 0)
            dados["validadores"] = st.text_input("Quem validou (um ou mais nomes)", value=str(original.get("validadores") or ""))
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
            elif dados["validacao"] == "Validada" and (dados["consequencia"] == "A validar" or dados["probabilidade"] == "A avaliar" or not dados["cenario"].strip()):
                st.error("Para validar, informe o cenário, a probabilidade e a severidade.")
            elif dados["status_acao"] == "Concluída" and not dados["evidencia"].strip():
                st.error("Informe a evidência antes de concluir a ação.")
            else:
                aplicar_risco(dados)
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


ROTULOS = {"validadores": "Quem validou","frequencia_observada": "Frequência observada (Monitor)","frequencia_atividade": "Frequência da atividade","pontuacao_risco": "Pontuação (P × S)","probabilidade": "Probabilidade (P)","nivel_risco": "Nível de risco", "atividade": "Atividade", "riscos": "Risco / perigos", "controles": "Controles atuais", "cenario": "Cenário de acidente / exposição", "consequencia": "Severidade", "severidade": "Severidade", "validacao": "Validação operacional", "responsavel": "Responsável", "nr": "NR informada na matriz", "lacuna": "Lacuna identificada em campo", "acao": "Ação adicional proposta", "hierarquia": "Hierarquia do controle", "prazo": "Prazo", "status_acao": "Status da ação", "evidencia": "Evidência / reavaliação", "probabilidade_residual": "Probabilidade residual", "severidade_residual": "Severidade residual", "nivel_residual": "Nível residual"}


PADRAO = {
    "validadores": "", "frequencia_atividade": "Diária", "atividade": "", "riscos": "", "controles": "", "responsavel": "", "nr": "",
    "probabilidade": "A avaliar", "consequencia": "A validar", "validacao": "Pendente", "cenario": "",
    "lacuna": "", "acao": "", "hierarquia": "", "prazo": None,
    "status_acao": "Não iniciada", "evidencia": "",
    "probabilidade_residual": "Não avaliada", "severidade_residual": "Não avaliada",
    "nivel_residual": "Não avaliado", "pontuacao_risco": None, "nivel_risco": None, "classificacao_original": "", "severidade_original": "",
}
CAMPOS_GRADE = ["validadores", "frequencia_atividade", "probabilidade", "validacao", "atividade", "consequencia", "riscos", "controles", "responsavel", "nr"]


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
        dados["frequencia_atividade"] = normalizar_frequencia(dados["frequencia_atividade"])
        if dados["frequencia_atividade"] not in FREQUENCIAS:
            raise ValueError("Selecione uma frequência válida: Diária, Semanal, Mensal ou Sob demanda.")
        dados["probabilidade"] = dados["probabilidade"] or "A avaliar"
        if dados["probabilidade"] not in PROBABILIDADES:
            raise ValueError("Selecione uma probabilidade válida.")
        dados["consequencia"] = dados["consequencia"] or "A validar"
        if dados["consequencia"] not in CONSEQUENCIAS:
            raise ValueError("Selecione uma severidade válida.")
        aplicar_risco(dados)
        dados["validacao"] = dados["validacao"] or "Pendente"
        if dados["validacao"] not in ("Pendente", "Validada"):
            raise ValueError("Selecione uma validação operacional válida.")
        if novo or any(dados.get(c) != (normalizar_severidade(anterior.get(c)) if c == "consequencia" else normalizar_probabilidade(anterior.get(c)) if c == "probabilidade" else normalizar_frequencia(anterior.get(c)) if c == "frequencia_atividade" else anterior.get(c)) for c in CAMPOS_GRADE):
            if dados["validacao"] == "Validada" and (
                dados["consequencia"] == "A validar" or dados["probabilidade"] == "A avaliar" or not str(dados.get("cenario") or "").strip()
            ):
                raise ValueError(f"Para validar '{nome}', informe a probabilidade, a severidade e o cenário na aba Validar / editar atividade.")
            alteracoes.append((cid, dados, anterior))
    for cid in permitidos - vistos:
        anterior = por_id[cid]
        dados = dict(anterior, excluido=True)
        alteracoes.append((cid, dados, anterior))
    return alteracoes


def mostrar_atividades(df, sb, usuario, originais):
    import hashlib
    st.subheader(f"Atividades selecionadas ({len(df)})")
    st.caption("Edite as células, use a última linha para acrescentar e selecione uma linha para excluir. Clique em Salvar alterações. Probabilidade, severidade e validação operacional são editáveis. Pontuação e nível de risco são calculados ao salvar. Para marcar Validada, informe a probabilidade, a severidade e o cenário na aba Validar / editar atividade.")
    import importlib
    monitor = importlib.reload(importlib.import_module("rh_riscos_monitor"))
    df = df.copy()
    try:
        observadas, contexto_monitor = monitor.observacao_na_tabela(sb, originais)
        df["frequencia_observada"] = df["id"].map(lambda cid: observadas.get(str(cid), "Sem correspondência"))
        st.caption(contexto_monitor)
    except Exception as exc:
        df["frequencia_observada"] = "Consulta indisponível"
        st.caption(f"Não foi possível atualizar a frequência observada: {exc}")
    campos = ["id", "atividade", "frequencia_atividade", "frequencia_observada", "probabilidade", "consequencia", "pontuacao_risco", "nivel_risco", "validacao", "riscos", "validadores", "controles", "responsavel", "nr"]
    base = df[campos].copy()
    # Categorias explícitas mantêm os três campos como seletores no editor.
    for campo, opcoes in (
        ("frequencia_atividade", FREQUENCIAS),
        ("probabilidade", PROBABILIDADES),
        ("consequencia", CONSEQUENCIAS),
        ("validacao", ["Pendente", "Validada"]),
    ):
        base[campo] = pd.Categorical(base[campo], categories=opcoes)
    # Uma seleção ou gravação diferente nunca reutiliza deltas de outras linhas.
    assinatura = hashlib.sha256(base[["id"]].to_json(orient="records").encode()).hexdigest()[:16]
    editado = st.data_editor(
        base, use_container_width=True, hide_index=True, num_rows="dynamic",
        disabled=["id", "frequencia_observada", "pontuacao_risco", "nivel_risco"],
        column_config={
            "id": None,
            "frequencia_observada": st.column_config.TextColumn("Frequência observada (Monitor)", width="medium", help="Calculada pela ASN: dias com registro e quantidade de OS. Não altera a frequência informada."),
            "frequencia_atividade": st.column_config.SelectboxColumn("Frequência da atividade", options=FREQUENCIAS, default="Diária", required=True),
            "probabilidade": st.column_config.SelectboxColumn("Probabilidade (P)", options=PROBABILIDADES),
            "nivel_risco": st.column_config.TextColumn("Nível de risco (automático)"),
            "pontuacao_risco": st.column_config.NumberColumn("P × S", format="%d"),
            **{c: st.column_config.TextColumn(ROTULOS[c]) for c in ["atividade", "riscos", "validadores", "controles", "responsavel", "nr"]},
            "atividade": st.column_config.TextColumn("Atividade", required=True),
            "consequencia": st.column_config.SelectboxColumn("Severidade", options=CONSEQUENCIAS),
            "validacao": st.column_config.SelectboxColumn("Validação operacional", options=["Pendente", "Validada"], width="medium", default="Pendente"),
        },
        key=f"riscos_grade_matriz_ps_v3_{assinatura}_{st.session_state.get('riscos_grade_versao', 0)}",
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
    if st.button("💾 Salvar alterações das atividades", type="primary", disabled=not confirmar, key=f"riscos_salvar_{assinatura}"):
        if alteracoes is None:
            st.error("Corrija os campos indicados antes de salvar.")
            return
        if not alteracoes:
            st.info("Nenhuma alteração encontrada. Termine a edição da célula com Enter e clique em Salvar.")
            return
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
        with st.expander("Excluir atividades"):
            alvos = st.multiselect("Atividades para excluir", df["id"].tolist(), format_func=lambda i: str(df.loc[df["id"].eq(i), "atividade"].iloc[0]))
            confirmar_exclusao = st.checkbox("Confirmo a exclusão das atividades selecionadas")
            if st.button("Excluir atividades selecionadas", disabled=not alvos or not confirmar_exclusao):
                try:
                    for cid in alvos:
                        anterior = next(r for r in originais if r["id"] == cid)
                        gravar_atividade(sb, usuario, cid, dict(anterior, excluido=True), anterior)
                    st.session_state["riscos_grade_versao"] = st.session_state.get("riscos_grade_versao", 0) + 1
                    st.rerun()
                except Exception as exc:
                    st.error(f"Não foi possível concluir a exclusão: {exc}")
        exportar = df[[c for c in campos if c != "id"]].rename(columns=ROTULOS)
        st.download_button("Baixar atividades selecionadas (CSV)", exportar.to_csv(index=False, sep=";").encode("utf-8-sig"), "atividades_riscos.csv", "text/csv")



def gravar_atividade(sb, usuario, cid, dados, anterior):
    dados = dict(dados)
    dados.pop('id', None)
    quando = datetime.now(timezone.utc).isoformat()
    autor = str(usuario.get('nome') or usuario.get('usuario') or 'Segurança')
    dados['historico'] = list(dados.get('historico') or []) + [{
        'em': quando, 'por': autor,
        'operacao': 'exclusao' if dados.get('excluido') else 'edicao',
        'antes': {k:v for k,v in anterior.items() if k not in ('id','historico')},
    }]
    sb('PATCH', 'rh_seguranca_riscos', f'id=eq.{int(cid)}',
       {'dados':dados,'atualizado_em':quando,'atualizado_por':autor}, 'return=minimal')


def editar_lote(view, sb, usuario, originais):
    with st.expander('Alterar em lote as atividades filtradas'):
        st.caption(f'{len(view)} atividades nos filtros atuais. Somente os campos marcados serão alterados. O nível de risco é recalculado por P × S.')
        with st.form('riscos_lote'):
            mudar_p = st.checkbox('Alterar probabilidade')
            p = st.selectbox('Nova probabilidade', PROBABILIDADES)
            mudar_s = st.checkbox('Alterar severidade')
            s = st.selectbox('Nova severidade', CONSEQUENCIAS)
            mudar_risco = st.checkbox('Alterar descrição do risco')
            risco = st.text_area('Novo risco / perigo')
            mudar_validadores = st.checkbox('Alterar quem validou')
            validadores = st.text_input('Quem validou — nomes separados por vírgula')
            aplicar = st.form_submit_button('Aplicar às atividades filtradas', disabled=view.empty)
        if aplicar:
            campos = {}
            if mudar_p: campos['probabilidade'] = p
            if mudar_s: campos['consequencia'] = s
            if mudar_risco: campos['riscos'] = risco
            if mudar_validadores: campos['validadores'] = validadores
            if not campos:
                st.warning('Marque pelo menos um campo para alterar.')
                return
            preparados = []
            for cid in view['id']:
                anterior = next(r for r in originais if r['id'] == cid)
                dados = aplicar_risco(dict(anterior, **campos))
                if dados.get('validacao') == 'Validada' and (dados['nivel_risco'] == 'A validar' or not str(dados.get('cenario') or '').strip()):
                    st.error('Uma atividade validada ficaria sem critérios completos. Ajuste a seleção antes de aplicar.')
                    return
                preparados.append((cid, dados, anterior))
            try:
                for cid, dados, anterior in preparados:
                    gravar_atividade(sb, usuario, cid, dados, anterior)
                st.session_state['riscos_grade_versao'] = st.session_state.get('riscos_grade_versao', 0) + 1
                st.rerun()
            except Exception as exc:
                st.error(f'Não foi possível concluir todas as alterações. Atualize antes de repetir: {exc}')


def evolucao_riscos(regs):
    # Reconstrói somente os estados comprovados no histórico. Não inventa meses anteriores.
    eventos, estado = [], {}
    agora = datetime.now(timezone.utc).isoformat()
    for r in regs:
        cid, atual = r['id'], dict(r.get('dados') or {})
        hist = sorted([h for h in atual.get('historico', []) if h.get('em')], key=lambda h:h['em'])
        if hist:
            primeiro = hist[0]
            estado[cid] = dict(primeiro.get('antes') or {})
            for i,h in enumerate(hist):
                depois = hist[i+1].get('antes', {}) if i+1<len(hist) else atual
                eventos.append((h['em'],cid,depois))
        else:
            # Sem histórico, o estado só é conhecido na consulta atual.
            eventos.append((agora,cid,atual))
    linhas = []
    def contar(em):
        contagem = {n:0 for n in NIVEIS_RISCO}
        for d in estado.values():
            if not d or d.get('excluido'): continue
            n = calcular_risco(d.get('probabilidade'),d.get('consequencia'))[1]
            contagem[n] += 1
        linhas.extend({'em':em,'nivel':n,'atividades':q} for n,q in contagem.items())
    if eventos:
        # Estado imediatamente antes da primeira alteração documentada.
        inicio = min(e[0] for e in eventos)
        baseline = (pd.to_datetime(inicio,utc=True)-pd.Timedelta(microseconds=1)).isoformat()
        contar(baseline)
        for em in sorted(set(e[0] for e in eventos)):
            for t,cid,d in eventos:
                if t==em: estado[cid]=d
            contar(em)
    return pd.DataFrame(linhas,columns=['em','nivel','atividades'])


def mostrar_evolucao(regs):
    with st.expander('Evolução do mapa de risco'):
        st.caption('Evolução por nível calculado (P × S), baseada nas alterações registradas. Atividades sem histórico entram na data da consulta; inclusão/exclusão também altera os totais. Baixo corresponde ao nível leve da matriz.')
        dados = evolucao_riscos(regs)
        if dados.empty:
            st.info('Ainda não há estados registrados para comparação.')
            return
        dados['em'] = pd.to_datetime(dados['em'],utc=True).dt.tz_convert('America/Sao_Paulo')
        st.altair_chart(alt.Chart(dados).mark_line(point=True,interpolate='step-after').encode(
            x=alt.X('em:T',title='Data / hora'),y=alt.Y('atividades:Q',title='Atividades',axis=alt.Axis(tickMinStep=1)),
            color=alt.Color('nivel:N',scale=alt.Scale(domain=NIVEIS_RISCO,range=CORES_NIVEIS)),
            tooltip=['em:T','nivel:N','atividades:Q']),use_container_width=True)
        st.download_button('Baixar evolução (CSV)',dados.to_csv(index=False,sep=';').encode('utf-8-sig'),'evolucao_riscos.csv','text/csv')
