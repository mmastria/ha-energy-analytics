# APIs do Home Assistant usadas — conferidas contra o fonte do HA **2026.7.4**

Tudo abaixo foi verificado contra o código do HA **2026.7.4**, não de memória.

Para reconferir: fonte público do `home-assistant/core` na tag da versão alvo, ou comportamento
observado pelo MCP `ha-mcp` — não há acesso ao fonte dentro do servidor. Se a versão do HA subir e
algo aqui divergir, marque como não verificado em vez de assumir.

## Recorder

```python
from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.util import session_scope
```

- **`session_scope` mora em `homeassistant/helpers/recorder.py`** e é apenas **re-exportado** por
  `components/recorder/util.py` (linhas ~30-34, com `# noqa: F401`). Procurar a definição em
  `util.py` não acha nada — o import continua válido.
- **`read_only=True` NÃO impede escrita.** Docstring do próprio HA: "does not prevent the session
  from writing and is not a security measure". Ele só dispensa o commit.
- `get_instance(hass).async_add_executor_job(fn)` roda no `_db_executor` do recorder — é o
  executor certo para SQL. **Não** é onde a CPU (regressão) deve rodar.

## SQL via SQLAlchemy `text()`

```python
from sqlalchemy import bindparam, text
stmt = text(sql).bindparams(bindparam("ids", expanding=True))
session.execute(stmt, {"ids": [1, 2, 3]})
```

`expanding=True` é obrigatório para `... IN :ids`. `= ANY(:ids)` (estilo psycopg) **não**
sobrevive ao `text()` sem tipagem.

## Prefs do painel de Energia

```python
from homeassistant.components.energy.data import async_get_manager
manager = await async_get_manager(hass)
manager.data          # espelha .storage/energy
```

`async_get_manager` é `@singleton.singleton(f"{DOMAIN}_manager")` — barato de chamar, não relê
disco a cada vez.

⚠️ **Schema do `grid`:** nesta instância a fonte `grid` guarda `stat_energy_from` /
`stat_energy_to` **planos**, não dentro de listas `flow_from` / `flow_to`. O código lê o plano
primeiro e só cai para a lista como fallback (`energy_tree._flat`). Assumir só a forma de lista
sobrescreve os valores reais com `None`.

## Arquivos estáticos (HA 2024.7+)

```python
from homeassistant.components.http import StaticPathConfig
await hass.http.async_register_static_paths([
    StaticPathConfig(url_path, str(path), cache_headers)   # cache_headers=False aqui
])
```

Idempotente **não** é: o router do aiohttp recusa o mesmo prefixo duas vezes. Guardar por flag.

## Painel

```python
from homeassistant.components import frontend, panel_custom
await panel_custom.async_register_panel(
    hass, frontend_url_path=..., webcomponent_name=..., module_url=...,
    sidebar_title=..., sidebar_icon=..., require_admin=True, embed_iframe=False)
frontend.async_remove_panel(hass, PANEL_URL)      # no unload, sempre
```

`module_url` é carregado como **ES module** — por isso o ECharts vendorizado precisa ser o build
**ESM** (`echarts.esm.min.js`), não o UMD.

## WebSocket

```python
from homeassistant.components import websocket_api

@websocket_api.websocket_command({vol.Required("type"): "energy_analytics/series", ...})
@websocket_api.async_response
async def ws_series(hass, connection, msg): ...

websocket_api.async_register_command(hass, ws_series)
```

Escolhido em vez de `HomeAssistantView` porque o painel **já tem sessão autenticada**: sem Bearer
token, sem CORS, sem token expirando no meio da sessão. No front: `hass.callWS({type: ..., ...})`.

## Contrato dos dois comandos

- `energy_analytics/tree` →
  `{nodes: [{entity,label,color,depth,group,children}], sources[], max_days, min_date, today}`.
  Nó com filhos gera duas linhas extras com `{parent, synthetic: "sum"|"untracked"}`, cujo `entity`
  **não é `entity_id`**: `sum:<pai>` e `untracked:<pai>`.
- `energy_analytics/series` — params `{entities[], from, to, source, degree}` →
  ```
  {step_min, sample_min, days[], unit, degree,
   series: [{entity, day, points[[min,val]], curve[[min,val]], dropped[], segments[], total}],
   means:  [{entity, points, curve, segments, days}],
   missing[], dropped_total}
  ```
  cada `segment` = `{x0, x1, direction: up|down|flat, n, degree, coef[], r2, equation, t}`.
