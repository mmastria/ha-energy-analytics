---
description: Corta uma versão — bump do manifest.json, commit, tag e push. Uso /ea-release <x.y.z>
---

Carregue a skill **`ea-release`** e siga-a. `$ARGUMENTS` = versão SemVer alvo (ex.: `0.2.0`).

Sem argumento: mostre a versão atual (`manifest.json` → `version`), a última tag
(`git describe --tags --abbrev=0`) e o que mudou desde ela (`git log --oneline`), e proponha o
próximo número — **sem** commitar.

Regras:
- a versão mora **só** em `custom_components/energy_analytics/manifest.json`;
- tag `vX.Y.Z`, push com `--tags`;
- a tag **fica disponível** no HACS, mas não se instala sozinha: baixar + reiniciar é `/ea-deploy`.
