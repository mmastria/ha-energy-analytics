# Harness — Energy Analytics

Harness do Claude Code para esta integração. Ponto de partida: **`HARNESS.md`** (roteamento).
Regras duras: **`../CLAUDE.md`**.

```
context/     conhecimento estável — leia conforme a tarefa
  invariants.md            OBRIGATÓRIO antes de mexer em cálculo, SQL ou UI
  architecture.md          módulos, fluxo de uma consulta, fontes de dado
  ha-apis.md               APIs do HA usadas, conferidas contra o 2026.7.4
  energy-tree.md           entidades, hierarquia, regra de cor (snapshot)
  ha-host.md               acesso (só MCP), entrega pelo HACS, versões
  decisions.md             decisões travadas — não reabrir sem pedido

agents/      ea-panel-frontend · ea-backend-data · ea-integration-reviewer
skills/      ea-deploy · ea-parity-check · ea-panel-edit · ea-release
commands/    /ea-deploy /ea-verify /ea-logs /ea-parity /ea-release
output/      saídas regeneráveis — gitignored
settings.json  permissões (leitura/checagem liberadas; vendor do ECharts negado)
```

## Convenções

- **Comando e saída compartilham o nome**, dashes→underscores:
  `/ea-parity` → `.claude/output/parity_*.json`.
- **Toda saída vai para `.claude/output/`** — nunca a raiz do projeto.
