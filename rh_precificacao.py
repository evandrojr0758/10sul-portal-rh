"""Precificação administrativa de serviços; percentuais sobre o preço de venda."""
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, ROUND_CEILING
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo
import unicodedata

TABELA = "rh_precificacao_servicos"
CENTAVO = Decimal("0.01")


def exigir_admin(usuario):
    if not usuario or not usuario.get("id") or str(usuario.get("perfil") or "").upper() != "ADMIN":
        raise PermissionError("A precificação está disponível somente para o perfil Administrador.")


def decimal_valido(valor, nome, limite="999999999999.99"):
    try:
        numero = Decimal(str(valor))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError(f"Informe um valor válido para {nome}.") from None
    if not numero.is_finite() or numero < 0 or numero > Decimal(limite):
        raise ValueError(f"Informe um valor válido, não negativo, para {nome}.")
    return numero


def normalizar(dados):
    servico = str(dados.get("servico") or "").strip()
    if not servico or len(servico) > 200:
        raise ValueError("Informe o nome do serviço, com até 200 caracteres.")
    profissionais = decimal_valido(dados.get("profissionais", 1), "quantidade de profissionais", "100")
    if profissionais < 1 or profissionais != profissionais.to_integral_value():
        raise ValueError("A quantidade de profissionais deve ser um inteiro de 1 a 100.")
    saida = dict(servico=servico, categoria=str(dados.get("categoria") or "").strip(),
                 observacoes=str(dados.get("observacoes") or "").strip(),
                 profissionais=int(profissionais), ativo=bool(dados.get("ativo", True)))
    for campo, nome, limite, casas in (
        ("horas", "tempo estimado", "100000", "0.0001"),
        ("custo_hora", "custo por hora", "999999999999.99", "0.01"),
        ("materiais", "materiais", "999999999999.99", "0.01"),
        ("outros", "outros custos", "999999999999.99", "0.01"),
        ("despesas_pct", "impostos e despesas", "99.9999", "0.0001"),
        ("margem_pct", "margem desejada", "99.9999", "0.0001"),
    ):
        saida[campo] = decimal_valido(dados.get(campo, 0), nome, limite).quantize(Decimal(casas), rounding=ROUND_HALF_UP)
    if saida["despesas_pct"] + saida["margem_pct"] >= 100:
        raise ValueError("A soma de impostos/despesas e margem desejada deve ser menor que 100%.")
    manual = dados.get("preco_manual")
    saida["preco_manual"] = None if manual is None else decimal_valido(manual, "preço praticado").quantize(CENTAVO, rounding=ROUND_HALF_UP)
    return saida


def calcular(dados):
    d = normalizar(dados)
    mao_obra = (d["horas"] * d["profissionais"] * d["custo_hora"]).quantize(CENTAVO, rounding=ROUND_HALF_UP)
    custo = mao_obra + d["materiais"] + d["outros"]
    divisor = 1 - (d["margem_pct"] + d["despesas_pct"]) / 100
    sugerido = (custo / divisor).quantize(CENTAVO, rounding=ROUND_CEILING)
    preco = sugerido if d["preco_manual"] is None else d["preco_manual"]
    despesas = (preco * d["despesas_pct"] / 100).quantize(CENTAVO, rounding=ROUND_HALF_UP)
    lucro = preco - custo - despesas
    margem = lucro / preco * 100 if preco else None
    return dict(mao_obra=mao_obra, custo=custo, sugerido=sugerido, preco=preco,
                despesas=despesas, lucro=lucro, margem=margem)


def listar(sb, usuario):
    exigir_admin(usuario)
    rows, offset = [], 0
    while True:
        pagina = sb("GET", TABELA, f"select=*&order=servico.asc,id.asc&limit=500&offset={offset}") or []
        rows.extend(pagina)
        if len(pagina) < 500:
            return rows
        offset += 500


def salvar(sb, usuario, dados, anterior=None, novo_id=None):
    exigir_admin(usuario)
    payload = normalizar(dados)
    payload = {k: str(v) if isinstance(v, Decimal) else v for k, v in payload.items()}
    payload.update(atualizado_em=datetime.now(ZoneInfo("America/Sao_Paulo")).isoformat(),
                   atualizado_por=str(usuario.get("nome") or usuario.get("usuario") or usuario["id"]))
    if anterior:
        rid = str(UUID(str(anterior["id"])))
        versao = int(anterior["versao"])
        payload["versao"] = versao + 1
        rows = sb("PATCH", TABELA, f"id=eq.{rid}&versao=eq.{versao}", payload, "return=representation")
        if not rows:
            raise ValueError("Outro administrador alterou este serviço. Atualize a lista e confira os valores antes de salvar novamente.")
    else:
        payload.update(id=str(UUID(str(novo_id))) if novo_id else str(uuid4()),
                       criado_em=payload["atualizado_em"], criado_por=payload["atualizado_por"])
        rows = sb("POST", TABELA, "on_conflict=id", payload, "resolution=ignore-duplicates,return=representation")
    return rows


def dinheiro(valor):
    return "R$ " + f"{valor:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def chave_busca(valor):
    return "".join(c for c in unicodedata.normalize("NFD", str(valor or "").casefold()) if not unicodedata.combining(c))


def tela(sb):
    import pandas as pd
    import streamlit as st

    usuario = st.session_state.get("usuario_logado") or {}
    try:
        exigir_admin(usuario)
    except PermissionError as exc:
        st.error(str(exc))
        return
    st.subheader("💲 Precificação de Serviços")
    st.caption("Cadastre custos, simule a margem e mantenha sua tabela de serviços.")
    if st.session_state.get("prec_sucesso"):
        st.success(st.session_state.pop("prec_sucesso"))
    if st.button("Atualizar serviços", key="prec_atualizar"):
        st.rerun()
    try:
        registros = listar(sb, usuario)
    except Exception:
        st.error("Não foi possível carregar os serviços. Tente atualizar novamente.")
        return
    a, b = st.columns([2, 1])
    busca = chave_busca(a.text_input("Buscar serviço ou categoria", key="prec_busca"))
    status = b.selectbox("Exibir", ("Ativos", "Todos", "Inativos"), key="prec_status")
    linhas = [r for r in registros if (status == "Todos" or bool(r["ativo"]) == (status == "Ativos"))
              and busca in chave_busca(r["servico"] + " " + r.get("categoria", ""))]
    if linhas:
        tabela = []
        for r in linhas:
            c = calcular(r)
            tabela.append({"Serviço": r["servico"], "Categoria": r.get("categoria") or "—",
                "Horas": float(r["horas"]), "Profissionais": r["profissionais"],
                "Custo total": dinheiro(c["custo"]), "Preço sugerido": dinheiro(c["sugerido"]),
                "Preço praticado": dinheiro(c["preco"]),
                "Margem real": f"{c['margem']:.2f}%" if c["margem"] is not None else "—",
                "Status": "Ativo" if r["ativo"] else "Inativo"})
        st.dataframe(pd.DataFrame(tabela), hide_index=True, use_container_width=True)
    else:
        st.info("Nenhum serviço encontrado. Você pode cadastrar um novo abaixo.")

    por_id = {r["id"]: r for r in linhas}
    rid = st.selectbox("Cadastrar / editar serviço", [""] + list(por_id),
        format_func=lambda k: "➕ Novo serviço" if not k else f"{por_id[k]['servico']} • {por_id[k].get('categoria') or 'Sem categoria'} • {k[:8]}",
        key="prec_selecao")
    r = por_id.get(rid) or {}
    novo_id = st.session_state.setdefault("prec_novo_id", str(uuid4()))
    chave = f"prec_{rid or novo_id}_{r.get('versao', 0)}_"
    st.markdown("#### Dados e custos do serviço")
    a, b = st.columns([2, 1])
    dados = {"servico": a.text_input("Serviço *", value=r.get("servico", ""), max_chars=200, key=chave+"servico"),
             "categoria": b.text_input("Categoria", value=r.get("categoria", ""), key=chave+"categoria")}
    a, b, c = st.columns(3)
    dados["horas"] = a.number_input("Tempo estimado (horas)", min_value=0.0, max_value=100000.0,
        value=float(r.get("horas", 0)), step=0.25, format="%.4f", key=chave+"horas", help="Tempo de execução por profissional. Ex.: 1,5 hora = 1h30.")
    dados["profissionais"] = b.number_input("Quantidade de profissionais", min_value=1, max_value=100,
        value=int(r.get("profissionais", 1)), step=1, key=chave+"profissionais")
    dados["custo_hora"] = c.number_input("Custo por hora / profissional (R$)", min_value=0.0,
        value=float(r.get("custo_hora", 0)), step=1.0, format="%.2f", key=chave+"custo_hora")
    a, b = st.columns(2)
    for coluna, campo, label in ((a, "materiais", "Peças e materiais (R$)"), (b, "outros", "Outros custos (R$)")):
        dados[campo] = coluna.number_input(label, min_value=0.0, value=float(r.get(campo, 0)), step=1.0, format="%.2f", key=chave+campo)
    a, b = st.columns(2)
    dados["despesas_pct"] = a.number_input("Impostos e despesas sobre a venda (%)", min_value=0.0, max_value=99.9999,
        value=float(r.get("despesas_pct", 0)), step=0.5, format="%.4f", key=chave+"despesas_pct")
    dados["margem_pct"] = b.number_input("Margem desejada sobre a venda (%)", min_value=0.0, max_value=99.9999,
        value=float(r.get("margem_pct", 0)), step=0.5, format="%.4f", key=chave+"margem_pct")
    st.caption("Mão de obra = horas × profissionais × custo/hora. Preço sugerido = custo total ÷ [1 − (impostos/despesas + margem) ÷ 100]. Informe os percentuais aplicáveis ao serviço.")
    usar_sugerido = st.checkbox("Usar automaticamente o preço sugerido", value=r.get("preco_manual") is None, key=chave+"automatico")
    dados["preco_manual"] = None if usar_sugerido else st.number_input("Preço praticado (R$)", min_value=0.0,
        value=float(r.get("preco_manual") or 0), step=1.0, format="%.2f", key=chave+"manual")
    dados["ativo"] = st.checkbox("Serviço ativo", value=bool(r.get("ativo", True)), key=chave+"ativo")
    dados["observacoes"] = st.text_area("Observações", value=r.get("observacoes", ""), key=chave+"observacoes")
    erro = None
    try:
        calculo = calcular({**dados, "servico": dados["servico"] or "Simulação"})
    except ValueError as exc:
        erro = str(exc)
        st.error(erro)
    else:
        a, b, c, d = st.columns(4)
        a.metric("Custo total", dinheiro(calculo["custo"]))
        b.metric("Preço sugerido", dinheiro(calculo["sugerido"]))
        c.metric("Preço praticado", dinheiro(calculo["preco"]))
        d.metric("Margem real", f"{calculo['margem']:.2f}%" if calculo["margem"] is not None else "—")
        st.caption(f"Mão de obra: {dinheiro(calculo['mao_obra'])} • Impostos/despesas: {dinheiro(calculo['despesas'])} • Lucro estimado: {dinheiro(calculo['lucro'])}")
        if calculo["preco"] < calculo["sugerido"]:
            st.warning("O preço praticado está abaixo do sugerido para a margem desejada.")
    if st.button("Salvar serviço", type="primary", disabled=bool(erro), key=chave+"salvar"):
        try:
            salvar(sb, usuario, dados, anterior=r or None, novo_id=novo_id)
        except (ValueError, PermissionError) as exc:
            st.error(str(exc))
        except Exception:
            st.error("Não foi possível confirmar o salvamento. Atualize a lista para conferir antes de tentar novamente.")
        else:
            st.session_state.pop("prec_novo_id", None)
            st.session_state["prec_sucesso"] = "Serviço salvo. Os valores ficam disponíveis ao reabrir o portal."
            st.rerun()
