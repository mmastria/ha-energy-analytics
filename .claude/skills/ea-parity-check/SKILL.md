---
name: ea-parity-check
description: Compara a saída do comando WebSocket energy_analytics/series com a implementação de referência (oráculo, porta 8766). Use depois de mexer em series.py, no SQL, nos binds ou em fit.py — divergência de número aponta bug de SQL/bind, nunca de matemática.
---

# Paridade contra o oráculo

Esta é a única verificação de correção do projeto: não há teste automatizado.

O oráculo é uma implementação de referência que roda **fora deste repo**, em
`~/wrk/homeassistant/analytics/` (projeto `uv` isolado, Flask em `127.0.0.1:8766`). Ela carrega
**o mesmo `fit.py`, byte a byte** — logo, para a mesma entrada, `points`, `curve`,
`segments[].coef`, `r2` e `total` têm que bater **dígito a dígito**. Se não baterem, o suspeito é
SQL / bind / bucketização, nunca o ajuste.

## Quando usar

Depois de qualquer mudança em `series.py`, no SQL, nos `bindparam`, em `energy_tree.py` ou em
`fit.py`. Não é preciso para mudança só de `panel.js`.

## Passos

### 1. Subir o oráculo
```bash
cd ~/wrk/homeassistant/analytics && ./localrun.sh    # 127.0.0.1:8766
```
Ele lê a **produção** por psycopg (`.env` → `.env.prod`). Confirme o alvo antes: apontando para o
mirror `:5433`, os números divergem **legitimamente** e a comparação não vale nada.

### 2. Pegar o mesmo payload dos dois lados

Oráculo:
```bash
curl -s "http://127.0.0.1:8766/api/series?entities=sensor.pwm_grid_energy&from=2026-07-30&to=2026-07-31&source=statistics&mode=delta&degree=auto" \
  > .claude/output/parity_flask.json
```

Integração — pelo WebSocket autenticado do HA. Sem token à mão, o caminho barato é o console do
próprio painel:
```js
// devtools em http://homeassistant:8123/energy-analytics
await document.querySelector("energy-analytics-panel")._hass.callWS({
  type: "energy_analytics/series",
  entities: ["sensor.pwm_grid_energy"],
  from: "2026-07-30", to: "2026-07-31",
  source: "statistics", mode: "delta", degree: "auto",
})
```
Salve o resultado em `.claude/output/parity_ws.json`.

### 3. Comparar os campos que importam
```bash
python3 - <<'PY'
import json
a = json.load(open(".claude/output/parity_flask.json"))
b = json.load(open(".claude/output/parity_ws.json"))
for k in ("step_min", "sample_min", "days", "unit", "dropped_total"):
    print(k, a.get(k) == b.get(k), a.get(k), b.get(k))
for sa, sb in zip(a["series"], b["series"]):
    assert sa["entity"] == sb["entity"] and sa["day"] == sb["day"], (sa["day"], sb["day"])
    print(sa["entity"], sa["day"],
          "points", sa["points"] == sb["points"],
          "curve",  sa["curve"]  == sb["curve"],
          "total",  sa["total"], sb["total"],
          "coef",   [s["coef"] for s in sa["segments"]] == [s["coef"] for s in sb["segments"]])
PY
```

## Ler a divergência

| sintoma | causa provável |
|---|---|
| primeiro bucket do dia diferente | âncora do `lag` (invariante 4) — o lookback de 1 dia sumiu |
| série do solar começa às 07:00 | preenchimento de bucket vazio (invariante 3b) |
| primeiro/último trecho cortado | contexto de 3 h com dado (invariante 3c) |
| delta negativo virou 0 nas fontes `statistics*` | clamp aplicado onde não devia (invariante 3) |
| `coef` diferente com os mesmos `points` | os dois `fit.py` divergiram — eles têm que ser idênticos |
| tudo deslocado no tempo | TZ: a integração usa `hass.config.time_zone`, o oráculo usa o `.env` |

## Número de referência

Janela 2026-07-31 ±12 h, `sensor.pwm_grid_energy`, `source=statistics`: `n=683`,
`sum_v=12776394.1430`, `sum_d=75.3880`, `min_d=0.0000`. Bateu igual dos dois lados — serve de
âncora rápida antes de investigar qualquer divergência nova.
