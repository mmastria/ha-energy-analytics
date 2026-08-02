---
name: ea-deploy
description: Leva uma mudança de custom_components/ até o Home Assistant de produção — checagem estática, git push para o GitHub, download pelo HACS via MCP e restart do HA. Use sempre que uma mudança precisar chegar no HA rodando.
---

# Deploy da `energy_analytics` para o HA

**A entrega é o HACS, e o HACS baixa do GitHub.** Não há shell no servidor nem cópia direta de
arquivo — o `.mcp.json` carrega só o `ha-mcp`. Logo, **o `git push` é o deploy**: o que não está em
`github.com/mmastria/ha-energy-analytics` não existe para o HA.

## Regras

- **Reiniciar o HA é ação com efeito na casa.** Confirme com o usuário antes, sempre — a menos que
  ele já tenha autorizado explicitamente nesta conversa.
- **Baixar pelo HACS não ativa nada**: o Python do HA já tem os módulos carregados. Sem restart, o
  deploy não vale.
- **Push é publicação.** O repo é público. Nada de token, IP interno ou `.storage` no commit.
- Owner é **`mmastria`** (dois `m`). `mastria/ha-energy-analytics` é 404.

## Passos

### 1. Checagem estática antes de empurrar
```bash
cd ~/wrk/ha-energy-analytics
uv run python -m py_compile custom_components/energy_analytics/*.py
uv run python -m json.tool custom_components/energy_analytics/manifest.json >/dev/null
uv run python -m json.tool hacs.json >/dev/null
node --check custom_components/energy_analytics/www/panel.js
```
Qualquer um falhando: **pare**, conserte, não empurre.

### 2. Publicar
```bash
git status --short          # olhe o que vai junto
git add -A && git commit -m "fix: …"
git push origin main
```
Versão nova (tag)? Use a skill **`ea-release`** em vez de empurrar solto.

### 3. Confirmar que o HACS enxerga o commit novo
```
ha_get_hacs_info(action="search", query="energy analytics", category="integration")
```
Compare `available_version` com `git rev-parse --short HEAD`. Ainda igual ao antigo = o HACS não
releu o repositório; espere e repita (ele tem cache) ou peça ao usuário um "Atualizar informações"
no HACS.

### 4. Baixar
```
ha_manage_hacs(action="download", repository_id="mmastria/ha-energy-analytics")
```
Para fixar uma versão: `version="v0.2.0"`.

### 5. Reiniciar (com confirmação do usuário)
```
ha_restart(confirm=True)
```
O HA leva 1–5 min. Não conclua nada enquanto a API não voltar.

### 6. Conferir que subiu
```
ha_get_logs(source="error_log", search="energy_analytics", limit=30)
ha_get_integration(query="Energy Analytics")
```
Esperado: log sem traceback e `state: loaded`. `ValueError: Overwriting panel` = o
`async_unload_entry` deixou de chamar `frontend.async_remove_panel` (invariante **H3**).

Depois disso, `/ea-verify` para a prova de runtime.

## Rollback

Sem artefato no host e sem shell, o rollback é **pelo próprio HACS**:

1. `git revert` (ou `git reset` + push) para deixar o branch no estado bom — e empurrar;
2. `ha_manage_hacs(action="download", repository_id="mmastria/ha-energy-analytics", version="<tag boa>")`
   se houver tag; sem tag, o passo 1 é o único caminho;
3. `ha_restart(confirm=True)`.

Se o HA não subir por causa da integração, o usuário precisa desinstalar pelo HACS na UI e
reiniciar — **isso não dá para fazer daqui**. A config entry sobrevive (fica "não carregada") e
volta quando a integração voltar.
