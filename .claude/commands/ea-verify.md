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

## 4. Painel + comandos WS (visual)

Use a **extensão do Chrome** (`claude-in-chrome`), não o Playwright: ela reaproveita a sessão do
usuário. O Playwright sobe perfil limpo e cai no `/auth/authorize` — e login com senha não é coisa
que se faça por automação.

- navegar para `http://homeassistant:8123/energy-analytics`
- **Energy Analytics** na sidebar, com `mdi:chart-bell-curve-cumulative` (só admin vê). Ela é longa:
  **role até o fim** antes de dizer que não está lá
- a árvore carrega com **33 linhas** e indentação = `energy_analytics/tree` respondeu
- marcar `PWM Grid Energy` desenha o gráfico = `energy_analytics/series` respondeu
- console sem erro **do painel**; screenshot para o registro

⚠️ **A primeira screenshot costuma sair preta** — é a página ainda montando, não falha do painel.
Confirme pelo DOM antes de concluir qualquer coisa.

⚠️ **`document.querySelector` NÃO atravessa shadow DOM.** O painel vive aninhado dentro de
`home-assistant` → `home-assistant-main` → `partial-panel-resolver`, então a busca rasa devolve
`null` e parece que o elemento não montou. Use travessia recursiva:

```js
function deepFind(sel, root=document, seen=new Set()){ if(seen.has(root))return null; seen.add(root);
  const h=root.querySelector&&root.querySelector(sel); if(h)return h;
  for(const n of (root.querySelectorAll?root.querySelectorAll("*"):[])) if(n.shadowRoot){
    const r=deepFind(sel,n.shadowRoot,seen); if(r)return r;} return null;}
const el = deepFind("energy-analytics-panel");   // el.shadowRoot, el._hass, el.shadowRoot.getElementById('from')
```

O registro do painel também sai direto do hass:
`document.querySelector("home-assistant").hass.panels["energy-analytics"]`.

**Regressão a testar sempre** (invariante 8b): esvaziar o campo `Até` e clicar ▶ **não** pode
lançar nada nem deslocar `De`. Já foi `RangeError: Invalid time value`, corrigido na v0.1.1.

## 5. `full` — ciclo de reload
Recarregar a entry **2×** (Configurações → Dispositivos e serviços → ⋮ → Recarregar) e conferir
que o log **não** traz `ValueError: Overwriting panel` (invariante H3) nem
`RuntimeError: Cannot register... already registered` nos estáticos.

## Relate

Uma linha por item: passou / falhou / **não verificado**. Não diga que funciona sem ter visto.

Estado conhecido (2026-08-02, `v0.1.1`): **passos 1–5 todos OK.** HACS `installed_version: v0.1.1`,
entry `loaded`, log limpo, painel na sidebar, gráfico traçado (192 pontos num dia parcial, 288 num
dia completo), console sem erro do painel, reload 2× sem `Overwriting panel`.

Erro de console que **não é deste projeto** e vai aparecer: o card-mod (`/www/community/
lovelace-card-mod/card-mod.js`) falha ao carregar e leva junto um `InvalidStateError` de transição.
Não confunda com falha do painel.

## Exercitar os comandos WS sem browser

O `ha_call_service` tem escape hatch de WebSocket cru — resolve o passo 4 menos a parte visual:
```
ha_call_service(ws_command="energy_analytics/tree")
ha_call_service(ws_command="energy_analytics/series",
                data={"entities": ["sensor.pwm_grid_energy"], "from": "...", "to": "...",
                      "source": "statistics", "mode": "delta", "degree": "auto"})
```
E o passo 5 sai por `homeassistant.reload_config_entry` com `entry_id`, 2×, conferindo o log depois.
