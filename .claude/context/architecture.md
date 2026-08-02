# Arquitetura — `custom_components/energy_analytics`

Integração HA (`integration_type: service`) que **não cria entidade nenhuma**. Ela registra três
coisas no `async_setup_entry` e mais nada:

1. **arquivos estáticos** em `/energy_analytics_static` (`www/`) — uma vez por processo,
   guardado por `hass.data[DOMAIN]["static_registered"]`, porque o router do aiohttp recusa o
   mesmo prefixo duas vezes;
2. **dois comandos WebSocket** (`energy_analytics/tree`, `energy_analytics/series`);
3. **um painel na sidebar** via `panel_custom.async_register_panel(..., embed_iframe=False,
   require_admin=True)`, apontando `module_url` para `panel.js`.

## Fluxo de uma consulta

```
panel.js  hass.callWS({type:"energy_analytics/series", entities, from, to, source, mode, degree})
   │
   ▼
websocket.ws_series          valida vol.Schema, aplica o teto max_days
   │
   ▼
energy_tree.async_get_tree   prefs AO VIVO (energy.data.async_get_manager) — sem arquivo
   │
   ▼
series.fetch                 async: monta janela, resolve metadata_id, puxa linhas
   │     ├── recorder_db.query(...)      ── executor DO RECORDER ── SELECT
   │     └── hass.async_add_executor_job(_assemble, ...) ── executor GERAL ── CPU
   │             └── fit.fit(points, degree, sample, step_min)   (uma vez por série e por média)
   ▼
{step_min, sample_min, days[], unit, degree, series[], means[], missing[], dropped_total}
```

**A separação de executores é regra, não estilo.** SQL no executor do recorder; a regressão
(centenas a milhares de ajustes por consulta) no executor geral. Rodar o `fit` dentro do executor
do recorder segura a gravação de estados e o HA começa a acumular eventos.

## Módulos

| Arquivo | Papel |
|---|---|
| `__init__.py` | setup/unload da entry: estáticos + WS + painel |
| `config_flow.py` | instância única (`async_set_unique_id(DOMAIN)`); OptionsFlow com `max_days` |
| `const.py` | `DOMAIN`, URLs do painel, `MIN_DATE`, nomes de tabela, `DEFAULT_MAX_DAYS=60`, `MAX_DAYS_CEILING=120` |
| `recorder_db.py` | `async query(hass, sql, params, expanding)` — **só SELECT** |
| `energy_tree.py` | `EnergyTree` + `async_get_tree(hass)` — prefs ao vivo |
| `series.py` | SQL por fonte, bucketização de 24 h, contexto, média entre dias |
| `fit.py` | segmentação + OLS por trecho + AICc + descarte por resíduo. Puro `math`/`statistics`; **não editar** (paridade) |
| `tree.py` | árvore plana (`entity,label,color,depth,group,children`) |
| `labels.py` | `pretty()` = `getStatisticLabel` do HA (nome vem do `hass.states`) |
| `palette.py` | cores do HA — **não editar** (regra de cor + paridade) |
| `websocket.py` | os dois comandos |
| `www/panel.js` | UI inteira: custom element + Shadow DOM |
| `www/echarts.esm.min.js` | ECharts **5.6.1** ESM, ~1 MB, **vendorizado** — sem CDN, funciona offline |

## Fontes de dado (`series.SOURCES`)

| chave | tabela | bucket | delta vem de |
|---|---|---|---|
| `states` | `states` + `states_meta` | 5 min (último `state` do bucket) | `state`, **com clamp em 0** (reset de contador) |
| `short_term` | `statistics_short_term` | 5 min | `sum`, **sem clamp** (export/carga são negativos legítimos) |
| `statistics` | `statistics` | 1 h | `sum`, **sem clamp** |

Constantes de contexto: `EXT_HOURS = 3`, `EXT_SEARCH_SEC = 12*3600`, `_LOOKBACK = 86400`.

## SQL — forma obrigatória

- bind nomeado `:x` (SQLAlchemy `text()`);
- lista de ids: `metadata_id IN :ids` com `bindparam(name, expanding=True)` — `text()` + psycopg2
  **não** passa lista para `ANY` sem tipagem explícita;
- `CAST(... AS double precision)` / `CAST(... AS bigint)`, não `::`;
- **sem prefixo `public.`** — a sessão do recorder já vem no `search_path` certo;
- fuso vem de `hass.config.time_zone`, nunca de variável de ambiente.

`DISTINCT ON` e o operador de regex `~` são **Postgres-only** e isso é aceito (escopo pessoal,
recorder é TimescaleDB/Postgres).

Mudou SQL, bind ou bucketização? A prova é a skill **`ea-parity-check`**.
