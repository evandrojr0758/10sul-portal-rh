-- Histórico de importações do ponto eletrônico. Acesso somente pelo servidor RH.
create table public.rh_ponto_importacoes (
    id uuid primary key default gen_random_uuid(),
    arquivo text not null,
    arquivo_hash text not null check (arquivo_hash ~ '^[0-9a-f]{64}$'),
    unidade text not null check (unidade in ('Aracruz', 'Bahia', 'Três Lagoas')),
    registros integer not null check (registros > 0),
    importado_por text not null,
    criado_em timestamptz not null default clock_timestamp(),
    unique (unidade, arquivo_hash)
);
create table public.rh_ponto_registros (
    id bigint generated always as identity primary key,
    importacao_id uuid not null references public.rh_ponto_importacoes(id),
    chave text not null check (chave ~ '^[0-9a-f]{64}$'),
    data_ponto date not null check (data_ponto between date '1900-01-01' and date '2100-12-31'),
    empresa text not null check (length(empresa)>0),
    cracha text not null default '',
    colaborador text not null check (length(colaborador)>0),
    extras_informadas boolean not null,
    minutos_extra integer not null check (minutos_extra between 0 and 1440),
    minutos_extra_noturna integer not null check (minutos_extra_noturna between 0 and 1440),
    minutos_extra_folga integer not null check (minutos_extra_folga between 0 and 1440),
    minutos_extra_folga_noturna integer not null check (minutos_extra_folga_noturna between 0 and 1440),
    minutos_extra_feriado integer not null check (minutos_extra_feriado between 0 and 1440),
    minutos_total integer,
    aba text not null,
    linha integer not null,
    dados_originais jsonb not null,
    unique (importacao_id, chave),
    check ((extras_informadas and minutos_total is not null and minutos_total = minutos_extra + minutos_extra_noturna + minutos_extra_folga + minutos_extra_folga_noturna + minutos_extra_feriado)
        or (not extras_informadas and minutos_total is null))
);
create index rh_ponto_registros_chave_idx on public.rh_ponto_registros(chave);
create index rh_ponto_registros_data_idx on public.rh_ponto_registros(data_ponto);
alter table public.rh_ponto_importacoes enable row level security;
alter table public.rh_ponto_registros enable row level security;
revoke all on public.rh_ponto_importacoes, public.rh_ponto_registros from anon, authenticated;
grant select, insert on public.rh_ponto_importacoes, public.rh_ponto_registros to service_role;
grant usage, select on sequence public.rh_ponto_registros_id_seq to service_role;

-- Uma exportação sem extras não apaga as horas já informadas por exportação completa.
create view public.rh_ponto_atual with (security_invoker=true) as
select distinct on (r.chave) r.*, i.unidade, i.arquivo, i.criado_em as importado_em
from public.rh_ponto_registros r
join public.rh_ponto_importacoes i on i.id=r.importacao_id
order by r.chave, r.extras_informadas desc, i.criado_em desc, r.id desc;
revoke all on public.rh_ponto_atual from anon, authenticated;
grant select on public.rh_ponto_atual to service_role;

-- Uma transação por arquivo: erro em qualquer registro desfaz toda a importação.
create function public.rh_importar_ponto(p_arquivo text, p_hash text, p_unidade text,
    p_usuario text, p_registros jsonb) returns jsonb
language plpgsql security invoker set search_path=public, pg_temp as $$
declare v_id uuid; v_qtd integer;
begin
    if jsonb_typeof(p_registros) is distinct from 'array' then
        raise exception 'Registros devem ser uma lista.';
    end if;
    v_qtd := jsonb_array_length(p_registros);
    if v_qtd < 1 or v_qtd > 50000 then
        raise exception 'Envie entre 1 e 50000 registros por arquivo.';
    end if;
    insert into public.rh_ponto_importacoes(arquivo, arquivo_hash, unidade, registros, importado_por)
    values(p_arquivo,p_hash,p_unidade,v_qtd,p_usuario)
    on conflict(unidade,arquivo_hash) do nothing returning id into v_id;
    if v_id is null then
        return jsonb_build_object('duplicado',true,'registros',0);
    end if;
    insert into public.rh_ponto_registros(importacao_id,chave,data_ponto,empresa,cracha,colaborador,
        extras_informadas,minutos_extra,minutos_extra_noturna,minutos_extra_folga,
        minutos_extra_folga_noturna,minutos_extra_feriado,minutos_total,aba,linha,dados_originais)
    select v_id,x.chave,x.data_ponto,x.empresa,x.cracha,x.colaborador,
        x.extras_informadas,x.minutos_extra,x.minutos_extra_noturna,x.minutos_extra_folga,
        x.minutos_extra_folga_noturna,x.minutos_extra_feriado,x.minutos_total,x.aba,x.linha,x.dados_originais
    from jsonb_to_recordset(p_registros) as x(chave text,data_ponto date,empresa text,cracha text,
        colaborador text,extras_informadas boolean,minutos_extra integer,minutos_extra_noturna integer,
        minutos_extra_folga integer,minutos_extra_folga_noturna integer,minutos_extra_feriado integer,
        minutos_total integer,aba text,linha integer,dados_originais jsonb);
    return jsonb_build_object('duplicado',false,'registros',v_qtd,'importacao_id',v_id);
end;
$$;
revoke all on function public.rh_importar_ponto(text,text,text,text,jsonb) from public, anon, authenticated;
grant execute on function public.rh_importar_ponto(text,text,text,text,jsonb) to service_role;
notify pgrst, 'reload schema';
