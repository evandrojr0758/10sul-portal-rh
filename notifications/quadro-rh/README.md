# Quadro RH no celular

Preparado para envio diário às 09h, 13h e 16h em America/Sao_Paulo. O verificador existente executa a cada minuto; chave por data/horário/aparelho impede duplicidade, com tentativas dentro da janela da hora.

Usa apenas aparelhos vinculados a usuários ativos RH/ADMIN. Não inclui nomes no resumo push. Mantém autorização de ativação de uso único, com expiração de 15 minutos e controle do aparelho existente.

Se hoje não tiver frequência preenchida, utiliza a última data anterior com lançamento dos colaboradores com vínculo atual. O payload informa a referência e pendências; se não existir data, informa indisponibilidade das situações. Não mistura dias entre colaboradores. Classificação segue overrides privados do portal e o mesmo cadastro de referência.

Fonte inicial: função alertas-10sul, versão 18, projeto rpkbosftqdtbubrqrtjq. A publicação proposta substitui esta função, preserva seus outros alertas e o verificador existente. Revalidar a versão atual antes de publicar se outra alteração ocorrer. verify_jwt continua false porque os endpoints têm autenticação própria.

Arquivos de deploy: index.ts, rules.mjs, deno.json, rh-summary.mjs, classification.mjs. Caminho de entrada index.ts; import map deno.json.

Validação: node notifications/quadro-rh/test.mjs; python -m unittest discover -s tests -p 'test_rh_quadro*.py'; python -m py_compile portal_rh.py. Não houve publicação: revisão automática exigiu autorização específica para substituir a função em produção. Nenhum aparelho está inscrito no RH na consulta de 17/11/2026.
