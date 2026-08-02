# Invariantes — quebrar qualquer um destes regride o painel em silêncio

Cada uma nasceu de um bug real. A numeração é fixa e citada pelo nome em skills, agentes e
comandos — **não renumere**.

## Dados (backend)

**1. SOMENTE LEITURA.** A integração só emite `SELECT`. Nenhum `INSERT`/`UPDATE`/`DELETE`, em
lugar nenhum, jamais. O alvo é o **recorder de produção**.
⚠️ `session_scope(read_only=True)` **NÃO** é barreira de escrita — o próprio HA documenta que ele
só sinaliza que a sessão dispensa commit. A garantia aqui é o **código**, não a flag.

**2. Cor = posição em `device_consumption`.** `palette.device(i)` com `i` = índice do device nas
prefs do painel de Energia (é o `getGraphColorByIndex` do HA). A cor está presa à **entidade**,
nunca à ordem do gráfico. Reordenar os devices no painel de Energia troca TODAS as cores — é a
mesma regra do HA, não é bug.

**3. Odômetro ≠ potência.** As entidades são `total_increasing` em kWh. `delta` (default) é o que
se sobrepõe; `raw` é inspeção. **Não "corrigir" delta negativo nas fontes `statistics*`** (export e
carga de bateria são legitimamente negativos). O clamp em 0 existe **só** na fonte `states`, onde
o negativo é reset de contador.

**3b. Vazio em `states` = odômetro parado, não falta de dado.** Todo bucket sem linha é
preenchido com **0** — não houve consumo. Sem isso a curva do solar começava às 07:00 e terminava
às 17:30. Não preencher **antes da primeira amostra** da entidade (não há âncora) nem **depois de
agora**.

**3c. Contexto = `EXT_HOURS` horas COM DADO de cada lado** (`_with_context`), não recorte fixo de
relógio: anda-se para fora somando horas DISTINTAS que tenham amostra, dentro de `EXT_SEARCH_SEC`.
Esses pontos **não** são desenhados, **não** entram na escala (o front descarta `x<0` e `x>1440`)
e **não** entram no `total`.

**4. Âncora do `lag`.** Todo SQL puxa também a última amostra ANTES da janela (lookback de 1 dia).
Sem isso o primeiro bucket de cada janela perde o delta.

**6. A curva é regressão, não interpolação.** `fit.py` faz OLS (resíduo **vertical**) por trecho de
subida/descida/platô; a suavização serve só para ACHAR os limites dos trechos — o ajuste usa os
pontos **crus**. Grau por **AICc** (tolerância de R² aceitava reta em rampa curva). Nas janelas de
blend entre trechos a linha é combinação linear de dois polinômios — ali ela não é, por definição,
o mínimo-quadrado de nenhum dos dois. **Não trocar por spline/orthogonal fit sem pedido**: a
equação por trecho é o entregável.

**7. Descarte por resíduo é UMA regra só** (`fit.fit`): `|y − p(t)| > max(3·σ_res, 5 % da
amplitude)`, ≤20 % do trecho, com refit sem os descartados. Vale para a REGRESSÃO e para a ESCALA;
a **média entre dias usa TODOS os pontos** (é média dos dados, não do ajuste). **Não criar um
segundo critério de outlier no front.**

## Front (`www/panel.js`)

**7b. Toggle é aparência, nunca cálculo.** `Pontos` / `Curva` / `Média` só mostram ou escondem
série. A linha de média desenha **SEMPRE `m.curve`** — já houve o bug de ela cair para `m.points`
quando `Curva` estava desligada, mudando o traçado sem que nenhum dado mudasse.

**8. Eixo Y é TRAVADO, com DOIS regimes.** `ensureY` recalcula só quando muda a chave
`datas|Pontos|entidades` (`state.yKey`):
- com `Pontos`: régua sai dos pontos **MANTIDOS** + média (a curva do dia fica fora — seu envelope
  reintroduziria o descartado);
- sem `Pontos`: sai das **CURVAS** (dias + média), visíveis ou não, com folga `_SLACK` nas duas
  pontas e passo de arredondamento mais fino.

`Curva` / `Média`, **fonte** e **grau** NÃO mexem na régua. `min`/`max` vão **SEMPRE explícitos**
(`null` = automático): o `setOption` faz **merge** e um limite anterior sobreviveria à troca.

**8b. `datesChanged` NÃO chama `build()`.** Passo de data recarrega com debounce de 250 ms; chamar
`build()` antes da resposta calcularia a régua com o payload **VELHO** sob a chave **nova** e ela
ficaria congelada errada. Campo de data vazio = digitação em andamento: não completar com hoje.

**9. Não re-renderizar a árvore dentro do `onchange` do checkbox** — o `<label>` re-dispara o
toggle sobre o input novo e desmarca de volta. A linha atualiza só a própria classe. `syncSynthetic`
obedece a isto: mexe apenas nas duas linhas derivadas do pai, nunca redesenha a árvore.

**10. `Σ filhos` / `(untracked)` são presas ao pai.** Só selecionáveis com o pai selecionado;
desmarcar o pai **desmarca e trava** as duas. A trava é aplicada em três lugares e os três têm que
concordar: `renderTree` (ao desenhar), `syncSynthetic` (ao clicar no pai) e a restauração do estado
salvo (derivada sem o pai na lista é descartada). O id delas **não é `entity_id`** — é
`sum:<pai>` / `untracked:<pai>`; qualquer código que assuma `entity_id` aqui quebra.

**11. O estado salvo não guarda datas.** Só a **distância em dias** (`span = daysBetween() − 1`).
Ao abrir, `Até` = hoje e `De` = hoje − `span`, preso a `MIN_DATE` e ao teto `max_days`. Salvar a
data absoluta faria o painel abrir no passado e parecer congelado.

## HA (integração e painel)

**H1. `set hass(hass)` só GUARDA a referência.** Ele dispara a cada mudança de estado do HA
(dezenas por segundo nesta casa). Qualquer `build()` / `callWS` ali derruba o painel.

**H2. Nada de I/O bloqueante no event loop.** Sem `open()`, `json.load`, `connect()` no import nem
no `async_setup_entry`. O HA 2026.x levanta erro, não warning.

**H3. `async_unload_entry` tem que chamar `frontend.async_remove_panel`.** Sem isso o próximo
setup estoura `ValueError: Overwriting panel`. Estáticos e comandos WS podem ficar — registrá-los
de novo é idempotente (o estático é guardado por flag; ver `architecture.md`).

**H4. Separação de executores.** SQL no executor do **recorder**; `fit` no executor **geral**.
Ver `architecture.md`.

**H5. `max_days` chega como `float`.** O `NumberSelector` devolve `15.0`; sempre `int(...)`, senão
a mensagem de erro sai "60.0". (A entry viva hoje tem `max_days: 15.0`.)
