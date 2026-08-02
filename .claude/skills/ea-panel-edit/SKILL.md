---
name: ea-panel-edit
description: Editar www/panel.js — a UI inteira do painel (custom element + Shadow DOM + ECharts). Use para qualquer mudança visual, de controle ou de eixo. Codifica as invariantes 7b/8/8b/9 e H1, que regridem em silêncio.
---

# Editar `www/panel.js`

Um único arquivo (~670 linhas): custom element `energy-analytics-panel`, Shadow DOM, ECharts
importado como ES module de `./echarts.esm.min.js`. **Leia `.claude/context/invariants.md` antes de
tocar.** As armadilhas abaixo não dão erro — elas mudam o desenho e ninguém percebe.

## As cinco que já quebraram

1. **`set hass(hass)` só guarda** (`this._hass = hass`). Ele dispara a cada mudança de estado do HA
   — dezenas por segundo. `build()` ou `callWS` ali derruba o painel. (**H1**)
2. **`min`/`max` do eixo Y vão SEMPRE explícitos.** `setOption` faz **merge**: omitir deixa o limite
   anterior sobreviver à troca. (**8**)
3. **`ensureY` só recalcula quando muda `state.yKey` = `datas|modo|Pontos|entidades`.**
   `Curva`/`Média`, fonte e grau **não** mexem na régua — comparar dois desenhos exige a mesma
   régua. Dois regimes: com `Pontos`, régua sai dos pontos **mantidos** + média; sem `Pontos`, sai
   das **curvas** (visíveis ou não) com folga `_SLACK`. (**8**)
4. **`datesChanged` NÃO chama `build()`.** Recarrega com debounce de 250 ms; `build()` antes da
   resposta calcula a régua com o payload velho sob a chave nova e ela congela errada. Campo de
   data vazio = digitação em andamento, não completar com hoje. (**8b**)
5. **O `onchange` do checkbox não re-renderiza a árvore** — o `<label>` re-dispara o toggle sobre o
   input novo e desmarca de volta. Atualize só a classe da linha. (**9**)

E: **a linha de média desenha SEMPRE `m.curve`**, nunca `m.points` (**7b**). Os três botões
(`Pontos`/`Curva`/`Média`) são **só aparência** — nenhum deles altera número nenhum.

## Coisas do HA que o painel precisa respeitar

- **ES module**: `module_url` é carregado como módulo. O ECharts vendorizado tem que ser o build
  **ESM**. Não trocar por UMD, não voltar para CDN (offline/CSP mataria o painel).
- **`ResizeObserver`** no host dispara `chart.resize()` — a sidebar colapsando e o `narrow` mudam a
  largura sem `window.resize`.
- **Shadow DOM** isola o CSS escuro do painel do tema do HA. Estilo novo entra dentro do shadow.
- Dados só por `this._hass.callWS(...)`. Sem `fetch`, sem token, sem CORS.
- Pontos de contexto: o front **descarta `x<0` e `x>1440`** — eles existem só para o cálculo.

## Depois de editar

```bash
node --check custom_components/energy_analytics/www/panel.js
```
Depois `/ea-deploy` (o navegador cacheia: recarregue com cache desligado, ou confirme que o arquivo
servido em `/energy_analytics_static/panel.js` é o novo).

Prova visual com Playwright MCP em `http://homeassistant:8123/energy-analytics` — ver `/ea-verify`.
Marcar entidade: clicar em `.row[title="<entity_id>"] input` dentro do shadow root.
