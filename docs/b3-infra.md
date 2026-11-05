# B3 — Infraestrutura como código (SAM)

Decidido em 2026-11-05: **AWS SAM**, região `sa-east-1`, um template para dois ambientes.

## Desenho

- `template.yaml` (raiz) com o parâmetro `Stage` (`dev` | `prod`) → stacks `word-chain-dev` e `word-chain-prod`. `samconfig.toml` tem uma seção por ambiente.
- Recursos por stack:
  - Tabelas `word-chain-<stage>-sessions` (GSI `name-index`) e `word-chain-<stage>-players` (GSI `session_id-index`), on-demand, TTL em `expires_in`. Sem `Retain`: o estado vive no máximo 1 h.
  - API Gateway WebSocket `word-chain-<stage>` com `$connect`, `$disconnect` e `$default` → integração proxy na Lambda. Stage `<stage>` com throttling padrão (50 msg/s, burst 100) como proteção de custo.
  - Lambda `word-chain-<stage>` (`main.main`, python3.13, x86_64, 512 MB, 10 s, X-Ray ativo), log group com 14 dias. Permissões: CRUD nas duas tabelas e `execute-api:ManageConnections` só na própria API.
  - Variáveis injetadas: `SESSIONS_TABLE`, `PLAYERS_TABLE`, `API_GATEWAY_URL`. Sem elas, o código cai em `sessions`/`players` (testes e servidor local).
  - Output `WebSocketUrl`: o `wss://` do front (`VITE_WS_URL`).
- O `AWS::ApiGatewayV2::Deployment` é um retrato das rotas: se rotas ou integração mudarem, renomeie o recurso para forçar um deploy novo da API.
- CI (`.github/workflows/deploy.yml`): push na `dev` → `dev`, push na `main` → `prod`. Testes → `sam validate --lint` → `sam build` → `sam deploy --config-env <stage>`.
- Acesso do CI por OIDC (`infra/github-oidc.yaml`, aplicado uma vez à mão):
  - **Deploy role** (`word-chain-github-deploy`): só pode ser assumido por jobs dos environments `dev`/`prod` deste repositório. Mexe apenas nas stacks `word-chain-dev`/`word-chain-prod`, no bucket de artefatos do SAM e repassa o role de execução ao CloudFormation.
  - **Execution role** (`word-chain-cfn-execution`): usado pelo CloudFormation para criar os recursos. Limitado a nomes `word-chain-*`.
- A infraestrutura manual antiga (API `h9qktxoj4a`, tabelas `sessions`/`players`, Lambda antiga) não é importada: a stack nova sobe em paralelo e a antiga é apagada depois da troca da URL no front.

## Primeiro deploy (do seu terminal)

Pré-requisitos: [SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html) (`winget install Amazon.SAM-CLI`), Python 3.13 no PATH e credenciais (`aws login`). Tudo na raiz do repositório.

1. `sam validate --lint` e `sam build`
2. `sam deploy --config-env dev` → revise o changeset e confirme. Anote o `WebSocketUrl`.
3. Smoke test no front: `E2E_WS_URL=<WebSocketUrl> npm run e2e`.

## CI por OIDC (uma vez por conta)

1. Veja se a conta já tem o provedor do GitHub:
   `aws iam list-open-id-connect-providers`
2. Aplique o bootstrap (acrescente `--parameter-overrides ExistingOidcProviderArn=<arn>` se o provedor já existir):
   `aws cloudformation deploy --template-file infra/github-oidc.yaml --stack-name word-chain-github-oidc --capabilities CAPABILITY_NAMED_IAM --region sa-east-1`
3. Pegue os ARNs:
   `aws cloudformation describe-stacks --stack-name word-chain-github-oidc --region sa-east-1 --query "Stacks[0].Outputs"`
4. No GitHub (Settings → Environments), em `dev` e em `prod`, crie as *variables* `AWS_DEPLOY_ROLE_ARN`, `AWS_CFN_EXEC_ROLE_ARN` e `AWS_REGION=sa-east-1`. Em `prod`, considere exigir aprovação (required reviewers).
5. Apague os secrets antigos `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` e `AWS_LAMBDA_FUNCTION_NAME`, e desative a access key do usuário IAM que o CI usava.

O CI usa o bucket que o `--resolve-s3` cria (stack `aws-sam-cli-managed-default`), então o primeiro deploy precisa ter sido feito do terminal.

## Troca e limpeza

1. Repita o primeiro deploy com `--config-env prod` (ou faça merge na `main`).
2. No front, troque `VITE_WS_URL` no `.env` pela URL de `prod` (ou `dev`) e rode o e2e.
3. Apague a infraestrutura manual antiga: API `h9qktxoj4a`, a Lambda antiga e as tabelas `sessions`/`players` em `sa-east-1`.
