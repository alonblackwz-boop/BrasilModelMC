# BrasilModelMC

Marketplace de modelos 3D para Minecraft, desenvolvido com Flask, SQLAlchemy, Jinja2 e JavaScript. Interface dark neon azul/roxo.

## Funcionalidades implementadas
- Cadastro, login e sessão de usuários.
- Catálogo com pesquisa, filtros e páginas de modelos.
- Painel administrativo para criar modelos como rascunho, enviar arquivos privados ZIP/BBMODEL, editar status e criar categorias por API.
- Biblioteca autenticada e download de modelos gratuitos ou comprados.
- Pedidos com preço calculado no servidor; confirmação Pix via consulta autenticada ao PagHiper.
- Avaliações de compradores verificados, sugestões e estrutura de cupons.
- Proteção CSRF, controle de acesso e testes automatizados no GitHub Actions.

## Execução local
Requer Python 3.12+.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

No Windows, ative com `.venv\\Scripts\\activate`. Copie `.env.example` para `.env` e configure uma `SECRET_KEY` longa e aleatória. Para testes locais HTTP, use `SESSION_COOKIE_SECURE=false`; em produção HTTPS, use `true`.

```bash
flask --app 'app:create_app' run
python -m unittest discover -s tests -v
```

O banco SQLite é criado automaticamente na primeira execução. O diretório de modelos deve ser privado e persistente, fora de `static`.

## Administração
O painel fica em `/admin` e exige usuário com papel `admin`. Não existe conta administrativa padrão nem senha fixa. Configure a primeira conta administrativa somente por procedimento seguro no ambiente privado, nunca por endpoint público.

## Produção e pagamentos
A implantação na Shard Cloud não está realizada. Defina `DATABASE_URL`, `PRIVATE_MODELS_DIR`, `SECRET_KEY`, HTTPS e backups antes de publicar. **Pix permanece desativado** (`PAGHIPER_PIX_ENABLED=false`) até validar conta elegível, credenciais, contrato de API, notificações, recuperação de falhas e transações reais com o titular autorizado. Não envie credenciais, banco ou uploads ao GitHub.

Veja `DEPLOY_CHECKLIST.md` e `PLANO_V03.md` para os requisitos de publicação e funcionalidades futuras. O projeto não deve ser anunciado como operação comercial homologada apenas por passar nos testes locais.
