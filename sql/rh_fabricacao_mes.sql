begin;
create table if not exists public.rh_fabricacao_mes (
 ano integer not null check (ano between 2025 and 2100),
 mes integer not null check (mes between 1 and 12),
 estoque_atendido boolean not null default false,
 atualizado_por text,
 atualizado_em timestamptz not null default now(),
 primary key (ano,mes)
);
alter table public.rh_fabricacao_mes enable row level security;
revoke all on public.rh_fabricacao_mes from anon,authenticated;
grant select,insert,update on public.rh_fabricacao_mes to service_role;
notify pgrst,'reload schema';
commit;
