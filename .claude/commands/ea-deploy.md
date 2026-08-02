---
description: Leva a mudança até o HA pelo caminho real — push para o GitHub, download pelo HACS e restart. Uso /ea-deploy [check|push|full]
---

Carregue a skill **`ea-deploy`** e siga-a. Arg `$ARGUMENTS` (default = `check`).

| arg | o que faz |
|---|---|
| `check` (default) | só a checagem estática + `git status`/`git log origin/main..HEAD` — mostra o que falta empurrar |
| `push` | checagem + commit + `git push origin main` + confere `available_version` no HACS. **Não reinicia** — o HA segue com o código velho |
| `full` | `push` + `ha_manage_hacs(download)` + `ha_restart(confirm=True)` + conferência do log |

O deploy é `git push` → HACS → restart. Commit que não foi empurrado para
`github.com/mmastria/ha-energy-analytics` é mudança que o HA não enxerga.

**Reiniciar o HA mexe na casa: confirme com o usuário antes**, a menos que ele já tenha autorizado
nesta conversa.

Antes de qualquer envio, a checagem estática (`py_compile`, `json.tool`, `node --check`). Falhou:
pare e conserte, não empurre.

Depois do restart, confira e relate:
`ha_get_logs(source="error_log", search="energy_analytics", limit=30)` e
`ha_get_integration(query="Energy Analytics")`. Esperado: log limpo e `state: loaded`.
`ValueError: Overwriting panel` = invariante H3 quebrada.
