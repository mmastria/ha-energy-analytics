---
description: Compara a saída do WS energy_analytics/series com a implementação de referência (oráculo, porta 8766). Uso /ea-parity [entidade] [de] [ate]
---

Carregue a skill **`ea-parity-check`** e siga-a.

`$ARGUMENTS` — opcional: `<entity_id> <YYYY-MM-DD> <YYYY-MM-DD>`.
Default: `sensor.pwm_grid_energy` nos dois últimos dias completos, `source=statistics`,
`mode=delta`, `degree=auto`.

Lembretes:
- o oráculo roda em `~/wrk/homeassistant/analytics/` — **outro repo**, `./localrun.sh`, porta 8766;
- confirme que o `.env` dele aponta para a **produção** (`.env.prod`); apontando para o mirror
  `:5433` a divergência é legítima e a comparação não vale;
- `fit.py` é o mesmo código nos dois lados — divergência de número é bug de **SQL/bind/bucket**;
- saídas em `.claude/output/parity_*.json`.
