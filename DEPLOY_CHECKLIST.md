# Implantação segura — BrasilModelMC

A implantação na Shard Cloud está **pendente**. Não habilite pagamentos reais até que testes de integração e webhook sejam concluídos.

## Variáveis de ambiente

- `SECRET_KEY`: chave secreta aleatória longa (obrigatória).
- `DATABASE_URL`: conexão persistente com o banco de dados.
- `PRIVATE_MODELS_DIR`: diretório privado, fora da pasta pública, com os arquivos dos modelos.
- `PAGHIPER_API_KEY`: credencial privada do PagHiper.
- `PAGHIPER_TOKEN`: token privado do PagHiper.
- `PAGHIPER_NOTIFICATION_URL`: endereço público HTTPS do endpoint `/webhooks/paghiper/pix`.
- `PAGHIPER_PIX_ENABLED`: manter ausente ou `false` até aprovação dos testes. Definir `true` somente após validação da conta e da integração.

Nunca colocar credenciais no GitHub, no JavaScript do navegador, em screenshots ou em arquivos enviados a terceiros.

## Pendências antes de ativar pagamentos

1. Confirmar habilitação do Pix no painel PagHiper e elegibilidade da conta.
2. Validar com documentação oficial os campos exatos de criação e resposta, notificações e status.
3. Validar idempotência e recuperação de falhas após criação remota de cobrança.
4. Verificar autenticação do webhook, valor, referência, estado e correspondência de transação.
5. Testar pagamento real de valor baixo sob supervisão do titular autorizado, incluindo rejeições, duplicações e reenvios.
6. Confirmar que os downloads ficam bloqueados até a confirmação.
7. Configurar HTTPS, banco persistente, backups e política de privacidade apropriada.

O endpoint de criação de pedido e a página de checkout existem, mas **não** garantem que uma cobrança Pix será aceita pelo PagHiper.
