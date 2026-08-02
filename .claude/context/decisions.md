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

**Runtime provado por completo**, passos 1–5 do `/ea-verify`: entry `loaded`; painel na sidebar com
`mdi:chart-bell-curve-cumulative` e `require_admin`; `energy-analytics-panel` monta com shadow root
e `_hass`; `tree` devolve as 33 linhas com a indentação da árvore; `series` desenha (192 pontos em
1 dia parcial, 288 num dia completo) com eixo 00:00–24:00 e descarte no rodapé; ◀ ▶ deslocam as
duas datas e redesenham; console sem erro do painel; reload 2× sem `Overwriting panel` (H3).

Regressão da v0.1.1 confirmada no navegador: campo de data vazio + clique em ▶ não lança nada e não
desloca (invariante 8b).

Ruído conhecido e **alheio a este projeto**: o console do HA acusa
`Failed to fetch dynamically imported module: /www/community/lovelace-card-mod/card-mod.js` e um
`InvalidStateError` de transição do frontend. É o card-mod, outra integração do HACS.
