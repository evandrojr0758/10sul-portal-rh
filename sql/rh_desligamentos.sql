-- Campos opcionais; registros anteriores permanecem intactos.
alter table public.rh_colaboradores
 add column if not exists motivo_desligamento text,
 add column if not exists observacao_desligamento text,
 add column if not exists desligamento_registrado_em timestamptz,
 add column if not exists desligamento_registrado_por bigint;
notify pgrst, 'reload schema';
