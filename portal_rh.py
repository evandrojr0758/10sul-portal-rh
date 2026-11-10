            if mudou:
                if not novo_nome or (novo_nome != original_nome.get(cid, "") and any(_nome_colaborador(c).strip().upper() == novo_nome and str(c["id"]) != cid for c in (sb("GET", "rh_colaboradores", "select=id,colaborador") or []))):
                    erros.append(str(linha.get("colaborador") or cid) + " (nome vazio ou duplicado)")
                elif novo_status == "INATIVO" and nova_dd is None and not deslig_exige_motivo(novo_status, nova_dd, original_cadastro[cid]):
                    erros.append(str(linha.get("colaborador") or cid))
                else:
                    alteracoes.append((linha, novo_status, nova_dd, novo_salario, nova_frente, nova_destra, nova_equipe))

        if erros:
            st.warning(
                "Informe a data de desligamento para: " + ", ".join(erros)
            )

        revisao_sem_equipe = [str(linha.get("colaborador") or linha.get("id")) for linha, _, _, _, nova_frente, _, nova_equipe in alteracoes if nova_frente == "REVISÃO" and nova_equipe not in ("EQUIPE 1", "EQUIPE 2")]
        if revisao_sem_equipe:
            st.warning("Selecione EQUIPE 1 ou EQUIPE 2 para os colaboradores da frente REVISÃO: " + ", ".join(revisao_sem_equipe))

        def _salvar_alteracoes_colaborador(motivos=None):
            motivos = motivos or {}
            validar_motivos_desligamento(alteracoes, original_cadastro, motivos)
            # Conferência antes de escrever: evita sobrescrever outro desligamento.
            atuais = {str(c["id"]): c for c in (sb("GET", "rh_colaboradores", "select=*") or [])}
            for linha, *_ in alteracoes:
                cid = str(linha["id"])
                anterior = original_cadastro[cid]
                atual = atuais.get(cid)
                if atual is None or any(atual.get(k) != anterior.get(k) for k in ("ativo", "status", "data_admissao", "data_desligamento", "motivo_desligamento", "observacao_desligamento")):
                    raise ValueError("O cadastro mudou em outra sessão. Recarregue e confira antes de salvar.")
            for linha, novo_status, data_desl, novo_salario, nova_frente, nova_destra, nova_equipe in alteracoes:
                payload = {**{campo: venc_data_iso(linha.get(campo)) for campo in CAMPOS_VENC}, "colaborador": str(linha.get("colaborador") or "").strip().upper(), "empresa": {"SERVICE": "10 SUL SERVICE", "PRESTADORA": "10 SUL PRESTADORA"}.get(str(linha.get("empresa") or "").strip().upper(), str(linha.get("empresa") or "").strip().upper()) or None, "funcao": None if pd.isna(linha.get("funcao")) else (str(linha.get("funcao") or "").strip().upper() or None), "salario_base": novo_salario, "frente": nova_frente or None, "destra": nova_destra or None, "equipe_revisao": nova_equipe or None, "tipo_contratacao": (lambda v: v if v in ("CONTRATO", "SPOT") else None)(str(linha.get("tipo_contratacao") or "").strip().upper())}
                payload.update({"ativo": novo_status == "ATIVO", "status": novo_status, "data_desligamento": data_desl.isoformat() if data_desl else None})
                payload["data_admissao"] = venc_data_iso(linha.get("data_admissao"))
                info = motivos.get(str(linha["id"]))
                if info:
                    payload.update(payload_desligamento(info, st.session_state["usuario_logado"]["id"]))
                # Status, data, motivo e observação são gravados juntos.
                sb("PATCH", "rh_colaboradores", "id=eq." + urllib.parse.quote(str(linha["id"])), payload, "return=minimal")
            _salvar_classificacoes_aracruz({
                str(linha["id"]): str(linha["classificacao_fechamento"])
                for linha, *_ in alteracoes
                if str(linha["classificacao_fechamento"]) != original_classificacao.get(str(linha["id"]))
            })
            st.success("Cadastro atualizado com sucesso.")
            st.rerun()

        if alteracoes:
            if st.button("💾 Salvar alterações do colaborador", type="primary", disabled=bool(revisao_sem_equipe)):
                if any(deslig_exige_motivo(a[1], a[2], original_cadastro[str(a[0]["id"])]) for a in alteracoes):
                    abrir_modal_desligamento(alteracoes, original_cadastro, _salvar_alteracoes_colaborador)
                else:
                    try:
                        _salvar_alteracoes_colaborador()
                    except Exception as e:
                        st.error(f"Não foi possível atualizar o cadastro: {e}")
    else:
        st.info("Nenhum colaborador encontrado para o filtro selecionado.")

    # Exclusão definitiva somente para cadastro sem registros relacionados.
    with st.expander("🗑️ Excluir colaborador sem movimentação"):
        st.warning("A exclusão é permanente. Colaboradores com frequência, ocorrências, DNA ou apuração de gratificação não podem ser excluídos.")
        _opcoes_exclusao = {f"{_nome_colaborador(c)} (ID {c['id']})": c for c in todos_cadastro}
        if _opcoes_exclusao:
            _escolha_exclusao = st.selectbox("Colaborador para exclusão", [""] + list(_opcoes_exclusao), key="rh_excluir_escolha")
            _confirmar_exclusao = st.checkbox("Confirmo a exclusão definitiva deste cadastro, caso não exista movimentação.", key="rh_excluir_confirmacao")
            if st.button("🗑️ Excluir cadastro", disabled=not (_escolha_exclusao and _confirmar_exclusao), key="rh_excluir_executar"):
                _registro_exclusao = _opcoes_exclusao[_escolha_exclusao]
                _id_exclusao = int(_registro_exclusao["id"])
                try:
                    _tabelas_movimento = ["rh_frequencia", "rh_colaborador_ocorrencias", "rh_dna_mensal", "rh_gratificacao_apuracao"]
                    _movimentos = []
                    for _tabela in _tabelas_movimento:
                        _encontrados = sb("GET", _tabela, f"select=*&colaborador_id=eq.{_id_exclusao}&limit=1") or []
                        if _encontrados:
                            _movimentos.append(_tabela)
                    if _movimentos:
                        st.error("Exclusão bloqueada: existem registros em " + ", ".join(_movimentos) + ". Desative o colaborador para preservar o histórico.")
                    else:
                        sb("DELETE", "rh_colaboradores", f"id=eq.{_id_exclusao}", prefer="return=minimal")
                        st.success("Colaborador excluído do cadastro.")
                        st.rerun()
                except Exception as _erro_exclusao:
                    st.error(f"Exclusão não realizada. Verifique outros vínculos no banco: {_erro_exclusao}")

with st.expander("⚙️ Cadastro de ocorrências"):
    st.caption("Esses códigos alimentam as opções disponíveis na grade.")
    st.dataframe(pd.DataFrame(ocorrencias), use_container_width=True, hide_index=True)


st.markdown("#### 📝 Observações de LB / COMP")
registros_obs = []
nomes_por_id = {int(c["id"]): _nome_colaborador(c) for c in colaboradores}
for r in freq:
    codigo = ocorrencia_codigo_por_id.get(int(r.get("ocorrencia_id")), "") if r.get("ocorrencia_id") is not None else ""
    observacao = str(r.get("observacao") or "").strip()
    if codigo in ("LB", "COMP") and observacao:
        try:
            data_reg = pd.to_datetime(r.get("data")).strftime("%d/%m/%Y")
        except Exception:
            data_reg = str(r.get("data") or "")
        registros_obs.append({
            "DATA": data_reg,
            "COLABORADOR": nomes_por_id.get(int(r.get("colaborador_id")), str(r.get("colaborador_id") or "")),
            "TIPO": codigo,
            "OBSERVAÇÃO": observacao,
        })

if registros_obs:
    st.dataframe(pd.DataFrame(registros_obs), use_container_width=True, hide_index=True)
else:
    st.caption("Nenhuma observação de LB/COMP registrada neste mês.")

st.caption("Desenvolvido para 10 Sul • Portal RH")
