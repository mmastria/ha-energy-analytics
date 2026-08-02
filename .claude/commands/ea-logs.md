---
description: Puxa e filtra os logs do HA em busca de problemas da integração (traceback, painel, recorder). Uso /ea-logs [n]
---

`$ARGUMENTS` = quantas linhas do fim considerar (default 200).

```
ha_get_logs(source="error_log", search="energy_analytics", limit=$ARGUMENTS)
ha_get_logs(source="system", level="ERROR", limit=$ARGUMENTS)   # visão estruturada
```

Sem `search`, o `error_log` vem inteiro — filtre lá, não aqui. Para o log do container do core:
`ha_get_logs(source="system_service", slug="core")`.

Filtre e classifique. O que procurar, e o que cada coisa significa:

| padrão | leitura |
|---|---|
| `energy_analytics` + `Traceback` | erro na integração — módulo e linha estão no traceback |
| `ValueError: Overwriting panel` | `async_unload_entry` não removeu o painel (invariante **H3**) |
| `Detected blocking call` / `blocking call to open` | I/O no event loop (invariante **H2**) |
| `Recorder queue` / `is taking too long` | consulta pesada segurando o recorder — reveja o teto `max_days` e a separação de executores (**H4**) |
| `Setup failed for energy_analytics` | `dependencies` do manifest ou import quebrado |
| `websocket_api` + `energy_analytics/...` | erro dentro de um dos dois comandos |

Se o log estiver limpo, diga isso em uma linha e pare — não invente hipótese.

Nota: não há shell no servidor. O log só chega pelo `ha_get_logs` do MCP `ha-mcp`; `ha core logs`
por `ssh` **não é opção** neste projeto.
