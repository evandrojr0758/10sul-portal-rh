-- Colunas opcionais; preserva cadastros, frequência e gratificação existentes.
alter table public.rh_colaboradores
 add column if not exists venc_aso date,
 add column if not exists venc_integracao_fabrica date,
 add column if not exists venc_integracao_unf date;
notify pgrst, 'reload schema';
