# Word Chain — backend

Servidor do jogo multiplayer de corrente de palavras (pt-BR): AWS API Gateway WebSocket → uma Lambda Python 3.13 → DynamoDB. O front (React + PixiJS) fica em `../word-chain-client`.

**Plano e fases:** `docs/backend-plan.md` é a fonte da verdade do backend (B1 e B2 concluídas; B3, infraestrutura como código com SAM, em andamento: `docs/b3-infra.md`). O plano do front fica em `../word-chain-client/docs/refactor-plan.md`.

## Comandos

Tudo roda em `lambda/`, com o venv em `lambda/.venv`:

```bash
python -m unittest discover -s tests -p '*_test.py'   # testes (unittest, *_test.py em tests/)
python -m protocol.export_schema                       # regenera protocol/v2.schema.json
python -m protocol.export_schema --check               # falha se o schema estiver desatualizado (CI)
python -u -m local.server --host 0.0.0.0 --port 3001   # servidor local, sem AWS
```

No Windows, o Python do venv é `.venv/Scripts/python`. Nos testes, `POWERTOOLS_TRACE_DISABLED=1` e `POWERTOOLS_LOG_LEVEL=CRITICAL` deixam a saída limpa (o CI usa os dois). O `-u` do servidor local faz os logs (`+`/`-` por conexão) aparecerem na hora.

## Contrato com o front

- O protocolo é o contrato entre os repositórios. A fonte da verdade são os modelos pydantic em `lambda/protocol/models.py`; o JSON Schema `lambda/protocol/v2.schema.json` é exportado deles, e o front copia esse arquivo com `npm run protocol:sync` (o `schema.test.ts` de lá falha se divergir).
- Mudança de protocolo começa aqui: modelos → `export_schema` → testes → commit. Depois o front sincroniza e adapta o zod. Nunca edite o schema à mão nem o código do front por este repositório.
- Os nomes de `ErrorMessage` (`messages/messages_pt.py`) são os códigos de erro do protocolo: o front decide pelo `code`, nunca pelo texto. Não renomeie um código; acrescente.
- Mudança que quebra o protocolo sobe `PROTOCOL_VERSION`; o servidor responde `UNSUPPORTED_VERSION` para versões diferentes.

## Arquitetura (`lambda/`)

- `main.py`: `GameApplication.run(event)` roteia `$connect`, `$disconnect` e `$default`. Valida o envelope (`v`, `requestId` de 1 a 64 caracteres, modelo pydantic), chama o `Game` com até 3 tentativas em `ConcurrentUpdateError` e responde pela management API (`ConnectionGateway`), não pelo retorno da Lambda. `main()` é o handler, com Powertools (logs estruturados e tracing); a aplicação é criada uma vez por container.
- `game.py`: `Game` trata uma mensagem de uma conexão num instante (`now`). Recarrega o estado a cada chamada (por isso pode ser repetido) e aplica os prazos antes de tudo.
- `entities/`: `Session` (status, corrente, `config`, `ends_at`, `turn_deadline`, `version`) e `Player`. Os prazos vencidos são aplicados em `Session.apply_deadlines`, encadeando do prazo expirado, não de `now`. Turno de 15 s (`TURN_MS`).
- `protocol/`: `models.py` (envelope e mensagens), `mapping.py` (entidades → visão do cliente), `export_schema.py`.
- `repository/`: DynamoDB. Tabelas `sessions` (GSI `name-index`) e `players` (GSI `session_id-index`), ambas com TTL em `expires_in`. Na AWS os nomes vêm de `SESSIONS_TABLE`/`PLAYERS_TABLE` (`word-chain-<stage>-…`); sem as variáveis, `sessions`/`players`. Escrita condicional por `version` (`ConditionExpression`) contra jogadas simultâneas; conflito vira `ConcurrentUpdateError`.
- `api_gateway_service.py`: envio e broadcast em paralelo pela management API. O broadcast devolve as conexões que sumiram (`GoneException`) e o `Game` marca esses jogadores como `offline`. Endpoint em `API_GATEWAY_URL`.
- `utils/wordlist.py`: `wordlist.txt` (537 mil linhas) lido uma vez por container, em `frozenset`.
- `local/`: `server.py` (WebSocket local com `websockets`, roda o `GameApplication` real) e `memory.py` (repositórios em memória, também usados pelos testes via `tests/fakes.py`).

## Testar com o front

1. Aqui: `python -u -m local.server --host 0.0.0.0 --port 3001`.
2. No front: `E2E_WS_URL=ws://localhost:3001 npm run e2e`, ou `VITE_WS_URL` no `.env.local` para jogar no navegador.
3. No celular: use o IP da máquina na rede (`ws://<ip>:3001`). O Python precisa estar liberado no firewall do Windows. O estado vive em memória e some quando o servidor reinicia.

## Deploy

Infraestrutura em SAM: `template.yaml` (API WebSocket, Lambda, tabelas) com o parâmetro `Stage`, `samconfig.toml` com `[dev]` e `[prod]` (stacks `word-chain-dev`/`word-chain-prod`, `sa-east-1`). Na raiz:

```bash
sam validate --lint
sam build
sam deploy --config-env dev    # o output WebSocketUrl é o VITE_WS_URL do front
```

`.github/workflows/deploy.yml`: em push para `dev` (→ `dev`) ou `main` (→ `prod`), com mudanças em `lambda/**`, `template.yaml` ou `samconfig.toml`, roda `export_schema --check` e os testes, depois `sam build` e `sam deploy`. Credenciais por OIDC (`infra/github-oidc.yaml`, aplicado uma vez à mão), com os ARNs em variables dos environments do GitHub. Passo a passo e desenho em `docs/b3-infra.md`.

## Convenções

- Código, identificadores, comentários e commits em inglês; mensagens ao jogador em pt-BR (`messages_pt.py`).
- Commits em Conventional Commits (`feat!:` para quebra de protocolo).
- Dependências de runtime em `requirements.txt` (vão para o zip); de teste e do servidor local em `requirements-dev.txt`.
- Testes com `unittest` e fakes em memória; `moto` só onde o DynamoDB importa (`repository_test.py`).
- Antes de usar APIs de pydantic v2, Powertools v3 ou boto3, confira a doc atual (Context7).
