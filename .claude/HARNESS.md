# HARNESS — mapa de roteamento

Comece aqui em tarefa não-trivial. Regras duras estão no `CLAUDE.md` da raiz.

## Por onde entrar

| o usuário quer… | vá para |
|---|---|
| mudar cor, eixo, controle, layout, interação do painel | agente **`ea-panel-frontend`** + skill **`ea-panel-edit`** |
| número errado, série vazia/deslocada, SQL, contrato do WS | agente **`ea-backend-data`** |
| revisar antes de release / o HA reclamou no log | agente **`ea-integration-reviewer`** |
| garantir o Python local igual ao do HA | **`/ea-env`** (antes de rodar qualquer Python) |
| levar a mudança para o HA rodando | **`/ea-deploy`** (skill `ea-deploy`) — push → HACS → restart |
| provar que está funcionando de verdade | **`/ea-verify`** |
| investigar erro no HA | **`/ea-logs`** |
| conferir número contra o oráculo | **`/ea-parity`** (skill `ea-parity-check`) |
| cortar versão / tag | **`/ea-release`** (skill `ea-release`) |

## Conhecimento (`.claude/context/`)

| arquivo | quando ler |
|---|---|
| **`invariants.md`** | **obrigatório** antes de mexer em `fit.py`, `series.py` ou `panel.js` |
| `architecture.md` | achar o módulo certo, entender o fluxo de uma consulta |
| `ha-apis.md` | usar qualquer API do HA (recorder, painel, WS, estáticos, prefs) |
| `energy-tree.md` | entidades, hierarquia, regra de cor |
| `ha-host.md` | acesso (só MCP), entrega pelo HACS, versões |
| `decisions.md` | "por que isso é assim?" — decisões travadas, o que não reabrir |

## Ordem de trabalho que não dá dor de cabeça

1. Ler a invariante que a tarefa toca.
2. Editar.
3. Checagem estática: `py_compile` / `json.tool` / `node --check`.
4. Mexeu em dado? **`/ea-parity`**.
5. **`/ea-deploy`** — `git push` é o deploy; download pelo HACS e restart só com confirmação do
   usuário.
6. **`/ea-verify`**.

## Fronteira com o repo do HA

`~/wrk/homeassistant/` é **outro projeto**. Vale ir lá para rodar o **oráculo** de paridade
(`analytics/`, porta 8766) e para consultar a config do HA.

O que não vale trazer de lá: o `uv` daquele workspace, e o vocabulário de `states`/`statistics` do
`timescaledb/` — lá esses nomes são um **mirror local reconstruído**; aqui são as tabelas do
**recorder de produção**.

## Ambiente Python — `uv`, na versão do HA

**Todo** Python daqui roda por **`uv run`**; `python3` do sistema é proibido (regra 10 do
`CLAUDE.md`). O `.venv` é travado no mesmo interpretador que o HA executa — hoje **3.14.6**, lido de
`ha_get_system_health().homeassistant.info.python_version`. É esse interpretador que roda a
integração; validar noutro é validar contra alvo que não existe.

Quando o HA subir de versão, **`/ea-env`** compara, apaga o `.venv` e recria na versão nova
(`uv python pin` → `rm -rf .venv` → `uv sync`). `.python-version` e `uv.lock` são versionados; o
`.venv` não.

Sem dependência própria (`requirements: []` no manifest, `dependencies = []` no pyproject) e sem
teste automatizado: a verificação é paridade contra o oráculo + prova de runtime.
