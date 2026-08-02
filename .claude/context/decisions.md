# Decisões travadas — não reabrir sem pedido do usuário

| decisão | escolha | por quê |
|---|---|---|
| Veículo | HACS `category: integration` + painel custom na sidebar | **O HACS não tem categoria "dashboard"**. As alternativas — card Lovelace (`plugin`) e add-on do Supervisor — não entregam um item de sidebar com acesso ao recorder |
| Alcance | **Só a instância "Arua" (pessoal)** | hardcodes de instância podem ficar; sem PR no `home-assistant/brands`, sem intenção de entrar na loja default do HACS |
| Fonte de dado | **sessão do recorder** (`session_scope`) | sem `psycopg` no `manifest.json`, sem segunda credencial — é o que torna seguro publicar o repo |
| ECharts | **vendorizado** em `www/echarts.esm.min.js` (5.6.1, ~1 MB) | sem CDN: o painel funciona offline e não depende de terceiro no runtime da casa |
| Contrato do WS | documentado no `README.md` e em `ha-apis.md` | não há rota de docs viva a manter em sincronia |
| SQL | **Postgres-only** (`DISTINCT ON`, operador `~`) | o recorder é TimescaleDB/Postgres; portabilidade para SQLite não é objetivo |

## Estado de verificação (2026-08-02, `v0.1.1`)

Provado: integração carrega, entry `loaded`, os dois comandos WS respondem de ponta a ponta
(`tree` e `series`, este último com SQL + regressão + descarte), estáticos servidos com md5 igual
ao repo, e o ciclo de reload 2× não estoura `Overwriting panel` (invariante H3).

**Não provado: o desenho.** A sidebar renderizada e o gráfico traçado nunca foram vistos — a
extensão do Chrome não estava conectada e o Playwright cai na tela de login do HA. Ver `/ea-verify`
passo 4.
