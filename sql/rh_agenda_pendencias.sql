begin;
create table if not exists public.rh_agenda_pendencias (
 id uuid primary key default gen_random_uuid(),
 situacao text not null check (length(btrim(situacao)) between 1 and 200),
 descricao text not null default '',
 responsavel text not null default '',
 prazo date,
 status text not null default 'PENDENTE' check (status in ('PENDENTE','RESOLVIDO')),
 solucao text not null default '',
 criado_em timestamptz not null default now(),
 criado_por text not null,
 atualizado_em timestamptz not null default now(),
 atualizado_por text not null,
 resolvido_em timestamptz,
 versao integer not null default 1 check (versao > 0),
 constraint rh_agenda_conclusao_check check (
   (status = 'PENDENTE' and resolvido_em is null) or
   (status = 'RESOLVIDO' and resolvido_em is not null)
 )
);
create index if not exists rh_agenda_status_prazo_idx on public.rh_agenda_pendencias(status,prazo);
alter table public.rh_agenda_pendencias enable row level security;
-- Apenas o servidor do Portal RH lê e grava após validar o perfil ADMIN.
revoke all on public.rh_agenda_pendencias from public,anon,authenticated;
grant select,insert,update on public.rh_agenda_pendencias to service_role;
notify pgrst,'reload schema';
commit;
