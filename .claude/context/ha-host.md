# Instância alvo — casa "Arua"

Este projeto é **pessoal, para uma instância só**. Hardcodes de instância são aceitos (decisão
travada com o usuário); não há PR no `home-assistant/brands` a fazer, nem intenção de entrar na
loja default do HACS.

## Acesso — só MCP

**Não há shell no servidor** — nem leitura ou escrita de arquivo do host. O `.mcp.json` traz **um**
servidor:

| o quê | como |
|---|---|
| API core do HA | MCP `ha-mcp` (`mcp-proxy` → `http://172.24.24.221:9584/…`) |
| UI / painel | navegador: `http://homeassistant:8123/energy-analytics` |
| logs | `ha_get_logs(source="error_log"\|"system", search="energy_analytics")` |
| estado da entry | `ha_get_integration(query="Energy Analytics")` |
| estado no HACS | `ha_get_hacs_info(action="search", query="energy analytics")` |
| instalar/atualizar | `ha_manage_hacs(action="download", repository_id="mmastria/ha-energy-analytics")` |
| ativar o código novo | `ha_restart(confirm=True)` — **confirme com o usuário antes** |
| prefs do painel de Energia | `ha_manage_energy_prefs` |

Consequência prática: não dá para conferir md5 arquivo a arquivo contra o host. A prova de que o
código certo está lá é o `installed_version` do HACS × o commit deste repo.

## Entrega = HACS

Remoto: **`git@github.com:mmastria/ha-energy-analytics.git`** (público, github.com — é o que o
HACS exige). Adicionado ao HACS como **repositório custom**, categoria `integration`, id
`1319738301`.

O caminho de uma mudança até a casa:

```
edita aqui → checagem estática → git commit → git push origin main
   → ha_manage_hacs(action="download", repository_id="mmastria/ha-energy-analytics")
   → ha_restart(confirm=True)        ← sem isto o Python do HA segue com o código velho
   → /ea-verify
```

**Sem release, o HACS acompanha o branch default e a "versão" é o SHA do commit** — hoje
`installed_version: 1bafb44`. Cortada a primeira tag `vX.Y.Z`, o HACS resolve por tag e
`pending_update: true` vira o sinal de que há coisa nova para baixar.

⚠️ Atenção ao owner: o remoto é **`mmastria`** (dois `m`). `github.com/mastria/ha-energy-analytics`
**não existe** (404) — `documentation` e `issue_tracker` do manifest apontando para lá reprovam na
`hacs/action`.

## Versões (conferidas 2026-08-02 por `ha_get_system_health`)

- Home Assistant Core **2026.7.4**, instalação **Supervised**, amd64, Debian 12, Supervisor
  2026.07.5.
- **Python 3.14.6** — `health_info.data.homeassistant.info.python_version`. **É o número que o
  `.venv` local tem que espelhar** (regra 10 / `/ea-env`): é este interpretador que executa a
  integração.
- HACS **2.0.5**.
- Recorder = **PostgreSQL 17.6** + TimescaleDB (por isso `DISTINCT ON` e `~` são aceitáveis),
  base com ~47,7 GiB.

## Outras integrações custom instaladas

Nenhuma colide com o domínio `energy_analytics`: `hacs`, `spook`, `spook_inverse`, `pyscript`,
`device_tools`, `huawei_solar`, `alexa_media`, `bermuda`, `watchman`, `xtend_tuya`,
`smartthinq_sensors`, `solcast_solar`, `import_statistics`, `history_editor`, `ha_mcp_tools`,
`mcp_assist`, `unifi_wan`, `advanced_snapshot`, `astroweather`, `nhs`, `openai_whisper_cloud`.

## Git

Git local é liberado neste projeto — não há hook bloqueando escrita.

`git push` **não é opcional nem cosmético: é o deploy.** Commit local que não foi empurrado é
mudança que o HA não tem como enxergar.
