# CLAUDE.md — Energy Analytics

Guia para o Claude Code neste repositório. **Projeto autônomo** — não depende do repo de config do
Home Assistant (`~/wrk/homeassistant`).

## O que é

Integração custom do Home Assistant que registra um **painel na sidebar** sobrepondo **perfis
diários de 24 h** das entidades do painel de Energia (5 fontes + 28 devices), lendo `states` e
`statistics*` pela **sessão do recorder** — **somente `SELECT`**.

Serve para comparar o **formato** do dia (quando a casa consome), não o total do mês. Totais por
dia/mês/ano são do painel de Energia oficial do HA.

A curva desenhada é **regressão polinomial por trecho** (OLS, grau por AICc), não interpolação.

## ⚠️ Regras duras

1. **SOMENTE LEITURA sobre produção.** Nenhum `INSERT`/`UPDATE`/`DELETE`, nunca.
   `session_scope(read_only=True)` **não** é barreira — a garantia é o código só emitir SELECT.
2. **Antes de mexer em `fit.py`, `series.py` ou `www/panel.js`, leia
   `.claude/context/invariants.md`.** Cada invariante é um bug real já pago. Um `setOption` sem
   `min`/`max` explícito ou um `build()` dentro do `datesChanged` regride o painel sem erro nenhum.
3. **`fit.py` e `palette.py` são idênticos, byte a byte, à implementação de referência** usada em
   `ea-parity-check`. Editar qualquer um dos dois quebra a paridade e a regra de cor do HA.
4. **Executores separados:** SQL no executor do **recorder**, regressão no executor **geral**.
   Juntar os dois segura a gravação de estados do HA.
5. **Nada de I/O bloqueante no event loop** — sem `open()`/`json.load()`/`connect()` em import ou
   em `async_setup_entry`. HA 2026.x levanta erro, não warning.
6. **A entrega é HACS, e HACS baixa do GitHub — não do seu disco.** Mudança só chega no HA depois
   de `git push` para `github.com/mmastria/ha-energy-analytics`. Commit não empurrado é mudança que
   não existe para o HA. Ver `.claude/context/ha-host.md` e a skill `ea-deploy`.
7. **Não há acesso ao servidor.** Tudo que toca o HA passa pelo MCP `ha-mcp` ou pelo navegador —
   não há shell, arquivo do host nem banco alcançável daqui.
8. **Git aqui é normal** (o bloqueio de git é hook do outro repo, não deste).
9. **SQL é Postgres-only** (`DISTINCT ON`, operador de regex `~`). O recorder de produção é
   TimescaleDB/Postgres e isso é decisão aceita — não "portar para SQLite".
9b. **Não distribuir.** Nada de PR em `home-assistant/brands` nem em `hacs/default`. O repo é
   público só porque o HACS exige para baixar; o ícone cinza "icon not available" no HACS é
   **esperado** e não é bug a corrigir. Ver *Não-distribuição* em `.claude/context/decisions.md`.
10. **Python local = `uv`, na versão do HA. SEMPRE.** Nada de `python3` do sistema: todo código
    Python que rodar aqui — validação, exercício do `fit.py`, script solto — vai por
    **`uv run`**. O interpretador do `.venv` tem que ser o **mesmo que o HA executa**
    (`python_version` do system health; hoje **3.14.6**), porque é ele que roda a integração —
    validar noutro é validar contra alvo que não existe. Antes de mexer, confira com **`/ea-env`**;
    quando o HA mudar de versão, o `/ea-env` apaga o `.venv` e o recria na versão nova.

## Comandos

Não há build, lint nem teste automatizado. A verificação é **checagem estática + paridade contra o
oráculo + prova de runtime**.

```bash
# checagem estática — a única porta antes do push
uv run python -m py_compile custom_components/energy_analytics/*.py
uv run python -m json.tool custom_components/energy_analytics/manifest.json >/dev/null
uv run python -m json.tool hacs.json >/dev/null
node --check custom_components/energy_analytics/www/panel.js
```

CI (`.github/workflows/validate.yml`): só `hacs/action` + `hassfest`. Nenhum roda Python daqui.

| slash | faz |
|---|---|
| `/ea-env` | confere o Python do `.venv` contra o do HA; recria se divergir |
| `/ea-deploy` | push + `ha_manage_hacs(download)` + restart (com confirmação) |
| `/ea-verify [quick\|full]` | prova de runtime: carregou, painel na sidebar, os 2 comandos WS respondem |
| `/ea-logs [n]` | logs do HA filtrados pela integração (`ha_get_logs`) |
| `/ea-parity [entidade] [de] [ate]` | compara o WS `series` com o Flask (porta 8766) |
| `/ea-release` | bump do `version` no `manifest.json` + commit + tag + push |

## Fluxo de uma consulta

```
panel.js  hass.callWS("energy_analytics/series", {entities, from, to, source, mode, degree})
  → websocket.ws_series      valida vol.Schema, aplica teto max_days
  → energy_tree.async_get_tree   prefs AO VIVO do manager de Energia (sem arquivo)
  → series.fetch
       ├─ recorder_db.query(...)               executor DO RECORDER — só SELECT
       └─ hass.async_add_executor_job(_assemble)  executor GERAL — fit.fit() por série e por média
```

Detalhe (SQL por fonte, contexto de 3 h, bucketização): `.claude/context/architecture.md`.

## Estrutura

```
custom_components/energy_analytics/    a integração (13 arquivos + www/)
  www/panel.js                         a UI inteira (custom element + Shadow DOM)
  www/echarts.esm.min.js               ECharts 5.6.1 ESM vendorizado (~1 MB, sem CDN)
hacs.json  README.md  .github/workflows/validate.yml
.claude/
  context/     conhecimento estável (arquitetura, invariantes, APIs do HA, árvore, host, decisões)
  agents/      3 agentes (front do painel, dados/backend, revisor de integração HA)
  skills/      4 skills (deploy, paridade, edição do painel, release)
  commands/    /ea-deploy /ea-verify /ea-logs /ea-parity /ea-release
  output/      saídas regeneráveis (gitignored)
```

Roteamento completo: **`.claude/HARNESS.md`**. Comece por lá em tarefa não-trivial.

## Contexto — leia conforme a tarefa

| tarefa | leia |
|---|---|
| qualquer coisa não-trivial | `.claude/HARNESS.md` |
| mudar cálculo, SQL ou UI | `.claude/context/invariants.md` **(obrigatório)** |
| entender o fluxo / achar módulo | `.claude/context/architecture.md` |
| usar API do HA | `.claude/context/ha-apis.md` |
| entidades, cores, hierarquia | `.claude/context/energy-tree.md` |
| acesso, entrega, versões, HACS | `.claude/context/ha-host.md` |
| "por que isso é assim?" | `.claude/context/decisions.md` |

## Estado (conferido 2026-08-02 pelo `ha-mcp`)

Instalada **pelo HACS** como repositório custom `mmastria/ha-energy-analytics`, HACS id
`1319738301`, `installed_version: v0.1.1`. O HACS resolve por **tag** (release publicada); sem
release ele cairia para o branch default e a versão viraria o SHA do commit.

Entry `01KZ02TX29DT3TPGX56BV0NC0G`, `state: loaded`, `options: {max_days: 15}`, HA 2026.7.4.

**Runtime provado por completo em 2026-08-02** (`/ea-verify` passos 1–5): painel na sidebar, custom
element montado, os dois comandos WS de ponta a ponta, gráfico traçado com eixo e descarte
corretos, triângulos ◀ ▶ deslocando as datas, console sem erro do painel, e reload 2× sem
`Overwriting panel`.

## Ambiente

- **`uv` é obrigatório** (regra 10). `.venv` travado em **3.14.6** = o Python do HA; `pyproject.toml`
  fixa `requires-python`, e `.python-version` + `uv.lock` são versionados. O `.venv` é descartável:
  `uv sync` refaz. Conferir/recriar: **`/ea-env`**.
- A integração **não tem dependência própria**: roda dentro do HA, com as libs do HA (`sqlalchemy`,
  `voluptuous`). `manifest.json` tem `requirements: []` e o `pyproject.toml`, `dependencies = []` —
  o venv local existe para **rodar e validar**, não para empacotar.
- **A máquina de trabalho é só este repo.** O servidor do HA é caixa-preta acessível por MCP; não
  há caminho de arquivo do host que se possa ler, copiar ou comparar por md5.
- `fit.py` é puro `math`/`statistics` — dá para exercitá-lo direto, mas **sempre** por
  `uv run python`.
- O oráculo de `/ea-parity` é uma implementação de referência que roda fora daqui
  (`~/wrk/homeassistant/analytics/`, `./localrun.sh`, porta 8766) — **outro repo, outro escopo**.
- Requisitos de runtime: HA **2026.7+**, painel de **Energia** já configurado (`grid`, `solar`,
  `battery`) e recorder em **PostgreSQL**.
