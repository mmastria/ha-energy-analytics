---
name: ea-release
description: Cortar uma versão da integração — bump do version no manifest.json, commit, tag e push para o GitHub. Use quando o usuário pedir release/tag/versão nova. A tag é o que o HACS passa a oferecer como versão instalável.
---

# Release

## Onde a versão mora

**Só em `custom_components/energy_analytics/manifest.json` → `"version"`.** O HACS exige esse campo
em integração e usa a **última tag** do repositório como versão a baixar. Não há `__version__` no
código nem versão no `hacs.json` — não inventar um segundo lugar para a mesma verdade.

`hacs.json` guarda `"homeassistant": "2026.7.0"` = **versão mínima do HA**. Só mexer nele quando
uma API nova exigir piso maior.

## Passos

1. Bump em `manifest.json` (SemVer). Hoje: `0.1.0`.
2. Checagem estática (a mesma da skill `ea-deploy`, passo 1).
3. Commit + tag + push:
   ```bash
   git add -A
   git commit -m "chore: release v0.2.0"
   git tag v0.2.0
   git push origin main --tags
   ```
   Se o remoto estiver à frente: `git pull --rebase origin main` antes.
4. Esperar a CI passar (`hacs/action` + `hassfest`) — ela roda no push.
5. Instalar no HA (`/ea-deploy` a partir do passo 3): a tag **fica disponível**, mas o HACS não
   baixa nem reinicia sozinho.

## Como o HACS resolve a versão

Remoto: **`github.com/mmastria/ha-energy-analytics`** (público — o HACS exige público, e resolve
só `owner/repo` do github.com). Adicionado como **repositório custom**, id `1319738301`.

**Sem release, o HACS acompanha o branch default e a versão é o SHA do commit**
(`installed_version: 1bafb44`). Existindo a tag `vX.Y.Z`, ele resolve por tag e baixa de
`https://github.com/{repo}/archive/{version}.zip` — **a tag é mecanismo de entrega, não
organização.**

Fixar uma versão na instalação:
`ha_manage_hacs(action="download", repository_id="mmastria/ha-energy-analytics", version="v0.2.0")`.

⚠️ Owner é `mmastria`, com dois `m` — `github.com/mastria/…` é 404, e a `hacs/action` cobra URL que
existe em `documentation` e `issue_tracker`.

## CI

`.github/workflows/validate.yml` roda `hacs/action@main` (`CATEGORY: integration`) e
`home-assistant/actions/hassfest@master`, em todo push e PR. O que a `hacs/action` cobra:

- `manifest.json` com `version`, `documentation` e `issue_tracker` apontando para **URLs que
  existem**;
- `hacs.json` válido;
- estrutura `custom_components/<domain>/`.
