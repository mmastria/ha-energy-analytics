---
description: Confere se o Python do .venv local é o mesmo que o HA executa e, se divergir, recria o ambiente com uv. Uso /ea-env [check|sync|recreate]
---

O interpretador local **tem que ser o mesmo que o HA roda** — é ele que executa a integração.
Validar noutra versão é validar contra um alvo que não existe. Arg `$ARGUMENTS` (default `check`).

## 1. Qual Python o HA executa (fonte da verdade)

```
ha_get_system_health()  →  health_info.data.homeassistant.info.python_version
```

Esse é o número que manda. Anote também `version` (core) — quando o core sobe, o Python pode subir
junto, e é exatamente aí que este comando importa.

## 2. Qual Python está no projeto

```bash
cat .python-version                      # pino do uv, versionado
uv run python -c "import sys; print(sys.version.split()[0])"
```

## 3. Decidir

| situação | ação |
|---|---|
| iguais | nada a fazer; só `uv sync` se o `.venv` não existir |
| divergem | **recriar** (passo 4) |
| sem `.venv` | `uv sync` |

## 4. Recriar na versão do HA (`recreate`)

```bash
uv python pin <versao-do-HA>     # reescreve .python-version
rm -rf .venv                     # o pino não migra um venv já criado
uv sync                          # recria já na versão nova
uv run python -c "import sys; print(sys.version.split()[0])"   # confirme
```

Se o `uv python list` não tiver a versão, `uv python install <versao>` antes — o uv baixa o
interpretador, não depende do Homebrew.

Atualize o `requires-python` do `pyproject.toml` se a série mudar (3.14 → 3.15) e a menção à versão
na regra 10 do `CLAUDE.md`.

## Regra que este comando protege

**Todo** Python deste repo roda por `uv run` — validação, exercício do `fit.py`, script solto.
`python3` do sistema é proibido: ele é outro interpretador, e o dia em que divergir do HA o erro
aparece em produção, não aqui.

```bash
uv run python -m py_compile custom_components/energy_analytics/*.py
uv run python -m json.tool custom_components/energy_analytics/manifest.json >/dev/null
```

O `.venv` é descartável (gitignored); `uv.lock` e `.python-version` são versionados — são eles que
amarram o interpretador local ao do HA.
