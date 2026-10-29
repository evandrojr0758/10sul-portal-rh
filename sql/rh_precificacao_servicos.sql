begin;
create table if not exists public.rh_precificacao_servicos (
 id uuid primary key default gen_random_uuid(),
 servico text not null check (length(btrim(servico)) between 1 and 200),
 categoria text not null default '',
 horas numeric(12,4) not null default 0 check (horas between 0 and 100000),
 profissionais integer not null default 1 check (profissionais between 1 and 100),
 custo_hora numeric(14,2) not null default 0 check (custo_hora between 0 and 999999999999.99),
 materiais numeric(14,2) not null default 0 check (materiais between 0 and 999999999999.99),
 outros numeric(14,2) not null default 0 check (outros between 0 and 999999999999.99),
 despesas_pct numeric(7,4) not null default 0 check (despesas_pct between 0 and 99.9999),
 margem_pct numeric(7,4) not null default 0 check (margem_pct between 0 and 99.9999),
 preco_manual numeric(14,2) check (preco_manual between 0 and 999999999999.99),
 ativo boolean not null default true,
 observacoes text not null default '',
 criado_em timestamptz not null default now(),
 criado_por text not null,
 atualizado_em timestamptz not null default now(),
 atualizado_por text not null,
 versao integer not null default 1 check (versao > 0),
 constraint rh_precificacao_percentuais_check check (despesas_pct + margem_pct < 100)
);
alter table public.rh_precificacao_servicos enable row level security;
-- Acesso pelo servidor Streamlit, após validação do perfil ADMIN.
revoke all on public.rh_precificacao_servicos from public,anon,authenticated;
grant select,insert,update on public.rh_precificacao_servicos to service_role;
notify pgrst,'reload schema';
commit;
