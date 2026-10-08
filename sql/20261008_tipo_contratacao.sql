-- Executar uma vez no SQL Editor do Supabase antes de usar o campo no Portal RH.
ALTER TABLE public.rh_colaboradores
ADD COLUMN IF NOT EXISTS tipo_contratacao TEXT;

ALTER TABLE public.rh_colaboradores
DROP CONSTRAINT IF EXISTS rh_colaboradores_tipo_contratacao_check;

ALTER TABLE public.rh_colaboradores
ADD CONSTRAINT rh_colaboradores_tipo_contratacao_check
CHECK (tipo_contratacao IS NULL OR tipo_contratacao IN ('CONTRATO', 'SPOT'));

-- Cadastros anteriores permanecem sem classificação até atualização manual.
