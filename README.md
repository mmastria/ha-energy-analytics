# Energy Analytics

Painel do Home Assistant que sobrepõe **perfis diários de 24 h** das entidades do **painel de
Energia**, lendo `states` e `statistics*` pela sessão do **recorder** (**somente `SELECT`**).

Serve para comparar o **formato** do dia — quando a casa consome, não quanto no mês. Para os
totais por dia/mês/ano use o painel de Energia oficial do HA.

## Instalação (HACS)

1. HACS → Integrações → ⋮ → **Repositórios personalizados**
2. URL `https://github.com/mmastria/ha-energy-analytics`, categoria **Integration** → Adicionar
3. Baixar **Energy Analytics** → **reiniciar o HA**
4. Configurações → Dispositivos e serviços → **Adicionar integração** → *Energy Analytics*

O painel aparece na barra lateral como **Energy Analytics** (visível só para administradores).
Em *Configurar* dá para mudar o **máximo de dias por consulta** (default 60).

Requisitos: HA **2026.7+**, painel de **Energia** já configurado (fontes `grid`, `solar` e
`battery`) e recorder em **PostgreSQL** — o SQL usa `DISTINCT ON` e o operador de regex `~`.

## Tela

- **Coluna esquerda** — as entidades do painel de Energia (fontes + devices), com **indentação
  pela árvore de consumo** (`included_in_stat`) e checkbox, todos **desmarcados**. Qualquer
  marcação/desmarcação refaz o gráfico.
- **`Σ filhos` e `(untracked)`** — todo nó com filhos ganha duas linhas derivadas, no nível dos
  filhos: `Σ filhos` **abre** a lista e `(untracked)` a **fecha**. Elas se comportam como qualquer
  entidade (regressão, descarte, total, média), mas só ficam **selecionáveis com o pai
  selecionado** — desmarcar o pai desmarca e trava as duas.
- **Datas De → Até** — ambas iniciam **hoje** (fuso do HA); qualquer mudança refaz o gráfico.
  Janela permitida: **01/01/2024 → hoje**. As duas pontas se acompanham (mexer no `De` para frente
  empurra o `Até`; puxar o `Até` para trás puxa o `De`), sempre dentro da janela.
- **Triângulos ◀ ▶** — cada clique desloca **as duas datas** 1 dia, **preservando o intervalo**;
  ficam desabilitados na borda da janela.
- **`Agora`** — põe as duas datas em **hoje** e recarrega.
- **Setas ↑ ↓ do teclado nos campos de data** rolam de forma **contínua**: no segmento do dia,
  31/07 ↑ vira 01/08 e 01/01 ↓ vira 31/12 do ano anterior; no segmento do mês, 12 ↑ vira 01 do ano
  seguinte. (O `input[type=date]` nativo gira cada segmento dentro do seu pai; o painel detecta o
  estouro e reescreve a data.) Na borda da janela o passo simplesmente não anda.
- **Botões** `Pontos` / `Curva` / `Média` (on/off) e os seletores `Fonte` / `Valor` / `Ajuste`.
- **A seleção e a configuração voltam como estavam** na próxima vez que a tela abrir. As **datas
  não** são salvas: guarda-se a **distância em dias** entre elas, e ao abrir `Até` volta em **hoje**
  com `De` recuando essa distância.
- **Gráfico** — eixo X **sempre 1 dia**: grade fina a cada **5 min**, linha de grade destacada a
  cada **30 min**, rótulo a cada **hora** (00:00…24:00).

## Curvas = regressão, não interpolação

A linha desenhada **não passa pelos pontos**: os pontos são o dado observado e a curva é o
**ajuste por mínimos quadrados** (OLS) de um polinômio, calculado **por trecho** de subida /
descida / platô (`fit.py`):

1. **suavização** (mediana móvel → média móvel) usada **só para achar os limites** dos trechos;
2. **segmentação** por run-length do sinal da inclinação (diferença central), com **banda morta** —
   é o que separa o platô da madrugada da rampa do sol; trechos curtos são fundidos no vizinho;
3. **ajuste** por mínimos quadrados sobre os pontos **crus** do trecho, com `t = (x−x0)/(x1−x0)`
   em `[0,1]` (normalizar segura o condicionamento da Vandermonde até grau 5);
4. **grau escolhido por AICc** (`auto`) — R² sempre sobe com o grau, então tolerância de R² aceitava
   reta em rampa curva; trecho quase plano em relação à série toda tem grau limitado a 2;
5. **amostragem** a cada 2 min, com blend linear na fronteira entre trechos (curva contínua).

### Vazio = odômetro parado (delta 0)

Um sensor de energia **para de gravar** quando o valor não muda: o solar não tem linha nenhuma
entre 17:30 e 07:00, a secadora fica dias sem linha. Isso **não** é ausência de informação — é
consumo zero. Sem esse tratamento a curva do solar começava às 07:00 e terminava às 17:30.

Todo bucket vazio é preenchido: **`delta` → 0**, **`bruto` → último valor conhecido**. O
preenchimento não inventa dado **antes da primeira amostra** da entidade nem **depois de agora**
(por isso a curva de hoje termina no horário atual).

### Contexto de 3 horas COM DADO (curva completa de 00:00 a 24:00)

O ajuste de cada dia enxerga, além do dia, **3 horas com dado de cada lado** — não é um recorte de
relógio: a busca anda para fora somando **horas distintas que tenham amostra** (até 12 h de área de
busca). Sem isso o primeiro e o último trecho nascem e morrem dentro do dia e a curva sai cortada.

Esses pontos de contexto servem **só ao cálculo**: não são desenhados, não entram na escala
vertical, não mudam o eixo horizontal e não entram no `total` do dia. No painel de equações um
trecho que começa/termina fora do dia aparece com o prefixo `d−1` / `d+1`.

O **desenho** de cada trecho é limitado ao envelope dos pontos **mantidos** daquele trecho (±5 %):
polinômio de grau alto dispara nas bordas. Os `coef` e o `r2` são os do ajuste, **sem** esse recorte.

### Pontos descartados

Depois do primeiro ajuste, o ponto cujo **resíduo** contra a curva do próprio trecho passa de
`max(3·σ_res, 5 % da amplitude do dia)` é **descartado** (`σ_res` = MAD dos resíduos, robusto; no
máximo 20 % dos pontos de um trecho). O trecho é então **reajustado sem ele**. Um ponto descartado:

- sai do **reajuste** daquele trecho;
- **não entra na escala** do eixo Y (nem ele, nem a curva do dia — o envelope dela o conteria);
- **continua na média** entre dias: a média é a média dos DADOS, não do ajuste;
- continua **desenhado**, como **anel vazado**, e é contado no rodapé.

Medido em 12 dias (5 min): rede 170/3456 descartados, solar 96/3456 (pico real de 0,593
**mantido**), geladeira 309/3456 (ciclo liga/desliga: σ_res minúsculo no platô).

> Os três botões (`Pontos`, `Curva`, `Média`) são **só aparência**: nenhum deles altera número
> algum. A linha de média é sempre a regressão da média — desligar `Curva` esconde as curvas dos
> dias e não toca nela.

## Escala vertical — travada, com dois regimes

A régua vertical **não muda** ao ligar/desligar `Curva` ou `Média`, ao trocar de **fonte** nem ao
mudar o **grau**: comparar dois desenhos exige a mesma régua. Ela é recalculada quando mudam as
**datas**, as **entidades**, o **modo do valor** (`delta` ↔ `bruto`) ou o botão **`Pontos`**:

| `Pontos` | régua calculada sobre | base |
|---|---|---|
| ligado | pontos **mantidos** + média (pontos e curva) | zero quando os dados são ≥ 0 e chegam perto dele; senão zoom no intervalo |
| desligado | **curvas dos dias + curva da média**, estejam elas visíveis ou não | folga de ≥ 8 % do intervalo nas **duas** pontas |

## Sobreposição de dias

| dia | `d` (mais recente) | `d−1` | `d−2` e `d−3` | `d−4` ou mais |
|---|---|---|---|---|
| opacidade | 100 % | 80 % | 60 % | 40 % |

`d` é a data mais recente **da seleção**, não a de hoje. Há ainda uma **curva média** por entidade
sobre todos os dias (média ponto a ponto no backend, depois regredida) — mesma cor, sem
transparência, traço mais grosso. Ligada por default quando o intervalo tem mais de 1 dia.

## Cores

Cor do device = `getGraphColorByIndex(i)` com `i` = **posição em `device_consumption`** das prefs
do painel de Energia — presa à entidade, nunca à ordem do gráfico. Fontes usam as CSS vars
`--energy-*-color` do HA (solar `#ff9800`, bateria out/in `#4db6ac`/`#f06292`, rede in/out
`#488fc2`/`#a280db`). Rótulos seguem o `getStatisticLabel` do HA: `name` das prefs →
`friendly_name` → derivação do `entity_id`.

Reordenar os devices no painel de Energia **troca todas as cores** — é a mesma regra do HA.

## Fonte × Valor

As entidades do painel de Energia são **odômetros** (`total_increasing`, kWh acumulado).

| Fonte | tabela | bucket |
|---|---|---|
| `states (5 min)` | `states` + `states_meta` | 5 min (último `state` do bucket) |
| `statistics_short_term (5 min)` | `statistics_short_term` | 5 min |
| `statistics (1 h)` | `statistics` | 1 h |

| Valor | o que plota |
|---|---|
| `delta` (default) | energia **no** bucket = valor − valor do bucket anterior. É a única leitura sobreponível dia a dia e a única em que a média tem sentido. Nas fontes `statistics*` o delta vem da coluna `sum` (odômetro canônico, imune a reset) e **não** é clampado; em `states` vem do próprio `state`, com clamp em 0 (reset do contador). |
| `raw` | o valor lido, sem derivar (inspeção do odômetro). |

O `lag` do primeiro bucket é ancorado na **última amostra antes da janela** (lookback de 1 dia),
senão o primeiro bucket de cada janela perderia o delta.

## Séries derivadas (`Σ filhos` / `(untracked)`)

Nascem no **backend**, sobre a grade já preenchida e **antes** da divisão por dia — a curva é
regressão do `fit.py`, que roda no servidor. Com isso elas percorrem exatamente o mesmo caminho de
qualquer entidade: contexto de 3 h, ajuste, descarte por resíduo, total e média entre dias.

A soma é dos **filhos diretos**. Somar a subárvore inteira contaria o neto duas vezes — uma na
soma do pai dele, outra na do avô; o neto já aparece na `Σ filhos` do próprio pai, que por sua vez
é um dos termos da soma do avô.

`pai − Σ filhos` **não é clampado**: negativo significa árvore mal configurada ou sensor errado, e
zerar isso esconderia o problema. Pai e filhos são consultados mesmo sem estarem selecionados —
alimentam a conta sem virar série desenhada.

No gráfico, `Σ filhos` herda a cor do pai com **traço tracejado** (sem isso as duas linhas seriam
indistinguíveis) e `(untracked)` usa o cinza `#9e9e9e` de "não monitorado" do HA. Com a `Σ` ligada,
o tooltip ganha na última linha `Δ (pai, Σ filhos)`.

## API (WebSocket)

- `energy_analytics/tree` → `{nodes[{entity,label,color,depth,group,children}], sources[],
  max_days, min_date, today}`. Nó com filhos gera duas linhas extras, que trazem também
  `{parent, synthetic: "sum"|"untracked"}` e cujo `entity` **não é um `entity_id`**:
  `sum:<pai>` (soma dos filhos **diretos**) e `untracked:<pai>` (pai − essa soma).
- `energy_analytics/series` — `{entities[], from, to, source, mode, degree}` →
  `{step_min, sample_min, days[], unit, degree,
  series[{entity, day, points[[min,val]], curve[[min,val]], dropped[], segments[], total}],
  means[{entity, points, curve, segments, days}], missing[], dropped_total}`;
  cada `segment` = `{x0, x1, direction: up|down|flat, n, degree, coef[], r2, equation, t}`.

## Arquivos

```
custom_components/energy_analytics/
  __init__.py       painel + estáticos + registro dos comandos WS
  config_flow.py    instância única; opção max_days
  const.py          domínio, URLs do painel, nomes das tabelas, MIN_DATE
  energy_tree.py    árvore lida AO VIVO do manager do painel de Energia
  recorder_db.py    SELECT pela sessão do recorder (executor do recorder)
  series.py         SQL (bucket + lag ancorado), bucketização 24 h e média entre dias
  fit.py            segmentação subida/descida + regressão polinomial (OLS) por trecho
  tree.py           árvore plana com depth + cor
  palette.py        cores do HA
  labels.py         getStatisticLabel do HA
  websocket.py      comandos energy_analytics/tree e /series
  www/panel.js      UI (custom element + Shadow DOM)
  www/echarts.esm.min.js   ECharts 5.6.1 vendorizado (sem CDN, funciona offline)
```

## Notas

- **Somente leitura**: a integração só emite `SELECT` — nenhum `INSERT`/`UPDATE`/`DELETE` em
  lugar nenhum. (O `read_only=True` do `session_scope` apenas dispensa o commit; o próprio HA
  documenta que ele não impede escrita, então a garantia aqui é o código, não a flag.)
- O SQL roda no executor do **recorder**; a regressão (centenas a milhares de ajustes por
  consulta) roda no executor **geral** — junto, o fit seguraria a gravação de estados do HA.
- Intervalos grandes × muitas entidades custam tempo de recorder. `max_days` é o freio.
