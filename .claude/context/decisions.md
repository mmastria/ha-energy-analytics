# Decisões travadas — não reabrir sem pedido do usuário

| decisão | escolha | por quê |
|---|---|---|
| Veículo | HACS `category: integration` + painel custom na sidebar | **O HACS não tem categoria "dashboard"**. As alternativas — card Lovelace (`plugin`) e add-on do Supervisor — não entregam um item de sidebar com acesso ao recorder |
| Alcance | **Só a instância "Arua" (pessoal)** | hardcodes de instância podem ficar; sem PR no `home-assistant/brands`, sem intenção de entrar na loja default do HACS — ver *Não-distribuição* abaixo |
| Ícone no HACS | **placeholder cinza aceito** | corrigir exige PR no `home-assistant/brands`, que é divulgação pública permanente de um projeto que não se propõe a terceiros |
| Fonte de dado | **sessão do recorder** (`session_scope`) | sem `psycopg` no `manifest.json`, sem segunda credencial — é o que torna seguro publicar o repo |
| ECharts | **vendorizado** em `www/echarts.esm.min.js` (5.6.1, ~1 MB) | sem CDN: o painel funciona offline e não depende de terceiro no runtime da casa |
| Contrato do WS | documentado no `README.md` e em `ha-apis.md` | não há rota de docs viva a manter em sincronia |
| SQL | **Postgres-only** (`DISTINCT ON`, operador `~`) | o recorder é TimescaleDB/Postgres; portabilidade para SQLite não é objetivo |

## Não-distribuição — decidido em 2026-08-02

**A integração não deve ser publicada nem tornada instalável por terceiros.** Não é pendência de
polimento: o alvo é uma instância só.

Três coisas distintas, que se confundem com facilidade:

| ato | o que faz | status |
|---|---|---|
| repo público no GitHub | permite ao HACS baixar por URL como **repositório custom** | **feito, e necessário** — o HACS não baixa de repo privado sem token |
| PR em `home-assistant/brands` | hospeda `icon.png`/`icon@2x.png` num CDN público, indexados pelo domínio | **não fazer** |
| PR em `hacs/default` | lista na **busca do HACS** para todo mundo — é isto que publica de fato | **não fazer** |

Só o terceiro distribui. O segundo apenas conserta o ícone, mas cria registro público permanente no
repo do Home Assistant, revisado por mantenedor — divulgação sem contrapartida, já que o projeto não
serve a outro ambiente.

**Por que não serve** (o que quebra noutra instância, não o que falta):

- **Recorder Postgres/TimescaleDB obrigatório** — `DISTINCT ON` e `~` não existem no SQLite, que é
  o default do HA. Porte fora de escopo (decisão *SQL* na tabela acima).
- **Painel de Energia com `grid` + `solar` + `battery`** — a raiz `Total consumed` é derivada das 5
  fontes; faltando solar ou bateria a conta não fecha.
- **Retenção longa de `states` com passo de 5 min** — com os 10 dias default a tela nasce quase
  vazia.
- **Sem matriz de compatibilidade, sem migração de config, sem suporte.** HA 2026.7+ porque é o que
  roda aqui.
- **O oráculo de `/ea-parity` roda fora deste repo** (`~/wrk/homeassistant/analytics/`, porta 8766).
  É a única prova de correção dos números e terceiro não reproduz.

Efeito colateral aceito: o placeholder cinza **"icon not available"** no HACS. Vem de
`https://brands.home-assistant.io/_/energy_analytics/icon.png`, que responde **HTTP 200** com a
imagem de placeholder para domínio não registrado — por isso não aparece erro nenhum no console.
Os PNGs em `custom_components/energy_analytics/brand/` são **inertes**: o HACS resolve o ícone pelo
domínio contra o CDN, nunca lendo arquivo do repositório. Ficam ali só como fonte, caso a decisão
mude.

Registrado no `README.md` na seção **Escopo**, para quem chegar pelo GitHub.

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
