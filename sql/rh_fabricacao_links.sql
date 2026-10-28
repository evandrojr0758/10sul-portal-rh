begin;
create table if not exists public.rh_fabricacao_links (
 id bigint generated always as identity primary key,
 token text not null unique check (token ~ '^[a-f0-9]{64}$'),
 ativo boolean not null default true,
 criado_em timestamptz not null default now()
);
alter table public.rh_fabricacao_links enable row level security;
revoke all on public.rh_fabricacao_links from anon,authenticated;
grant select,insert,update on public.rh_fabricacao_links to service_role;
grant usage,select on sequence public.rh_fabricacao_links_id_seq to service_role;
notify pgrst,'reload schema';
commit;
