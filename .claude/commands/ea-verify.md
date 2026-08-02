---
description: Prova de runtime da integração — carregou, painel na sidebar, os dois comandos WS respondem, reload sem "Overwriting panel". Uso /ea-verify [quick|full]
---

Verificação de que a integração está **de fato** funcionando no HA. Arg `$ARGUMENTS`
(default = `quick`). **Nada aqui escreve no HA** exceto o reload da entry no passo 5 (`full`), que
precisa de confirmação do usuário.

Tudo passa pelo MCP `ha-mcp` ou pelo navegador — não há shell no servidor.

## 1. O que está instalado é o que está neste repo
```
ha_get_hacs_info(action="search", query="energy analytics", category="integration")
```
Compare `installed_version` com `git rev-parse --short HEAD` (sem release, o HACS mostra o SHA do
commit; com release, a tag). Divergiu = falta baixar pelo HACS, ou falta empurrar daqui.
`pending_update: true` = o GitHub tem coisa que o HA não tem.

## 2. Carregou sem erro
```
ha_get_logs(source="error_log", search="energy_analytics", limit=30)
ha_get_logs(source="system", level="ERROR", search="energy_analytics")
```
Esperado: vazio.

## 3. A config entry existe e está habilitada
```
ha_get_integration(query="Energy Analytics", include_options=True)
```
`state` = `loaded`, `disabled_by` = `null`, `options.max_days` = o esperado (hoje `15`).

## 4. Painel + comandos WS (visual — Playwright MCP)
- `browser_navigate http://homeassistant:8123/energy-analytics`
- **Energy Analytics** aparece na sidebar (visível só para admin).
- A árvore de entidades carrega = `energy_analytics/tree` respondeu.
- Marcar uma entidade (`.row[title="sensor.pwm_grid_energy"] input` dentro do shadow root) desenha
  o gráfico = `energy_analytics/series` respondeu.
- `browser_console_messages` sem erro; `browser_take_screenshot` para o registro.

Sem browser à mão: pelo console do painel,
`document.querySelector("energy-analytics-panel")._hass.callWS({type:"energy_analytics/tree"})`.

## 5. `full` — ciclo de reload
Recarregar a entry **2×** (Configurações → Dispositivos e serviços → ⋮ → Recarregar) e conferir
que o log **não** traz `ValueError: Overwriting panel` (invariante H3) nem
`RuntimeError: Cannot register... already registered` nos estáticos.

## Relate

Uma linha por item: passou / falhou / **não verificado**. Não diga que funciona sem ter visto.
Estado conhecido: passos 1–3 OK (HACS `installed_version: 1bafb44`, entry `loaded`); **4 e 5 nunca
foram exercitados**.
