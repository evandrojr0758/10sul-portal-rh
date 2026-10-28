"""Regras e apuração da Fabricação, separadas das demais frentes."""
import calendar
import hashlib
import json
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP


METAS = {
    "Chapa de Dimensão": 3, "Chapa RMT": 4, "Régua 0,75 m": 15,
    "Régua 1 m": 15, "Régua 1,5 m": 15, "Régua 3 m": 16,
    "Chapa de Assoalho": 13, "Mão Francesa": 16,
}
CONFIG = {"desconto_2_atestados_percentual": 50, "desconto_item_percentual": 5,
          "limite_he_sem_solicitacao": 5, "metas": METAS}


def numero(regra, campo, padrao):
    valor = regra.get(campo)
    return float(padrao if valor is None else valor)


def configuracao(regra):
    cfg = {**CONFIG, **(regra.get("fabricacao_config") or {})}
    cfg["metas"] = {**METAS, **cfg.get("metas", {})}
    return cfg


def resumo_estoque(registros, metas):
    medias = {}
    for item in metas:
        valores = [float(r["quantidades"][item]) for r in registros
                   if (r.get("quantidades") or {}).get(item) is not None]
        medias[item] = sum(valores) / len(valores) if valores else None
    # Uma mudança de estoque ou meta exige nova conferência antes do fechamento.
    base = {"metas": metas, "registros": sorted(
        [{"data": str(r["data"]), "quantidades": r["quantidades"]} for r in registros],
        key=lambda r: r["data"])}
    assinatura = hashlib.sha256(json.dumps(base, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    return medias, assinatura


def calcular(salario, faltas, atestados, dna, horas, medias, conferido, regra):
    cfg = configuracao(regra)
    integral = Decimal(str(salario or 0)) * Decimal(str(numero(regra, "percentual_salario", 35))) / 100
    integral = integral.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    motivos, pendencias = [], []
    if salario is None or float(salario) <= 0:
        pendencias.append("informar salário-base")
    if horas is None:
        pendencias.append("informar horas extras sem solicitação (inclusive zero)")
    if not conferido:
        pendencias.append("conferir estoque mensal")
    if any(medias.get(item) is None for item in cfg["metas"]):
        pendencias.append("informar estoque dos 8 itens")
    # O termo não define o desconto para meio período; não presumir penalidade.
    if 0 < float(atestados) <= 2 and not float(atestados).is_integer():
        pendencias.append("atestado fracionado: definir critério da Fabricação")
    if faltas > 0:
        motivos.append(f"{faltas} falta(s)")
    dna_min = int(numero(regra, "dna_minimo", 2))
    if dna < dna_min:
        motivos.append(f"DNA {dna}/{dna_min}")
    if horas is not None and float(horas) > float(cfg["limite_he_sem_solicitacao"]):
        motivos.append(f"{float(horas):g}h extras sem solicitação: acima de {cfg['limite_he_sem_solicitacao']:g}h")
    if atestados > 2:
        motivos.append(f"{atestados:g} dias de atestado: acima de 2 dias")
    zerada = bool(motivos)
    desconto = Decimal("0")
    if atestados in (1, 2):
        pct = numero(regra, "desconto_1_atestado_percentual", 25) if atestados == 1 else float(cfg["desconto_2_atestados_percentual"])
        desconto += Decimal(str(pct))
        motivos.append(f"{atestados:g} dia(s) de atestado (-{pct:g}%)")
    abaixo = [item for item, meta in cfg["metas"].items()
              if medias.get(item) is not None and medias[item] < float(meta)]
    if abaixo:
        pct = Decimal(str(cfg["desconto_item_percentual"])) * len(abaixo)
        desconto += pct
        motivos.append(f"Estoque: {len(abaixo)} item(ns) abaixo da meta (-{pct}%): " + ", ".join(abaixo))
    if pendencias:
        return float(integral), None, " • ".join(pendencias + motivos)
    valor = Decimal("0") if zerada else max(Decimal("0"), integral * (1 - desconto / 100))
    return float(integral), float(valor.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)), " • ".join(motivos) or "Requisitos atendidos"


def tela_regra(st, r):
    cfg = configuracao(r)
    st.caption("35% do salário-base. Estoque: média mensal dos registros diários; desconto por item abaixo da meta.")
    a, b, c = st.columns(3)
    pct = a.number_input("Bonificação integral (% do salário)", 0.0, 100.0, numero(r, "percentual_salario", 35), key="fab_reg_pct")
    d1 = b.number_input("1 dia de atestado — desconto (%)", 0.0, 100.0, numero(r, "desconto_1_atestado_percentual", 25), key="fab_reg_at1")
    d2 = c.number_input("2 dias de atestado — desconto (%)", 0.0, 100.0, float(cfg["desconto_2_atestados_percentual"]), key="fab_reg_at2")
    a, b, c = st.columns(3)
    item = a.number_input("Desconto por item abaixo da meta (%)", 0.0, 100.0, float(cfg["desconto_item_percentual"]), key="fab_reg_item")
    limite = b.number_input("Limite de HE sem solicitação (h)", min_value=0.0, value=float(cfg["limite_he_sem_solicitacao"]), key="fab_reg_he")
    dna = c.number_input("DNA mínimo no mês", min_value=0, value=int(numero(r, "dna_minimo", 2)), key="fab_reg_dna")
    metas = {}
    st.markdown("**Metas de estoque por item**")
    cols = st.columns(4)
    for n, (nome, meta) in enumerate(cfg["metas"].items()):
        metas[nome] = cols[n % 4].number_input(nome, min_value=0.0, value=float(meta), key=f"fab_meta_{n}")
    st.info("Falta injustificada, DNA abaixo do mínimo, mais de 2 dias de atestado ou HE sem solicitação acima do limite zeram a bonificação. Descontos de estoque e atestado são somados sobre o valor integral.")
    return {"percentual_salario": pct, "desconto_1_atestado_percentual": d1, "dna_minimo": dna,
            "fabricacao_config": {"desconto_2_atestados_percentual": d2, "desconto_item_percentual": item,
                                   "limite_he_sem_solicitacao": limite, "metas": metas}}


def tela_lancamentos(st, pd, sb, ano, mes, colabs, regra, usr, bloqueada):
    cfg = configuracao(regra)
    ini = date(ano, mes, 1)
    fim = date(ano, mes, calendar.monthrange(ano, mes)[1])
    regs = sb("GET", "rh_fabricacao_estoque", f"select=*&data=gte.{ini}&data=lte.{fim}&order=data.asc") or []
    ap = sb("GET", "rh_fabricacao_apuracao", f"select=*&ano=eq.{ano}&mes=eq.{mes}") or []
    medias, assinatura = resumo_estoque(regs, cfg["metas"])
    por_id = {int(r["colaborador_id"]): r for r in ap}
    def verificar_aberta():
        atuais = sb("GET", "rh_gratificacao_aprovacoes", f"select=status&ano=eq.{ano}&mes=eq.{mes}&order=id.desc&limit=1") or []
        if atuais and atuais[0].get("status") in ("AGUARDANDO_AUTORIZACAO", "AUTORIZADA"):
            raise ValueError("Competência enviada/autorizada em outra sessão. Recarregue a tela.")
    with st.expander("🏭 Fabricação — estoque e horas extras", expanded=True):
        st.caption("Estoque compartilhado pela frente; horas extras e conferência por colaborador. Informe somente horas SEM solicitação Suzano/10 Sul.")
        if bloqueada:
            st.info("Competência enviada ou autorizada: lançamentos bloqueados.")
        with st.form(f"fab_estoque_{ano}_{mes}"):
            dia = st.date_input("Data do estoque", value=min(max(date.today(), ini), fim), min_value=ini, max_value=fim, disabled=bloqueada)
            st.caption("Consulte os valores salvos na tabela abaixo. Salvar substitui todos os 8 valores da data selecionada.")
            quantidades = {}
            cols = st.columns(4)
            for n, item in enumerate(cfg["metas"]):
                quantidades[item] = cols[n % 4].number_input(item, min_value=0.0, value=None, key=f"fab_qtd_{ano}_{mes}_{n}", disabled=bloqueada)
            salvar = st.form_submit_button("Salvar estoque do dia", disabled=bloqueada)
        if salvar:
            if any(v is None for v in quantidades.values()):
                st.error("Preencha os 8 itens; informe zero quando não houver estoque.")
            else:
                verificar_aberta()
                sb("POST", "rh_fabricacao_estoque", "on_conflict=data", {
                    "data": dia.isoformat(), "quantidades": quantidades,
                    "atualizado_por": str(usr), "atualizado_em": datetime.now().isoformat()},
                    "resolution=merge-duplicates,return=minimal")
                st.rerun()
        if regs:
            st.dataframe(pd.DataFrame([{"DATA": r["data"], **r["quantidades"]} for r in regs]), hide_index=True, use_container_width=True)
        st.caption(f"{len(regs)} dia(s) registrado(s). A média usa apenas os dias lançados; confira se todos os dias de acompanhamento foram incluídos antes de concluir.")
        st.dataframe(pd.DataFrame([{"ITEM": item, "META": meta, "MÉDIA MENSAL": medias[item]} for item, meta in cfg["metas"].items()]), hide_index=True, use_container_width=True)
        opcoes = {int(c["id"]): c for c in colabs if str(c.get("frente") or "").upper().strip() == "FABRICAÇÃO"}
        if opcoes:
            cid = st.selectbox("Colaborador da Fabricação", list(opcoes), format_func=lambda x: f"{opcoes[x]['colaborador']} (ID {x})", key=f"fab_colab_{ano}_{mes}")
            anterior = por_id.get(cid, {})
            with st.form(f"fab_ap_{ano}_{mes}_{cid}_{assinatura[:12]}"):
                horas = st.number_input("Horas extras sem solicitação no mês (h)", min_value=0.0, value=float(anterior["horas_sem_solicitacao"]) if anterior.get("horas_sem_solicitacao") is not None else None, step=0.5, disabled=bloqueada)
                conferido = st.checkbox("Conferi os registros de estoque do mês e as horas extras deste colaborador", value=anterior.get("estoque_assinatura") == assinatura, disabled=bloqueada)
                salvar_ap = st.form_submit_button("Salvar conferência da Fabricação", disabled=bloqueada)
            if salvar_ap:
                if horas is None or not conferido or any(v is None for v in medias.values()):
                    st.error("Informe as horas (inclusive zero), preencha o estoque e marque a conferência.")
                else:
                    verificar_aberta()
                    atuais = sb("GET", "rh_fabricacao_estoque", f"select=*&data=gte.{ini}&data=lte.{fim}&order=data.asc") or []
                    if resumo_estoque(atuais, cfg["metas"])[1] != assinatura:
                        raise ValueError("O estoque mudou em outra sessão. Recarregue e confira novamente.")
                    sb("POST", "rh_fabricacao_apuracao", "on_conflict=colaborador_id,ano,mes", {
                        "colaborador_id": cid, "ano": ano, "mes": mes, "horas_sem_solicitacao": horas,
                        "estoque_assinatura": assinatura, "atualizado_por": str(usr),
                        "atualizado_em": datetime.now().isoformat()}, "resolution=merge-duplicates,return=minimal")
                    st.rerun()
    return medias, assinatura, por_id
