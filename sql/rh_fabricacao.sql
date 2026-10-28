-- Fabricação: apenas o backend do Portal RH (service_role) acessa os lançamentos.
begin;
alter table public.rh_regras_gratificacao add column if not exists fabricacao_config jsonb;
insert into public.rh_regras_gratificacao
    (codigo,nome,percentual_salario,dna_minimo,desconto_1_atestado_percentual,
     falta_zera_tudo,dna_abaixo_minimo_zera,desvio_comportamental_zera,fabricacao_config)
values ('FABRICACAO','FABRICAÇÃO',35,2,25,true,true,false,
 '{"desconto_2_atestados_percentual":50,"desconto_item_percentual":5,"limite_he_sem_solicitacao":5,"metas":{"Chapa de Dimensão":3,"Chapa RMT":4,"Régua 0,75 m":15,"Régua 1 m":15,"Régua 1,5 m":15,"Régua 3 m":16,"Chapa de Assoalho":13,"Mão Francesa":16}}'::jsonb)
on conflict(codigo) do nothing;

create table if not exists public.rh_fabricacao_estoque (
 data date primary key,
 quantidades jsonb not null check (jsonb_typeof(quantidades)='object'),
 atualizado_por text,
 atualizado_em timestamptz not null default now()
);
create table if not exists public.rh_fabricacao_apuracao (
 colaborador_id bigint not null references public.rh_colaboradores(id),
 ano integer not null check (ano between 2025 and 2100),
 mes integer not null check (mes between 1 and 12),
 horas_sem_solicitacao numeric not null check (horas_sem_solicitacao >= 0),
 estoque_assinatura text not null,
 atualizado_por text,
 atualizado_em timestamptz not null default now(),
 primary key (colaborador_id,ano,mes)
);
alter table public.rh_fabricacao_estoque enable row level security;
alter table public.rh_fabricacao_apuracao enable row level security;
revoke all on public.rh_fabricacao_estoque,public.rh_fabricacao_apuracao from anon,authenticated;
grant select,insert,update on public.rh_fabricacao_estoque,public.rh_fabricacao_apuracao to service_role;
notify pgrst,'reload schema';
commit;
