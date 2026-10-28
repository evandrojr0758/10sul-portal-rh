"""Agenda administrativa persistente do Portal RH."""
from datetime import date, datetime
from zoneinfo import ZoneInfo
from uuid import uuid4
import unicodedata


TABELA = "rh_agenda_pendencias"
STATUS = ("PENDENTE", "RESOLVIDO")


def agora_local():
    return datetime.now(ZoneInfo("America/Sao_Paulo"))


def exigir_admin(usuario):
    if not usuario or not usuario.get("id") or str(usuario.get("perfil", "")).upper() != "ADMIN":
        raise PermissionError("A agenda está disponível somente para o perfil Administrador.")


def vencida(registro, hoje):
    return (registro["status"] == "PENDENTE" and bool(registro.get("prazo"))
            and date.fromisoformat(registro["prazo"]) < hoje)


def _normalizar(texto):
    return "".join(c for c in unicodedata.normalize("NFD", str(texto or "").casefold())
                   if not unicodedata.combining(c))


def filtrar(registros, hoje, status="TODOS", busca="", atrasadas=False):
    busca = _normalizar(busca).strip()
    linhas = [r for r in registros if (status == "TODOS" or r["status"] == status)
              and (not atrasadas or vencida(r, hoje))
              and (not busca or busca in _normalizar(" ".join(str(r.get(c) or "") for c in
                   ("situacao", "descricao", "responsavel", "solucao"))))]
    # Pendentes primeiro; os prazos mais próximos aparecem antes dos sem prazo.
    return sorted(linhas, key=lambda r: (r["status"] != "PENDENTE", r.get("prazo") or "9999-12-31",
                                        r.get("criado_em") or "", r["id"]))


def listar(sb, usuario):
    exigir_admin(usuario)
    registros, offset = [], 0
    while True:
        pagina = sb("GET", TABELA, f"select=*&order=criado_em.desc,id.asc&limit=500&offset={offset}") or []
        registros.extend(pagina)
        if len(pagina) < 500:
            return registros
        offset += 500


def preparar(dados, anterior=None, agora=None):
    agora = agora or agora_local()
    situacao = str(dados.get("situacao") or "").strip()
    status = dados.get("status", "PENDENTE")
    if not situacao:
        raise ValueError("Informe a situação que precisa ser resolvida.")
    if len(situacao) > 200:
        raise ValueError("A situação deve ter até 200 caracteres.")
    if status not in STATUS:
        raise ValueError("Status inválido.")
    prazo = dados.get("prazo")
    if prazo:
        prazo = date.fromisoformat(str(prazo)).isoformat()
    resolvida = status == "RESOLVIDO"
    conclusao = ((anterior or {}).get("resolvido_em") or agora.isoformat()) if resolvida else None
    return {"situacao": situacao, "descricao": str(dados.get("descricao") or "").strip(),
            "responsavel": str(dados.get("responsavel") or "").strip(), "prazo": prazo or None,
            "status": status, "solucao": str(dados.get("solucao") or "").strip(),
            "resolvido_em": conclusao, "atualizado_em": agora.isoformat()}


def salvar(sb, usuario, dados, anterior=None, novo_id=None):
    exigir_admin(usuario)
    payload = preparar(dados, anterior)
    payload["atualizado_por"] = str(usuario.get("nome") or usuario.get("usuario") or usuario["id"])
    if anterior:
        versao = int(anterior["versao"])
        payload["versao"] = versao + 1
        rows = sb("PATCH", TABELA, f"id=eq.{anterior['id']}&versao=eq.{versao}",
                  payload, "return=representation")
        if not rows:
            raise ValueError("Outra pessoa alterou esta situação. Atualize a agenda e confira antes de salvar novamente.")
    else:
        payload.update(id=novo_id or str(uuid4()), criado_por=payload["atualizado_por"],
                       criado_em=payload["atualizado_em"])
        # O mesmo formulário mantém o ID ao tentar novamente após uma falha de rede.
        rows = sb("POST", TABELA, "on_conflict=id", payload,
                  "resolution=ignore-duplicates,return=representation")
    return rows


def tela(sb):
    import pandas as pd
    import streamlit as st

    usuario = st.session_state.get("usuario_logado") or {}
    try:
        exigir_admin(usuario)
    except PermissionError as exc:
        st.error(str(exc))
        return
    st.subheader("🗓️ Agenda de Pendências")
    st.caption("Registre situações, acompanhe os prazos e mantenha o histórico das soluções.")
    if st.session_state.get("agenda_sucesso"):
        st.success(st.session_state.pop("agenda_sucesso"))
    if st.button("Atualizar agenda", key="agenda_atualizar"):
        st.rerun()
    try:
        registros = listar(sb, usuario)
    except Exception:
        st.error("Não foi possível carregar a agenda. Tente atualizar novamente.")
        return

    hoje = agora_local().date()
    cols = st.columns(3)
    cols[0].metric("Pendentes", sum(r["status"] == "PENDENTE" for r in registros))
    cols[1].metric("Atrasadas", sum(vencida(r, hoje) for r in registros))
    cols[2].metric("Resolvidas", sum(r["status"] == "RESOLVIDO" for r in registros))

    novo_id = st.session_state.setdefault("agenda_novo_id", str(uuid4()))
    with st.expander("➕ Nova situação", expanded=not registros):
        with st.form("agenda_nova_" + novo_id):
            situacao = st.text_input("Situação *", max_chars=200)
            descricao = st.text_area("Detalhes da situação")
            a, b = st.columns(2)
            responsavel = a.text_input("Responsável")
            prazo = b.date_input("Prazo", value=None, format="DD/MM/YYYY")
            enviar = st.form_submit_button("Registrar pendência", type="primary")
        if enviar:
            try:
                salvar(sb, usuario, dict(situacao=situacao, descricao=descricao,
                       responsavel=responsavel, prazo=prazo), novo_id=novo_id)
            except ValueError as exc:
                st.error(str(exc))
            except Exception:
                st.error("Não foi possível confirmar o registro. Tente novamente; o formulário evita duplicações.")
            else:
                st.session_state.pop("agenda_novo_id", None)
                st.session_state["agenda_sucesso"] = "Pendência registrada."
                st.rerun()

    a, b = st.columns([1, 2])
    status = a.selectbox("Status", ("TODOS",) + STATUS,
                         format_func=lambda v: {"TODOS": "Todos", "PENDENTE": "Pendente", "RESOLVIDO": "Resolvido"}[v])
    busca = b.text_input("Buscar situação ou responsável", key="agenda_busca")
    atrasadas = st.checkbox("Somente pendências atrasadas", key="agenda_atrasadas")
    linhas = filtrar(registros, hoje, status, busca, atrasadas)
    if not linhas:
        st.info("Nenhuma situação encontrada para os filtros selecionados.")
        return

    def data_br(valor):
        if not valor:
            return "—"
        texto = str(valor)
        if "T" in texto:
            return datetime.fromisoformat(texto.replace("Z", "+00:00")).astimezone(ZoneInfo("America/Sao_Paulo")).strftime("%d/%m/%Y")
        return date.fromisoformat(texto).strftime("%d/%m/%Y")

    st.dataframe(pd.DataFrame([{
        "Situação": r["situacao"], "Responsável": r.get("responsavel") or "—",
        "Prazo": data_br(r.get("prazo")),
        "Status": "🔴 Pendente — atrasada" if vencida(r, hoje) else ("🟠 Pendente" if r["status"] == "PENDENTE" else "✅ Resolvido"),
        "Registrada em": data_br(r.get("criado_em")), "Concluída em": data_br(r.get("resolvido_em")),
    } for r in linhas]), hide_index=True, use_container_width=True)

    por_id = {r["id"]: r for r in linhas}
    registro_id = st.selectbox("Abrir / editar situação", list(por_id),
        format_func=lambda k: f"{'🔴 ' if vencida(por_id[k], hoje) else ''}{por_id[k]['situacao']} • {por_id[k].get('responsavel') or 'Sem responsável'} • {k[:8]}",
        key="agenda_selecionada")
    r = por_id[registro_id]
    st.caption(f"Registrada por {r['criado_por']} em {data_br(r['criado_em'])}. Última alteração por {r['atualizado_por']}.")
    with st.form(f"agenda_editar_{r['id']}_{r['versao']}"):
        situacao = st.text_input("Situação *", value=r["situacao"], max_chars=200)
        descricao = st.text_area("Detalhes da situação", value=r.get("descricao") or "")
        a, b, c = st.columns(3)
        responsavel = a.text_input("Responsável", value=r.get("responsavel") or "")
        prazo = b.date_input("Prazo", value=date.fromisoformat(r["prazo"]) if r.get("prazo") else None, format="DD/MM/YYYY")
        novo_status = c.selectbox("Status da situação", STATUS, index=STATUS.index(r["status"]), format_func=str.capitalize)
        solucao = st.text_area("Observação / solução", value=r.get("solucao") or "")
        st.caption("Ao marcar Resolvido, a data de conclusão é registrada automaticamente. É possível reabrir como Pendente.")
        gravar = st.form_submit_button("Salvar alterações", type="primary")
    if gravar:
        try:
            salvar(sb, usuario, dict(situacao=situacao, descricao=descricao,
                   responsavel=responsavel, prazo=prazo, status=novo_status, solucao=solucao), anterior=r)
        except (ValueError, PermissionError) as exc:
            st.error(str(exc))
        except Exception:
            st.error("Não foi possível confirmar a alteração. Atualize a agenda para conferir antes de tentar novamente.")
        else:
            st.session_state["agenda_sucesso"] = "Situação atualizada."
            st.rerun()
