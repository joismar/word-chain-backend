# Plano do backend — Word Chain

> Movido de `../word-chain-client/docs/refactor-plan.md` (seção 5) em 2026-10-31, quando o backend ganhou o próprio `CLAUDE.md`. O redesenho começou junto com a refatoração do front (2026-10-20); o plano do front continua lá.

---

## 0. Diagnóstico (2026-10-20)

Bugs do backend encontrados na leitura do código, todos resolvidos em B1 e B2:

1. **Host não conseguia iniciar a partida**: o front enviava `start` com `['3','true']` e `Game.start(self, mode)` aceitava 1 argumento → `TypeError` → HTTP 500.
2. **O `GameData` não levava a `config`**, e o front não tinha como calcular o fim da partida.
3. **O jogo podia travar**: o fim da partida dependia do host enviar `END` e a troca de turno, do jogador da vez enviar `PASS`. Fechou a aba → travou.
4. **`wordlist.txt` (537 mil linhas) lido a cada requisição** e validado com `word in list` (O(n)).
5. **Sem controle de concorrência no DynamoDB**: duas jogadas simultâneas → last-write-wins.
6. **CI com Python 3.9** (EOL em out/2025); infraestrutura (API Gateway, tabelas, GSIs) fora do código.

---

## 1. Fases

### B1 — Hotfix (antes de F1 do front, destravou os testes ponta a ponta)
- [x] `start(time, repetition)` aceitando a config real; persistir `config` na sessão e enviá-la no `GameData`
- [x] Wordlist carregada **uma vez por container** (escopo de módulo) num `set`/`frozenset`
- [x] Python 3.13 no CI e no runtime da Lambda

### B2 — Protocolo v2 e servidor autoritativo
- [x] Envelope versionado: `{ v: 2, type, payload, requestId }`; erros com `code` estável (`INEXISTENT_SESSION`, `INVALID_TURN`…) além da mensagem pt-BR
- [x] Schema único do protocolo (JSON Schema) → pydantic v2 no back, zod no front
- [x] **Prazos no servidor:** a sessão guarda `turn_deadline` e `ends_at`. Toda mensagem recebida valida os prazos primeiro (troca o turno ou encerra a partida se venceram). O cliente pode mandar `timeout` quando o prazo vence localmente, e o servidor só aceita se o prazo dele também já passou. Isso resolve os travamentos sem precisar de infraestrutura nova
  - Opcional, numa fase futura: Step Functions (Wait state) para encerrar partidas mesmo sem nenhum cliente conectado
- [x] Escritas condicionais no DynamoDB (`version` + `ConditionExpression`) contra jogadas simultâneas
- [x] Broadcast em paralelo e limpeza de conexões `GoneException`
- [x] AWS Lambda Powertools (logs estruturados, tracing) no lugar de `print(json.dumps(event))`
- [x] Servidor WebSocket local (`local/server.py`) para testar o front ponta a ponta sem deploy

### B3 — Infraestrutura como código

Desenho e passo a passo: `docs/b3-infra.md`.

- [x] Versionar API Gateway WebSocket, Lambda, tabelas `sessions`/`players` + GSIs `name-index` e `session_id-index` e TTL em `expires_in` (**SAM**, decidido em 2026-11-05: `template.yaml`)
- [x] Ambientes `dev`/`prod` (`samconfig.toml`); deploy via OIDC do GitHub (`infra/github-oidc.yaml`)
- [ ] Primeiro deploy de `dev` e `prod`, bootstrap do OIDC, variables nos environments do GitHub
- [ ] Front apontando para a URL nova; infraestrutura manual antiga apagada; access keys antigas removidas

---

## 2. Decisões pendentes

1. ~~IaC: SAM ou CDK.~~ SAM (2026-11-05).
2. O backend continua em Python ou migra para TypeScript (Node 22) para compartilhar tipos diretamente com o front. A recomendação atual é **Python + JSON Schema**, por ser a menor ruptura.
