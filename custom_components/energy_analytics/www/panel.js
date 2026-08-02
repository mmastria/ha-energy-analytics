/* Energy Analytics — painel do HA.
 *
 * Porte 1:1 do `analytics_app/templates/index.html` do app Flask. Mudou o invólucro (custom
 * element + Shadow DOM), a origem do dado (`hass.callWS` em vez de `fetch /api/*`) e a origem
 * do ECharts (vendorizado ao lado, sem CDN). A LÓGICA do gráfico é a mesma, de propósito:
 * escala travada, descarte por resíduo, opacidade por idade do dia e regras de data já foram
 * depuradas contra dados reais — ver as regras 7b/8/8b/9 do CLAUDE.md do projeto original.
 */
import * as echarts from "./echarts.esm.min.js";

const STYLE = `
  :host{
    --bg:#111; --card:#1c1c1c; --divider:#2a2a2a; --fg:#e1e1e1; --fg-dim:#9b9b9b;
    --accent:#03a9f4; --radius:12px;
    display:block; height:100vh; background:var(--bg); color:var(--fg);
    font-family:Roboto,-apple-system,"Segoe UI",sans-serif; font-size:14px;
  }
  *{box-sizing:border-box}
  .wrap{display:flex;gap:16px;padding:16px;height:100%}
  .side{width:320px;min-width:320px;display:flex;flex-direction:column;
        background:var(--card);border:1px solid var(--divider);border-radius:var(--radius)}
  .side header{padding:0 16px;height:48px;display:flex;align-items:center;justify-content:space-between;
               border-bottom:1px solid var(--divider);font-size:16px}
  .side header .btns{display:flex;gap:6px;align-items:center}
  .side .list{overflow:auto;padding:8px 0;flex:1}
  .grp{padding:10px 16px 4px;color:var(--fg-dim);font-size:11px;letter-spacing:.08em;text-transform:uppercase}
  .row{display:flex;align-items:center;gap:8px;padding:4px 16px;cursor:pointer;line-height:20px}
  .row:hover{background:#232323}
  .row input{accent-color:var(--accent);margin:0;cursor:pointer}
  .sw{width:14px;height:14px;border-radius:3px;flex:0 0 14px;opacity:.35}
  .row.on .sw{opacity:1}
  .row .nm{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .row.dim .nm{color:var(--fg-dim)}
  /* Σ filhos / (untracked): derivadas do pai, só selecionáveis com o pai selecionado. */
  .row.syn .nm{font-style:italic}
  .row.locked{opacity:.4;cursor:default}
  .row.locked:hover{background:none}
  .row.locked input{cursor:default}
  .main{flex:1;display:flex;flex-direction:column;gap:16px;min-width:0}
  .bar{background:var(--card);border:1px solid var(--divider);border-radius:var(--radius);
       padding:12px 16px;display:flex;align-items:center;gap:12px;flex-wrap:wrap}
  label.f{display:flex;align-items:center;gap:6px;color:var(--fg-dim)}
  input[type=date],select{background:#242424;color:var(--fg);border:1px solid var(--divider);
        border-radius:6px;padding:6px 8px;font-family:inherit;font-size:14px}
  .tgl{background:#242424;color:var(--fg-dim);border:1px solid var(--divider);border-radius:16px;
       padding:6px 14px;cursor:pointer;font-family:inherit;font-size:13px;user-select:none}
  .tgl.on{background:rgba(3,169,244,.18);border-color:var(--accent);color:#7fd4ff}
  .tgl:disabled{opacity:.4;cursor:default}
  .sep{width:1px;height:24px;background:var(--divider)}
  .nav{background:#242424;border:1px solid var(--divider);border-radius:8px;width:34px;height:32px;
       display:flex;align-items:center;justify-content:center;cursor:pointer;padding:0}
  .nav:hover:not(:disabled){border-color:var(--accent);background:rgba(3,169,244,.14)}
  .nav:disabled{opacity:.3;cursor:default}
  .tri{width:0;height:0;border-top:7px solid transparent;border-bottom:7px solid transparent}
  .tri.l{border-right:10px solid var(--fg)}
  .tri.r{border-left:10px solid var(--fg)}
  .chart-card{flex:1;background:var(--card);border:1px solid var(--divider);
              border-radius:var(--radius);display:flex;flex-direction:column;min-height:0}
  .chart-card .hd{height:48px;padding:0 16px;display:flex;align-items:center;justify-content:space-between;
                  border-bottom:1px solid var(--divider)}
  .chart-card .hd .t{font-size:16px}
  .chip{background:#242424;border:1px solid var(--divider);border-radius:14px;padding:3px 10px;
        color:var(--fg-dim);font-size:12px}
  #chart{flex:1;min-height:0}
  .msg{padding:10px 16px;color:var(--fg-dim);font-size:12px}
  .eqg{margin:8px 0 4px;display:flex;align-items:center;gap:8px;font-size:13px}
  .eqg i{width:12px;height:12px;border-radius:3px;display:inline-block}
  table.eq{width:100%;border-collapse:collapse;font-size:12px}
  table.eq th{color:var(--fg-dim);text-align:left;font-weight:400;padding:2px 8px 2px 0;
              border-bottom:1px solid var(--divider)}
  table.eq td{padding:2px 8px 2px 0;vertical-align:top;white-space:nowrap}
  table.eq td.f{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;white-space:normal}
  table.eq td.r2{color:var(--fg-dim)}
  .msg.err{color:#ff8a80}
  .scale{display:flex;align-items:center;gap:4px;color:var(--fg-dim);font-size:11px}
  .scale i{width:12px;height:12px;border-radius:2px;background:#8ea9ff;display:inline-block}
  #menu{display:none}
  :host([narrow]) #menu{display:block}
  :host([narrow]) .wrap{flex-direction:column;height:auto;min-height:100%}
  :host([narrow]) .side{width:auto;min-width:0;max-height:40vh}
  :host([narrow]) .chart-card{min-height:60vh}
`;

const TEMPLATE = `
<div class="wrap">
  <aside class="side">
    <header>
      <span>Entidades</span>
      <span class="btns">
        <button class="tgl" id="menu" title="menu">☰</button>
        <button class="tgl" id="none">Nenhuma</button>
      </span>
    </header>
    <div class="list" id="tree"></div>
  </aside>

  <div class="main">
    <div class="bar">
      <button class="nav" id="prev" title="um dia para trás"><i class="tri l"></i></button>
      <label class="f">De <input type="date" id="from"></label>
      <label class="f">Até <input type="date" id="to"></label>
      <button class="nav" id="next" title="um dia para a frente"><i class="tri r"></i></button>
      <button class="tgl" id="now" title="hoje, nas duas datas">Agora</button>
      <div class="sep"></div>
      <button class="tgl on" id="tPts">Pontos</button>
      <button class="tgl on" id="tCurve">Curva</button>
      <button class="tgl" id="tAvg">Média</button>
      <div class="sep"></div>
      <label class="f">Fonte <select id="source"></select></label>
      <label class="f">Valor
        <select id="mode">
          <option value="delta">delta (kWh no intervalo)</option>
          <option value="raw">bruto (odômetro)</option>
        </select>
      </label>
      <label class="f">Ajuste
        <select id="degree">
          <option value="auto">auto (grau 1–5)</option>
          <option value="1">grau 1</option>
          <option value="2">grau 2</option>
          <option value="3">grau 3</option>
          <option value="4">grau 4</option>
          <option value="5">grau 5</option>
          <option value="off">sem ajuste (poligonal)</option>
        </select>
      </label>
      <button class="tgl" id="tEq">Equações</button>
    </div>

    <div class="chart-card">
      <div class="hd">
        <span class="t">Perfil diário sobreposto</span>
        <span style="display:flex;gap:8px;align-items:center">
          <span class="scale" id="scale"></span>
          <span class="chip" id="chip">—</span>
        </span>
      </div>
      <div id="chart"></div>
      <div class="msg" id="msg"></div>
    </div>

    <div class="chart-card" id="eqCard" style="display:none;flex:0 0 260px">
      <div class="hd"><span class="t">Regressões por trecho</span>
        <span class="chip" id="eqChip">—</span></div>
      <div id="eqBody" style="overflow:auto;padding:8px 16px 12px"></div>
    </div>
  </div>
</div>
`;

/* ---------- cor + transparência por idade do dia ---------------------------------------- */
// Regra FIXA por idade do dia (0 = data mais recente da seleção): d 100%, d−1 80%,
// d−2 e d−3 50%, o resto 20%. Vale igual para pontos e para linhas.
const ALPHA = [1, 0.8, 0.6, 0.6];
const alphaFor = age => ALPHA[age] ?? 0.4;
function rgba(hex, a){
  const h = hex.replace('#',''); const n = parseInt(h,16);
  return `rgba(${(n>>16)&255},${(n>>8)&255},${n&255},${a})`;
}

function niceStep(x){
  const e = Math.floor(Math.log10(x)), f = x / Math.pow(10, e);
  return (f <= 1 ? 1 : f <= 2 ? 2 : f <= 5 ? 5 : 10) * Math.pow(10, e);
}

/* ---------- painel de equações: uma tabela por série, um bloco por trecho --------------- */
// Minuto do dia com marca de dia vizinho: as 3 h de contexto do ajuste caem em −180…0 e
// 1440…1620, e um trecho pode começar/terminar fora do dia exibido.
function hhmm(m){
  m = Math.round(m);
  const tag = m < 0 ? 'd−1 ' : (m >= 1440 ? 'd+1 ' : '');
  const t = ((m % 1440) + 1440) % 1440;
  return tag + String(Math.floor(t/60)).padStart(2,'0') + ':' + String(t%60).padStart(2,'0');
}
const DIR = {up:'subida', down:'descida', flat:'platô'};

function eqTable(segs){
  const rows = segs.map(g=>`<tr>
      <td>${hhmm(g.x0)}–${hhmm(g.x1)}</td>
      <td>${DIR[g.direction]||g.direction}</td>
      <td>${g.n}</td><td>${g.degree}</td>
      <td class="r2">${g.r2.toFixed(3)}</td>
      <td class="f">${g.equation}<span class="r2"> &nbsp;(${g.t})</span></td>
    </tr>`).join('');
  return `<table class="eq"><tr><th>intervalo</th><th>trecho</th><th>n</th><th>grau</th>
          <th>R²</th><th>equação</th></tr>${rows}</table>`;
}

/* ---------- eixo X: 1 dia, grade de 5 min, marca a cada 30 min, rótulo a cada hora ------ */
function xAxis(stepMin){
  return {
    type:'value', min:0, max:1440, interval:30,
    axisLine:{lineStyle:{color:'#3a3a3a'}},
    axisTick:{show:true, lineStyle:{color:'#4a4a4a'}},
    minorTick:{show:true, splitNumber: 30/stepMin, lineStyle:{color:'#333'}},
    splitLine:{show:true, lineStyle:{color:'#2b2b2b'}},
    minorSplitLine:{show:true, lineStyle:{color:'#1e1e1e'}},
    axisLabel:{color:'#9b9b9b', formatter: m => m % 60 ? '' : String(m/60).padStart(2,'0')+':00'},
  };
}

function shiftD(s, n){
  const d = new Date(s + 'T12:00:00');   // meio-dia: imune a fuso/horário de verão
  d.setDate(d.getDate() + n);
  return d.toISOString().slice(0,10);
}

function addMonths(iso, n){
  const [y, m, d] = iso.split('-').map(Number);
  const first = new Date(Date.UTC(y, m - 1 + n, 1));
  const last = new Date(Date.UTC(first.getUTCFullYear(), first.getUTCMonth() + 1, 0)).getUTCDate();
  return `${first.getUTCFullYear()}-${String(first.getUTCMonth()+1).padStart(2,'0')}-`
       + String(Math.min(d, last)).padStart(2,'0');
}

// Séries SINTÉTICAS de um nó com filhos (ver const.py). O id não é entity_id: é prefixo + o
// entity_id do pai.
const SUM_PREFIX = 'sum:', UNTRACKED_PREFIX = 'untracked:';
const parentOf = id => id.startsWith(SUM_PREFIX) ? id.slice(SUM_PREFIX.length)
                     : id.startsWith(UNTRACKED_PREFIX) ? id.slice(UNTRACKED_PREFIX.length) : null;

// Seleção + configuração de visualização sobrevivem a recarga/troca de tela. As DATAS não:
// guarda-se só a distância em dias entre elas, e ao abrir `Até` volta em hoje.
const LS_KEY = 'energy-analytics.view.v1';

const _SLACK = 0.08;   // folga mínima (fração do intervalo) para a curva não colar no limite

class EnergyAnalyticsPanel extends HTMLElement {
  constructor(){
    super();
    this.attachShadow({mode:'open'});
    this._booted = false;
    this._chart = null;
    this._dtTimer = null;
    this.NODES = []; this.COLOR = {}; this.LABEL = {}; this.SYN = {};
    this._rows = new Map();   // entity -> {row, cb} para acender/apagar as sintéticas do pai
    this.MAX_DAYS = 60; this.MIN_DATE = '2024-01-01'; this.MAX_DATE = null;
    this.YDEC = 2;
    this.state = {
      sel: new Set(),          // entity_id selecionados
      pts: true, curve: true,
      avgUser: null,           // null = segue o default (ligada com mais de 1 dia)
      data: null, seq: 0,
      y: {min:null, max:null, scale:true},   // escala travada
      yKey: null,                            // datas + entidades + modo que geraram `y`
      span: 0,                               // distância em dias entre `De` e `Até` (persistida)
    };
  }

  /* ---------- estado persistido --------------------------------------------------------- */
  // Só o que o usuário escolheu; nada de dado nem de datas absolutas. Falha de localStorage
  // (modo privativo, quota) não pode derrubar o painel — daí o try/catch dos dois lados.
  saveView(){
    try{
      localStorage.setItem(LS_KEY, JSON.stringify({
        sel: [...this.state.sel], pts: this.state.pts, curve: this.state.curve,
        avgUser: this.state.avgUser, span: this.state.span,
        source: this.$('source').value, mode: this.$('mode').value, degree: this.$('degree').value,
        eq: this.$('eqCard').style.display !== 'none',
      }));
    }catch(e){ /* sem persistência é degradação aceitável */ }
  }

  readView(){
    try{ return JSON.parse(localStorage.getItem(LS_KEY)) || null; }catch(e){ return null; }
  }

  // `set hass` dispara a CADA mudança de estado do HA (dezenas por segundo nesta casa).
  // Só guarda a referência: qualquer render aqui derruba o painel.
  set hass(hass){ this._hass = hass; }
  get hass(){ return this._hass; }

  set narrow(v){ this.toggleAttribute('narrow', !!v); if (this._chart) this._chart.resize(); }

  connectedCallback(){
    if (this._booted) return;
    this._booted = true;
    this.shadowRoot.innerHTML = `<style>${STYLE}</style>${TEMPLATE}`;
    this._chart = echarts.init(this.$('chart'), null, {renderer:'canvas'});
    this._ro = new ResizeObserver(() => this._chart.resize());
    this._ro.observe(this.$('chart'));
    this._wire();
    this._init();
  }

  disconnectedCallback(){
    if (this._ro) this._ro.disconnect();
    if (this._chart) this._chart.dispose();
    this._chart = null;
    this._booted = false;
  }

  $(id){ return this.shadowRoot.getElementById(id); }

  _ws(type, extra){
    return this._hass.callWS({type: 'energy_analytics/' + type, ...(extra||{})});
  }

  /* ---------- árvore -------------------------------------------------------------------- */
  // Classe da linha em um lugar só: `renderTree` e `syncSynthetic` têm que concordar.
  rowClass(n, checked, locked){
    return 'row' + (n.synthetic ? ' syn' : '') + (checked ? ' on' : ' dim') + (locked ? ' locked' : '');
  }

  // Σ filhos e (untracked) são derivadas: sem o pai selecionado elas não têm o que derivar.
  // Desmarcar o pai desmarca e trava as duas. Mexe SÓ nas duas linhas — re-renderizar a árvore
  // aqui trocaria o input sob o <label> e o clique voltaria desmarcado (invariante 9).
  syncSynthetic(parent){
    const on = this.state.sel.has(parent);
    for (const id of [SUM_PREFIX + parent, UNTRACKED_PREFIX + parent]){
      const r = this._rows.get(id);
      if (!r) continue;
      if (!on){ this.state.sel.delete(id); r.cb.checked = false; }
      r.cb.disabled = !on;
      r.row.className = this.rowClass(r.node, r.cb.checked, !on);
    }
  }

  renderTree(){
    const box = this.$('tree'); box.innerHTML = '';
    this._rows.clear();
    let group = null;
    for (const n of this.NODES){
      if (n.group !== group){
        group = n.group;
        const h = document.createElement('div');
        h.className = 'grp'; h.textContent = group === 'source' ? 'Fontes' : 'Dispositivos';
        box.appendChild(h);
      }
      const locked = !!n.synthetic && !this.state.sel.has(n.parent);
      if (locked) this.state.sel.delete(n.entity);      // pai desmarcado: derivada não sobrevive
      const row = document.createElement('label');
      row.className = this.rowClass(n, this.state.sel.has(n.entity), locked);
      row.style.paddingLeft = (16 + n.depth * 18) + 'px';
      row.title = n.synthetic === 'sum' ? `soma dos filhos diretos de ${n.parent}`
                : n.synthetic === 'untracked' ? `${n.parent} − soma dos filhos diretos`
                : n.entity;
      const cb = document.createElement('input');
      cb.type = 'checkbox'; cb.checked = this.state.sel.has(n.entity); cb.disabled = locked;
      // Só a classe da própria linha muda aqui: re-renderizar a árvore DENTRO do dispatch do
      // clique troca o input sob o <label>, e o label re-dispara o toggle (desmarca de volta).
      cb.onchange = () => {
        cb.checked ? this.state.sel.add(n.entity) : this.state.sel.delete(n.entity);
        row.className = this.rowClass(n, cb.checked, false);
        if (n.children) this.syncSynthetic(n.entity);
        this.saveView();
        this.load();
      };
      this._rows.set(n.entity, {row, cb, node: n});
      const sw = document.createElement('span');
      sw.className = 'sw'; sw.style.background = n.color;
      const nm = document.createElement('span');
      nm.className = 'nm'; nm.textContent = n.label;
      row.append(cb, sw, nm);
      box.appendChild(row);
    }
  }

  /* ---------- escala vertical: TRAVADA, com dois regimes -------------------------------- */
  // A régua não pode mexer ao ligar/desligar Curva ou Média, nem ao trocar de fonte
  // (states ↔ statistics) ou de grau — comparar dois desenhos exige a mesma régua. Ela é
  // memorizada numa chave = datas + entidades + modo do valor + estado do botão Pontos:
  //   • Pontos LIGADOS  → régua sobre os pontos MANTIDOS + média (a nuvem é o que se lê);
  //   • Pontos DESLIGADOS → régua sobre as CURVAS (dias + média), com folga nas duas pontas,
  //     independentemente de Curva/Média estarem visíveis — sem a nuvem, o ajuste ocupa a tela.
  // O modo entra na chave porque `delta` (0…0,6 kWh) e `bruto` (odômetro, 1386 kWh) são
  // grandezas de ordem diferente: manter a régua do delta jogaria o odômetro para fora da tela.
  computeY(d, withPoints){
    let lo = Infinity, hi = -Infinity;
    const scan = (arr, skip) => { for (const p of (arr||[])){ const v = p[1];
      if (v == null || !isFinite(v)) continue;
      if (p[0] < 0 || p[0] > 1440) continue;     // contexto de 3 h fora do dia: não mede a régua
      if (skip && skip.has(p[0])) continue;      // ponto fora do ajuste: não manda na régua
      if (v < lo) lo = v; if (v > hi) hi = v; } };

    if (withPoints){
      // Curva do DIA fica fora: seu envelope é o do próprio trecho, que contém o ponto
      // descartado — deixá-la entrar traria de volta, pela porta dos fundos, o excluído.
      for (const s of d.series) scan(s.points, new Set(s.dropped || []));
      for (const m of d.means){ scan(m.points); scan(m.curve); }
    } else {
      for (const s of d.series) scan(s.curve);
      for (const m of d.means) scan(m.curve);
    }
    if (!isFinite(lo)) return {min:null, max:null, scale:true, dec:2};

    const vlo = lo, vhi = hi;                    // extremos crus do que foi varrido
    const span0 = hi - lo || Math.abs(hi) || 1;
    if (!withPoints){
      // Sem a nuvem, a régua é das curvas: folga nas DUAS pontas para nenhuma delas colar
      // no limite (inclusive a que repousa exatamente no zero, como o solar de madrugada).
      lo -= span0 * _SLACK;
      hi += span0 * _SLACK;
    } else {
      // Ruído negativo (delta de `sum` da ordem de −0,001) NÃO abre o eixo para baixo: com o
      // passo "redondo" de uma série que vai a 7 kWh, um −0,001 viraria mínimo −2.
      if (lo >= 0) lo = lo <= span0 * 0.25 ? 0 : lo - span0 * 0.05;
      else if (lo >= -0.05 * span0) lo = 0;
      else lo -= span0 * 0.05;
      hi += span0 * 0.05;
    }

    // Passo mais fino sem a nuvem: arredondar em passo grosso engolia a folga toda numa ponta
    // (curvas em −0,019…0,545 caíam num eixo −0,2…0,6, com 32 % de vazio embaixo).
    const step = niceStep((hi - lo || 1) / (withPoints ? 5 : 8));
    lo = Math.floor(lo / step) * step;
    hi = Math.ceil(hi / step) * step;
    if (!withPoints){                            // o arredondamento pode ter comido a folga
      const need = (vhi - vlo || Math.abs(vhi) || 1) * _SLACK;
      while (vlo - lo < need) lo -= step;
      while (hi - vhi < need) hi += step;
    }
    const span = hi - lo;
    return {min:+lo.toFixed(6), max:+hi.toFixed(6), scale:false,
            dec: span >= 10 ? 1 : span >= 1 ? 2 : span >= 0.1 ? 3 : 4};
  }

  yKeyOf(){
    return [this.$('from').value, this.$('to').value, this.$('mode').value,
            this.state.pts ? 'pts' : 'sem-pts',
            [...this.state.sel].sort().join('+')].join('|');
  }

  ensureY(d){
    const key = this.yKeyOf();
    if (key === this.state.yKey) return;
    const y = this.computeY(d, this.state.pts);
    this.state.y = {min:y.min, max:y.max, scale:y.scale};
    this.YDEC = y.dec;
    this.state.yKey = key;
  }

  fmtY(v){ return Number(v.toFixed(this.YDEC)).toString(); }

  renderEq(d, avgOn){
    const body = this.$('eqBody');
    if (this.$('eqCard').style.display === 'none') return;
    if (d.degree === 'off'){
      body.innerHTML = '<div class="msg">Ajuste desligado — a linha é a poligonal dos pontos.</div>';
      this.$('eqChip').textContent = '—'; return;
    }
    const blocks = [];
    if (avgOn) for (const m of d.means)
      blocks.push([`Média · ${this.LABEL[m.entity]} (${m.days} dia(s))`, this.COLOR[m.entity], m.segments]);
    for (const s of d.series)
      blocks.push([`${this.LABEL[s.entity]} · ${s.day}`, this.COLOR[s.entity], s.segments]);

    const shown = blocks.slice(0, 30);
    body.innerHTML = shown.map(([t,c,segs]) =>
        `<div class="eqg"><i style="background:${c}"></i>${t}</div>` +
        (segs.length ? eqTable(segs) : '<div class="msg">pontos insuficientes</div>')).join('')
      + (blocks.length > shown.length
          ? `<div class="msg">… e mais ${blocks.length - shown.length} série(s) — reduza a seleção.</div>` : '');
    const nseg = blocks.reduce((a,b)=>a+b[2].length,0);
    this.$('eqChip').textContent = `${blocks.length} série(s) · ${nseg} trecho(s)`;
  }

  build(){
    const d = this.state.data;
    if (!d){ this._chart.clear(); return; }
    this.ensureY(d);
    const days = [...new Set(d.series.map(s=>s.day))].sort().reverse();  // recente -> antigo
    const age = Object.fromEntries(days.map((day,i)=>[day,i]));
    const multi = days.length > 1;
    const avgOn = this.state.avgUser === null ? multi : this.state.avgUser;
    this.$('tAvg').classList.toggle('on', avgOn);

    // Pontos e curva são séries SEPARADAS: os pontos são o dado observado, a curva é a regressão
    // (`s.curve`, vinda do backend) — ela NÃO passa pelos pontos.
    const series = [];
    for (const s of d.series){
      const a = alphaFor(age[s.day]), c = this.COLOR[s.entity] || '#888';
      const nm = this.LABEL[s.entity] + ' · ' + s.day;
      const drop = new Set(s.dropped || []);
      if (this.state.pts){
        series.push({
          name: nm, type:'scatter', data: drop.size ? s.points.filter(p=>!drop.has(p[0])) : s.points,
          symbolSize: 4, itemStyle:{color: rgba(c, a)},
          emphasis:{disabled:true}, animation:false, z:2,
        });
        if (drop.size) series.push({     // descartados da média: anel vazado, fora da régua
          name: nm + ' (descartado)', type:'scatter', symbol:'emptyCircle', symbolSize: 5,
          data: s.points.filter(p=>drop.has(p[0])),
          itemStyle:{color:'transparent', borderColor: rgba(c, a), borderWidth:1},
          emphasis:{disabled:true}, animation:false, z:2,
        });
      }
      if (this.state.curve) series.push({
        name: (d.degree === 'off' ? nm : 'Ajuste · ' + nm), type:'line', data: s.curve,
        showSymbol:false, itemStyle:{color: rgba(c, a)},
        // `Σ filhos` herda a cor do pai: sem o tracejado as duas linhas seriam indistinguíveis.
        lineStyle:{color: rgba(c, a), width:1.4, type: this.SYN[s.entity]==='sum' ? 'dashed':'solid'},
        emphasis:{disabled:true}, animation:false, z:3, silent: this.state.pts,
      });
    }
    // A média é SEMPRE a sua própria regressão (`m.curve`). Ligar/desligar `Curva` é escolha de
    // aparência das séries do DIA — não pode trocar o dado que a média desenha.
    if (avgOn) for (const m of d.means){
      const c = this.COLOR[m.entity] || '#888';
      series.push({
        name:'Média · ' + this.LABEL[m.entity], type:'line', data: m.curve,
        showSymbol:false, itemStyle:{color:c},
        lineStyle:{color:c, width:3.2, type: this.SYN[m.entity]==='sum' ? 'dashed':'solid'},
        emphasis:{disabled:true}, animation:false, z:10,
      });
    }

    // Δ (pai, Σfilhos) do tooltip: é a mesma conta do `(untracked)`, mostrada mesmo quando
    // aquela linha não está ligada — quem ligou a Σ quer saber o que sobrou do pai.
    const deltas = [];
    for (const id of this.state.sel){
      if (!id.startsWith(SUM_PREFIX)) continue;
      const parent = parentOf(id);
      if (!this.state.sel.has(parent)) continue;
      for (const day of days){
        const ps = d.series.find(s => s.entity === parent && s.day === day);
        const ss = d.series.find(s => s.entity === id && s.day === day);
        if (!ps || !ss) continue;
        const sum = new Map(ss.points), map = new Map();
        for (const [m, v] of ps.points){
          const o = sum.get(m);
          if (o != null) map.set(m, v - o);
        }
        deltas.push({label: `Δ (${this.LABEL[parent]}, Σ filhos)`
                            + (multi ? ' · ' + day : ''), color: this.COLOR[parent] || '#888', map});
      }
    }

    this._chart.setOption({
      backgroundColor:'transparent',
      grid:{left:64, right:24, top:24, bottom:40},
      textStyle:{fontFamily:'Roboto, sans-serif'},
      tooltip:{
        trigger:'axis', axisPointer:{type:'line', lineStyle:{color:'#555'}},
        backgroundColor:'#1c1c1c', borderColor:'#2a2a2a', textStyle:{color:'#e1e1e1', fontSize:12},
        confine:true, order:'valueDesc',
        formatter: p => {
          if (!p.length) return '';
          const m = p[0].axisValue|0;
          const hh = String(Math.floor(m/60)).padStart(2,'0'), mm = String(m%60).padStart(2,'0');
          const line = (mark, name, val) =>
            `<div style="display:flex;gap:8px;justify-content:space-between">
               <span>${mark}${name}</span><b>${(+val).toFixed(4)} ${d.unit}</b></div>`;
          const rows = p.filter(x=>x.data && x.data[1]!=null).slice(0,24)
            .map(x=>line(x.marker, x.seriesName, x.data[1])).join('');
          // Δ vai SEMPRE por último, depois de um filete separando do que é série desenhada.
          const dl = deltas.filter(g => g.map.has(m)).map(g => line(
            `<span style="display:inline-block;width:10px;height:0;border-top:2px dashed ${g.color};`
            + `vertical-align:middle;margin-right:5px"></span>`, g.label, g.map.get(m))).join('');
          return `<div style="margin-bottom:4px">${hh}:${mm}</div>${rows}`
               + (dl ? `<div style="margin-top:4px;padding-top:4px;border-top:1px solid #2a2a2a">${dl}</div>` : '');
        },
      },
      xAxis: xAxis(d.step_min),
      yAxis:{
        type:'value', name: d.unit, nameTextStyle:{color:'#9b9b9b'}, nameRotate:0,
        nameLocation:'end', nameGap:12,
        // `min`/`max` explícitos SEMPRE (null = automático): o setOption faz merge e um limite de
        // uma seleção anterior sobreviveria à troca de escala.
        min: this.state.y.min, max: this.state.y.max, scale: this.state.y.scale,
        axisLabel:{color:'#9b9b9b', formatter: v => this.fmtY(v)},
        splitLine:{lineStyle:{color:'#242424'}},
      },
      series,
    }, {replaceMerge:['series']});

    this.renderEq(d, avgOn);
    const npts = d.series.reduce((a,s)=>a+s.points.length,0);
    this.$('chip').textContent = `${d.series.length} séries · ${days.length} dia(s) · ${npts} pontos`;
    this.$('scale').innerHTML = multi
      ? `<span>opacidade</span><i style="opacity:1" title="d"></i><i style="opacity:.8" title="d−1"></i>`
        + `<i style="opacity:.6" title="d−2 / d−3"></i><i style="opacity:.4" title="d−4 ou mais"></i>`
        + `<span>d → d−4+</span>`
      : '';
    const miss = d.missing.length ? ` · sem metadata: ${d.missing.join(', ')}` : '';
    const drp = d.dropped_total
      ? ` · ${d.dropped_total} ponto(s) fora do ajuste (anel vazado; fora da escala, dentro da média)`
      : '';
    this.$('msg').className = 'msg';
    this.$('msg').textContent = this.state.sel.size
      ? `fonte ${d.source} · bucket ${d.step_min} min · ${d.mode}${drp}${miss}`
      : 'Selecione uma ou mais entidades à esquerda.';
  }

  /* ---------- carga --------------------------------------------------------------------- */
  async load(){
    const f = this.$('from').value, t = this.$('to').value;
    if (!f || !t) return;
    if (!this.state.sel.size){ this.state.data = null; this._chart.clear();
                               this.$('chip').textContent='—';
                               this.$('msg').className='msg';
                               this.$('msg').textContent='Selecione uma ou mais entidades à esquerda.'; return; }
    const seq = ++this.state.seq;
    this.$('msg').className = 'msg'; this.$('msg').textContent = 'carregando…';
    try{
      const j = await this._ws('series', {
        from: f, to: t, entities: [...this.state.sel],
        source: this.$('source').value, mode: this.$('mode').value,
        degree: this.$('degree').value,
      });
      if (seq !== this.state.seq) return;              // resposta obsoleta
      this.state.data = j;
      this.build();     // `ensureY` decide se a régua muda (só data/entidade/modo/Pontos)
    }catch(e){
      if (seq !== this.state.seq) return;
      this.$('msg').className='msg err';
      this.$('msg').textContent = (e && (e.message || e.error)) || String(e);
    }
  }

  /* ---------- eventos ------------------------------------------------------------------- */
  daysBetween(){
    const a = new Date(this.$('from').value), b = new Date(this.$('to').value);
    return Math.abs(Math.round((b-a)/86400000)) + 1;
  }

  clampD(s){ return s < this.MIN_DATE ? this.MIN_DATE : (s > this.MAX_DATE ? this.MAX_DATE : s); }

  // Passos de data podem vir em rajada (segurar a seta do teclado): recarrega uma vez só, no fim.
  // Nada de `build()` aqui — ele recalcularia a régua com o payload VELHO sob a chave nova, e a
  // régua ficaria congelada errada quando o payload certo chegasse.
  datesChanged(now){
    if (this.daysBetween() > this.MAX_DAYS){
      this.$('msg').className='msg err';
      this.$('msg').textContent =
        `intervalo de ${this.daysBetween()} dias excede o limite de ${this.MAX_DAYS}`;
    }
    this.$('prev').disabled = this.$('from').value <= this.MIN_DATE;
    this.$('next').disabled = this.$('to').value >= this.MAX_DATE;
    // Persiste a DISTÂNCIA, nunca as datas: ao reabrir, `Até` volta em hoje e `De` recua isso.
    this.state.span = this.daysBetween() - 1;
    this.saveView();
    clearTimeout(this._dtTimer);
    if (now) this.load(); else this._dtTimer = setTimeout(() => this.load(), 250);
  }

  // Setas: deslocam as DUAS datas 1 dia, preservando o intervalo; travam na borda da janela.
  step(n){
    const fv = this.$('from').value, tv = this.$('to').value;
    if (!fv || !tv) return;   // campo vazio = digitação em andamento (invariante 8b): não deslocar
    const f = shiftD(fv, n), t = shiftD(tv, n);
    if (t > this.MAX_DATE || f < this.MIN_DATE) return;
    this.$('from').value = f; this.$('to').value = t;
    this.datesChanged(true);
  }

  /* ---------- rolagem contínua dia → mês → ano nos campos de data ------------------------ */
  // O `input[type=date]` nativo gira o dia DENTRO do mês (31 ↑ vira 01 no mesmo mês) e o mês
  // dentro do ano. Aqui o estouro de um segmento leva o seguinte junto: 31/07 ↑ = 01/08,
  // 01/01 ↓ = 31/12 do ano anterior. Detectamos pelo salto (o valor nativo já foi aplicado) e
  // reescrevemos a data como prev ± 1 dia (ou ± 1 mês, se o segmento mexido foi o do mês).
  rollover(inp){
    const prev = inp.dataset.prev, dir = +(inp.dataset.dir || 0);
    inp.dataset.prev = ''; inp.dataset.dir = '';
    if (!prev || !dir || !inp.value) return;
    const [py, pm, pd] = prev.split('-').map(Number);
    const [ny, nm, nd] = inp.value.split('-').map(Number);
    // Ano: o próprio Chrome dá a volta dentro de [min, max] (2026 ↑ = 2024). Na borda da janela
    // o passo não deve teleportar para a outra ponta — fica onde está.
    if (ny !== py){
      if (Math.sign(ny - py) !== dir) inp.value = prev;
      return;
    }
    if (nm === pm && nd !== pd && Math.sign(nd - pd) !== dir) inp.value = shiftD(prev, dir);
    else if (nm !== pm && nd === pd && Math.sign(nm - pm) !== dir) inp.value = addMonths(prev, dir);
  }

  _wire(){
    // Ao mexer numa ponta, a outra ACOMPANHA se a ordem quebrar (De ≤ Até), sempre dentro da
    // janela. Campo vazio = digitação em andamento (o input nativo só entrega valor com todos os
    // segmentos preenchidos): não completar com "hoje" no meio da digitação.
    this.$('from').onchange = () => {
      if (!this.$('from').value) return;
      const f = this.clampD(this.$('from').value);
      this.$('from').value = f;
      if (this.$('to').value < f) this.$('to').value = f;
      this.datesChanged();
    };
    this.$('to').onchange = () => {
      if (!this.$('to').value) return;
      const t = this.clampD(this.$('to').value);
      this.$('to').value = t;
      if (this.$('from').value > t) this.$('from').value = t;
      this.datesChanged();
    };
    this.$('prev').onclick = () => this.step(-1);
    this.$('next').onclick = () => this.step(+1);
    this.$('now').onclick  = () => { this.$('from').value = this.MAX_DATE;
                                     this.$('to').value = this.MAX_DATE;
                                     this.datesChanged(true); };

    for (const id of ['from','to']){
      const inp = this.$(id);
      inp.addEventListener('keydown', e => {
        if (e.key === 'ArrowUp' || e.key === 'ArrowDown'){
          inp.dataset.prev = inp.value;
          inp.dataset.dir = e.key === 'ArrowUp' ? '1' : '-1';
        }
      });
      inp.addEventListener('input', () => {
        this.rollover(inp);
        if (inp.value) inp.dispatchEvent(new Event('change'));
      });
    }

    const reload = () => { this.saveView(); this.load(); };
    this.$('source').onchange = reload;
    this.$('mode').onchange = reload;
    this.$('degree').onchange = reload;

    this.$('tEq').onclick = e => {
      const card = this.$('eqCard'), on = card.style.display === 'none';
      card.style.display = on ? 'flex' : 'none';
      e.currentTarget.classList.toggle('on', on);
      this._chart.resize();
      if (on && this.state.data) this.build();
      this.saveView();
    };
    this.$('tPts').onclick   = e => { this.state.pts = !this.state.pts;
                                      e.currentTarget.classList.toggle('on', this.state.pts);
                                      this.saveView(); this.build(); };
    this.$('tCurve').onclick = e => { this.state.curve = !this.state.curve;
                                      e.currentTarget.classList.toggle('on', this.state.curve);
                                      this.saveView(); this.build(); };
    this.$('tAvg').onclick   = () => { const cur = this.state.avgUser === null
                                         ? this.daysBetween() > 1 : this.state.avgUser;
                                       this.state.avgUser = !cur; this.saveView(); this.build(); };
    this.$('none').onclick   = () => { this.state.sel.clear(); this.renderTree();
                                       this.saveView(); this.load(); };
    this.$('menu').onclick   = () => this.dispatchEvent(
      new Event('hass-toggle-menu', {bubbles:true, composed:true}));
  }

  async _init(){
    let j;
    try{
      j = await this._ws('tree');
    }catch(e){
      this.$('msg').className = 'msg err';
      this.$('msg').textContent = (e && (e.message || e.error)) || String(e);
      return;
    }
    this.NODES = j.nodes;
    this.MAX_DAYS = j.max_days;
    this.MIN_DATE = j.min_date;
    this.MAX_DATE = j.today;          // "hoje" do SERVIDOR (fuso do HA), não do navegador
    for (const n of this.NODES){
      this.COLOR[n.entity] = n.color; this.LABEL[n.entity] = n.label;
      if (n.synthetic) this.SYN[n.entity] = n.synthetic;
    }
    const sel = this.$('source');
    for (const s of j.sources){
      const o = document.createElement('option');
      o.value = s.key; o.textContent = s.label; o.disabled = !s.enabled;
      sel.appendChild(o);
    }

    // ---- última configuração ----------------------------------------------------------
    // A seleção salva é filtrada contra a árvore ATUAL: mexer no painel de Energia pode ter
    // aposentado uma entidade, e pedir série de algo que não existe mais só gera erro.
    const v = this.readView() || {};
    const known = new Set(this.NODES.map(n => n.entity));
    for (const id of (v.sel || [])){
      if (!known.has(id)) continue;
      const p = parentOf(id);
      if (p && !(v.sel || []).includes(p)) continue;   // derivada sem o pai não se sustenta
      this.state.sel.add(id);
    }
    if (typeof v.pts === 'boolean') this.state.pts = v.pts;
    if (typeof v.curve === 'boolean') this.state.curve = v.curve;
    if (v.avgUser === true || v.avgUser === false) this.state.avgUser = v.avgUser;
    for (const [id, val] of [['source', v.source], ['mode', v.mode], ['degree', v.degree]]){
      if (val && [...this.$(id).options].some(o => o.value === val && !o.disabled)) {
        this.$(id).value = val;
      }
    }
    this.$('tPts').classList.toggle('on', this.state.pts);
    this.$('tCurve').classList.toggle('on', this.state.curve);
    if (v.eq){ this.$('eqCard').style.display = 'flex'; this.$('tEq').classList.add('on'); }

    this.renderTree();

    // `Até` SEMPRE em hoje; `De` recua a distância salva, presa ao piso e ao teto da janela.
    const span = Math.max(0, Math.min(this.MAX_DAYS - 1, Math.round(+v.span || 0)));
    this.state.span = span;
    for (const id of ['from','to']){
      this.$(id).min = this.MIN_DATE;
      this.$(id).max = this.MAX_DATE;
    }
    this.$('to').value = this.MAX_DATE;
    this.$('from').value = this.clampD(shiftD(this.MAX_DATE, -span));
    this.$('prev').disabled = this.$('from').value <= this.MIN_DATE;
    this.$('next').disabled = this.$('to').value >= this.MAX_DATE;
    this.$('tAvg').classList.toggle('on', this.state.avgUser === null
                                         ? this.daysBetween() > 1 : this.state.avgUser);
    this.$('msg').textContent = 'Selecione uma ou mais entidades à esquerda.';
    if (this.state.sel.size) this.load();
  }
}

customElements.define('energy-analytics-panel', EnergyAnalyticsPanel);
