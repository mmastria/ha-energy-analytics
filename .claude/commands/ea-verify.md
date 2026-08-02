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

Estado conhecido (2026-08-02, `v0.1.1`):
- 1–3 OK — HACS `installed_version: v0.1.1`, entry `loaded`, log limpo;
- 5 OK — reload 2× sem `Overwriting panel` nem `already registered`;
- 4 **parcial** — os dois comandos WS respondem de ponta a ponta e os estáticos são servidos com
  md5 idêntico ao repo, mas **o desenho na tela nunca foi visto**. Falta a sidebar renderizada e o
  gráfico traçado.

## Exercitar os comandos WS sem browser

O `ha_call_service` tem escape hatch de WebSocket cru — resolve o passo 4 menos a parte visual:
```
ha_call_service(ws_command="energy_analytics/tree")
ha_call_service(ws_command="energy_analytics/series",
                data={"entities": ["sensor.pwm_grid_energy"], "from": "...", "to": "...",
                      "source": "statistics", "mode": "delta", "degree": "auto"})
```
E o passo 5 sai por `homeassistant.reload_config_entry` com `entry_id`, 2×, conferindo o log depois.
