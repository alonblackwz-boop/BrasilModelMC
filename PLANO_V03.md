# BrasilModelMC — Plano de reconstrução v0.3

## Base
- Fonte: backup v0.2 fornecido pelo proprietário.
- Stack: Flask, SQLite, Jinja2, HTML, CSS e JavaScript.
- Preservar esquema e dados existentes por migrações incrementais.
- Nunca versionar bancos, uploads privados, chaves ou arquivos .env.

## Funcionalidades previstas
1. Avaliações com 1–5 estrelas e compra verificada.
2. Sugestões públicas de modelos, com prazo de 15 dias.
3. Cupons percentuais ou fixos, validade e limites de uso.
4. Carteira de créditos, extrato e infraestrutura para recarga Pix futura.
5. Ranking de clientes com controles de privacidade.
6. Banners e anúncios agendados, com segmentação por página e cupons.
7. Temas e personalização visual.
8. Permissões administrativas e downloads protegidos.

## Requisitos para publicação
- Testes de autenticação, CSRF, permissões e downloads.
- Testes de migração usando cópia do banco de dados.
- Nenhuma integração de pagamento real sem credenciais e homologação.
- Publicação na Shard Cloud somente após validação.
- Registrar mudanças no changelog e README.

## Estado
Planejamento registrado. Implementação e testes da v0.3 ainda pendentes.
