"""Leitura de `states` / `statistics_short_term` / `statistics` e bucketizacao 24h.

Modelo: as entidades do Energy Dashboard sao ODOMETROS (kWh acumulado, `total_increasing`).
Por isso ha dois modos:

- `delta` (default) — energia consumida NO bucket = valor do bucket menos o do bucket anterior.
  E a unica leitura que faz sentido sobrepor dia a dia (o cru cresce por centenas de kWh entre
  dias, as curvas nunca cairiam no mesmo eixo) e a unica sobre a qual a media tem significado.
  Fonte `statistics*`: delta da coluna `sum` (odometro canonico, imune a reset), SEM clamp —
  export/carga sao legitimamente negativos. Fonte `states`: delta do proprio `state`, com clamp
  em 0 (reset do contador viraria um negativo enorme).
- `raw` — o valor lido, sem derivar. Util para 1 dia / inspecao do odometro.

Ancoragem: o `lag` do primeiro bucket vem da ULTIMA amostra ANTES da janela (lookback de 1 dia),
senao o primeiro bucket de cada janela perde o delta.

Divisao de trabalho: o SQL roda no executor DO RECORDER (`recorder_db.query`); a montagem +
regressao (`_assemble`, centenas a milhares de ajustes) roda no executor GERAL. Nunca juntar os
dois — o fit dentro do executor do recorder segura a gravacao de estados do HA inteiro.
"""
from __future__ import annotations

import datetime as dt
import math
from zoneinfo import ZoneInfo

from homeassistant.core import HomeAssistant

from . import const, fit, recorder_db
from .energy_tree import EnergyTree

SOURCES = {
    # chave -> (tabela, passo em segundos, rotulo)
    "states": (const.TBL_STATES, 300, "states (5 min)"),
    "short_term": (const.TBL_STATISTICS_SHORT_TERM, 300, "statistics_short_term (5 min)"),
    "statistics": (const.TBL_STATISTICS, 3600, "statistics (1 h)"),
}

_NUMERIC = r"^-?[0-9]+(\.[0-9]+)?$"
_LOOKBACK = 86400  # ancora do lag: 1 dia antes da janela

# Contexto do ajuste: 3 HORAS COM DADO antes e depois de cada dia (nao um recorte fixo de
# relogio) — a busca anda para tras/para a frente ate' juntar 3 horas distintas com amostra.
# So' alimenta a REGRESSAO: nao vira ponto desenhado, nao entra na escala, nao muda o eixo X.
EXT_HOURS = 3
EXT_SEARCH_SEC = 12 * 3600   # ate' onde procurar essas horas


def source_options():
    return [{"key": k, "label": lab, "step_min": step // 60, "enabled": bool(tbl)}
            for k, (tbl, step, lab) in SOURCES.items()]


def _with_context(pts):
    """Mantem o dia inteiro + EXT_HOURS horas COM DADO de cada lado.

    "3 horas" nao e' um recorte de relogio: anda-se para fora somando HORAS DISTINTAS que
    tenham amostra, ate' juntar `EXT_HOURS` de cada lado (ou acabar a area de busca). Assim
    uma entidade que so' grava de manha ainda ganha contexto — vem de onde houver dado.
    """
    keep = {x: v for x, v in pts.items() if 0 <= x < 1440}
    for side in (-1, 1):
        cand = sorted((x for x in pts if (x < 0 if side < 0 else x >= 1440)),
                      reverse=(side < 0))
        hours = set()
        for x in cand:
            h = x // 60
            if h not in hours:
                if len(hours) >= EXT_HOURS:
                    break
                hours.add(h)
            keep[x] = pts[x]
    return keep


def _epoch(day, tz):
    return dt.datetime.combine(day, dt.time(0, 0), tz).timestamp()


async def _meta_ids(hass: HomeAssistant, entities, source):
    """entity_id -> metadata_id (states_meta ou statistics_meta, conforme a fonte)."""
    if source == "states":
        sql = (f"SELECT entity_id, metadata_id FROM {const.TBL_STATES_META} "
               "WHERE entity_id IN :ents")
    else:
        sql = (f"SELECT statistic_id, id FROM {const.TBL_STATISTICS_META} "
               "WHERE statistic_id IN :ents")
    rows = await recorder_db.query(hass, sql, {"ents": list(entities)}, expanding=("ents",))
    return {r[0]: r[1] for r in rows}


async def _rows_states(hass: HomeAssistant, ids, lo, hi, step):
    sql = f"""
    WITH raw AS (
        SELECT s.metadata_id AS mid, s.last_updated_ts AS ts,
               CAST(s.state AS double precision) AS v
          FROM {const.TBL_STATES} s
         WHERE s.metadata_id IN :ids
           AND s.last_updated_ts >= :lo AND s.last_updated_ts < :hi
           AND s.state ~ :num
        UNION ALL
        SELECT a.mid, a.ts, a.v FROM (
            SELECT DISTINCT ON (s.metadata_id)
                   s.metadata_id AS mid, s.last_updated_ts AS ts,
                   CAST(s.state AS double precision) AS v
              FROM {const.TBL_STATES} s
             WHERE s.metadata_id IN :ids
               AND s.last_updated_ts < :lo AND s.last_updated_ts >= :back
               AND s.state ~ :num
             ORDER BY s.metadata_id, s.last_updated_ts DESC
        ) a
    ), bucketed AS (
        SELECT mid, CAST(floor((ts - :lo) / :step) AS bigint) AS bk, ts, v FROM raw
    ), last_of_bucket AS (
        SELECT DISTINCT ON (mid, bk) mid, bk, v
          FROM bucketed ORDER BY mid, bk, ts DESC
    )
    SELECT mid, bk, v, v - lag(v) OVER (PARTITION BY mid ORDER BY bk) AS d
      FROM last_of_bucket ORDER BY mid, bk
    """
    return await recorder_db.query(
        hass, sql,
        {"ids": ids, "lo": lo, "hi": hi, "back": lo - _LOOKBACK, "step": step, "num": _NUMERIC},
        expanding=("ids",))


async def _rows_stats(hass: HomeAssistant, table, ids, lo, hi, step):
    sql = f"""
    WITH raw AS (
        SELECT st.metadata_id AS mid, st.start_ts AS ts,
               CAST(st.state AS double precision) AS v,
               CAST(st.sum AS double precision) AS acc
          FROM {table} st
         WHERE st.metadata_id IN :ids
           AND st.start_ts >= :lo AND st.start_ts < :hi
        UNION ALL
        SELECT a.mid, a.ts, a.v, a.acc FROM (
            SELECT DISTINCT ON (st.metadata_id)
                   st.metadata_id AS mid, st.start_ts AS ts,
                   CAST(st.state AS double precision) AS v,
                   CAST(st.sum AS double precision) AS acc
              FROM {table} st
             WHERE st.metadata_id IN :ids
               AND st.start_ts < :lo AND st.start_ts >= :back
             ORDER BY st.metadata_id, st.start_ts DESC
        ) a
    ), bucketed AS (
        SELECT mid, CAST(floor((ts - :lo) / :step) AS bigint) AS bk, ts, v, acc FROM raw
    ), last_of_bucket AS (
        SELECT DISTINCT ON (mid, bk) mid, bk, v, acc
          FROM bucketed ORDER BY mid, bk, ts DESC
    )
    SELECT mid, bk, v, acc - lag(acc) OVER (PARTITION BY mid ORDER BY bk) AS d
      FROM last_of_bucket ORDER BY mid, bk
    """
    return await recorder_db.query(
        hass, sql,
        {"ids": ids, "lo": lo, "hi": hi, "back": lo - _LOOKBACK, "step": step},
        expanding=("ids",))


def _parse_selection(entities, tree):
    """Separa o pedido em reais x sinteticas e diz o que a CONSULTA precisa buscar.

    Sintetica e' `sum:<pai>` (soma dos filhos DIRETOS) ou `untracked:<pai>` (pai - essa soma).
    O pai e os filhos entram na consulta mesmo sem estarem selecionados — eles alimentam a
    conta, mas so' viram serie desenhada se o usuario tiver pedido.

    Devolve (pedidas, necessarias, {id_sintetico: (pai, filhos)}), sem repetir e na ordem.
    """
    requested, need, kids = [], [], {}
    for e in entities:
        if e in tree.ALL_ENTITIES:
            requested.append(e)
            need.append(e)
            continue
        for prefix in (const.SUM_PREFIX, const.UNTRACKED_PREFIX):
            if not e.startswith(prefix):
                continue
            parent = e[len(prefix):]
            children = list(tree.CHILDREN.get(parent, []))
            if not children or parent not in tree.ALL_ENTITIES:
                break                      # no sem filhos nao tem soma nem sobra
            requested.append(e)
            kids[e] = (parent, children)
            need.extend(children)
            if prefix == const.UNTRACKED_PREFIX:
                need.append(parent)        # a sobra precisa do pai; a soma, nao
            break

    def _uniq(seq):
        seen = set()
        return [x for x in seq if not (x in seen or seen.add(x))]

    return _uniq(requested), _uniq(need), kids


async def fetch(hass: HomeAssistant, tree: EnergyTree, entities, d_from, d_to,
                source="states", mode="delta", degree="auto", max_days=const.DEFAULT_MAX_DAYS):
    """Uma serie por (entidade, dia): pontos `[minuto_do_dia, valor]` na grade do `step`.

    Cada serie leva tambem a REGRESSAO (`curve` + `segments`): a linha desenhada e' o ajuste
    por minimos quadrados de um polinomio por trecho de subida/descida — ela NAO passa pelos
    pontos. `means` traz a mesma coisa para a media de todos os dias de cada entidade.
    `degree` = 'auto' | 'off' (sem ajuste: poligonal crua) | 1..5.
    """
    if source not in SOURCES:
        raise ValueError(f"fonte invalida: {source}")
    table, step, _lab = SOURCES[source]
    if mode not in ("delta", "raw"):
        raise ValueError(f"modo invalido: {mode}")
    if d_to < d_from:
        d_from, d_to = d_to, d_from
    ndays = (d_to - d_from).days + 1
    if ndays > max_days:
        raise ValueError(f"intervalo de {ndays} dias excede o limite de {max_days}")
    if degree not in ("auto", "off") and str(degree) not in "12345":
        raise ValueError(f"grau invalido: {degree}")

    tz = ZoneInfo(hass.config.time_zone)
    days = [d_from + dt.timedelta(days=i) for i in range(ndays)]
    lo = _epoch(d_from, tz)
    hi = _epoch(d_to + dt.timedelta(days=1), tz)

    # `requested` e' o que sera' desenhado; `needed` inclui pai/filhos puxados so' para
    # alimentar uma serie sintetica.
    requested, needed, kids = _parse_selection(entities, tree)
    step_min = step // 60
    smp = 2 if step_min <= 5 else max(2, step_min // 4)
    out = {"step_min": step_min, "mode": mode, "source": source, "unit": "kWh",
           "degree": degree, "sample_min": smp,
           "days": [d.isoformat() for d in days], "series": [], "means": [], "missing": [],
           "dropped_total": 0}
    if not needed:
        return out

    mids = await _meta_ids(hass, needed, source)
    out["missing"] = [e for e in needed if e not in mids]
    ids = [mids[e] for e in needed if e in mids]
    if not ids:
        return out
    by_id = {mids[e]: e for e in needed if e in mids}

    # Janela ALARGADA para o ajuste enxergar contexto fora do dia (senao o 1o e o ultimo trecho
    # nascem/morrem dentro do dia e a curva aparece cortada). O que entra de fato sao 3 horas
    # COM DADO de cada lado, escolhidas depois — a janela larga e' so' area de busca.
    lo_q, hi_q = lo - EXT_SEARCH_SEC, hi + EXT_SEARCH_SEC
    if source == "states":
        rows = await _rows_states(hass, ids, lo_q, hi_q, step)
    else:
        rows = await _rows_stats(hass, table, ids, lo_q, hi_q, step)

    return await hass.async_add_executor_job(
        _assemble, out, rows, by_id, requested, kids, days, tz, lo_q, hi_q, step, mode, source,
        degree, smp, step_min)


def _assemble(out, rows, by_id, requested, kids, days, tz, lo_q, hi_q, step, mode, source,
              degree, smp, step_min):
    """Parte de CPU: bucketizacao, preenchimento, contexto e regressao. Roda no executor geral."""
    nbk = int(math.ceil((hi_q - lo_q) / step))
    grid = {}      # entidade -> {bucket: valor}
    anchor = {}    # entidade -> (bucket, valor cru) da ultima amostra ANTES da janela
    for mid, bk, v, d in rows:
        entity = by_id[mid]
        if bk < 0:                       # ancora do lag: prova que a entidade ja existia
            prev = anchor.get(entity)
            if v is not None and (prev is None or bk > prev[0]):
                anchor[entity] = (bk, float(v))
            continue
        if bk >= nbk:
            continue
        value = v if mode == "raw" else d
        if value is None:
            continue
        if mode == "delta" and source == "states" and value < 0:
            value = 0.0                  # reset do contador total_increasing
        grid.setdefault(entity, {})[bk] = round(float(value), 4)

    # ---- preenchimento dos vazios -----------------------------------------------------
    # A ausencia de linha em `states` NAO e' ausencia de informacao: o odometro nao mudou.
    # Solar de madrugada, tomada desligada, aparelho parado — todos param de gravar e o
    # grafico ficava com a curva comecando as 07:00. Vazio => delta 0 (sem consumo) no modo
    # `delta`, ultimo valor conhecido no modo `bruto`. Nao se inventa dado antes da primeira
    # amostra da entidade (sem ancora) nem depois de AGORA (o dia de hoje ainda nao aconteceu).
    now_bk = int((dt.datetime.now(tz).timestamp() - lo_q) // step)
    for entity, g in grid.items():
        ks = sorted(g)
        if not ks:
            continue
        start = 0 if entity in anchor else ks[0]
        end = min(nbk - 1, now_bk)
        last = anchor.get(entity, (None, None))[1]
        for bk in range(start, end + 1):
            if bk in g:
                last = g[bk]
                continue
            if mode == "delta":
                g[bk] = 0.0
            elif last is not None:
                g[bk] = last

    # ---- series sinteticas: `Σ filhos` e `(untracked)` ---------------------------------
    # Nascem AQUI, sobre a grade ja' preenchida e antes da divisao por dia, para percorrerem
    # exatamente o mesmo caminho de qualquer entidade real: contexto de 3 h, regressao,
    # descarte por residuo, total do dia e media entre dias. Sao filhos DIRETOS: o neto entra
    # na soma do pai dele, que por sua vez e' um dos termos da soma do avo.
    # O negativo NAO e' clampado — pai menor que a soma dos filhos e' arvore mal configurada
    # ou sensor errado, e zerar isso esconderia o problema.
    for syn, (parent, children) in kids.items():
        present = [grid[c] for c in children if c in grid]
        if syn.startswith(const.SUM_PREFIX):
            if not present:
                continue
            g = {}
            for gc in present:
                for bk, v in gc.items():
                    g[bk] = g.get(bk, 0.0) + v
        else:
            base = grid.get(parent)
            if not base:
                continue
            g = {bk: v - sum(gc.get(bk, 0.0) for gc in present) for bk, v in base.items()}
        grid[syn] = {bk: round(v, 4) for bk, v in g.items()}

    # ---- distribuicao por dia + contexto de EXT_HOURS horas COM DADO -------------------
    day_start = {d.isoformat(): _epoch(d, tz) for d in days}
    buf = {}   # (entity, dia) -> {minuto relativo ao dia: valor}
    for entity, g in grid.items():
        xs_by_day = {}
        for bk, val in g.items():
            epoch = lo_q + bk * step
            ts = dt.datetime.fromtimestamp(epoch, tz)
            for off in (-1, 0, 1):
                iso = (ts.date() + dt.timedelta(days=off)).isoformat()
                start = day_start.get(iso)
                if start is None:
                    continue
                x = int(round((epoch - start) / 60))
                if -EXT_SEARCH_SEC // 60 <= x <= 1440 + EXT_SEARCH_SEC // 60:
                    xs_by_day.setdefault(iso, {})[x] = val
        for iso, pts in xs_by_day.items():
            buf[(entity, iso)] = _with_context(pts)

    def _regress(points):
        if degree == "off":
            return {"curve": points, "segments": [], "dropped": []}
        return fit.fit(points, degree=degree, sample=smp, step_min=step_min)

    # ---- ajuste por dia + marcacao dos pontos fora do ajuste ---------------------------
    # Descartado = ponto cujo residuo contra a regressao do proprio trecho passa de
    # max(3 x sigma_res robusto, 5% da amplitude do dia) — ver `fit.fit`. O descarte vale
    # para a REGRESSAO (o trecho e' reajustado sem ele) e para a ESCALA do eixo Y (o front o
    # exclui); a MEDIA entre dias continua com TODOS os pontos — ela e' a media dos dados,
    # nao do ajuste. Visualmente o ponto vira anel vazado.
    def _in_day(x):
        return 0 <= x < 1440

    # Pai e filhos podem ter sido buscados so' para alimentar uma sintetica: o que nao foi
    # PEDIDO nao vira serie desenhada.
    for key in [k for k in buf if k[0] not in set(requested)]:
        del buf[key]

    order = {e: i for i, e in enumerate(requested)}
    acc = {}      # entidade -> {minuto: [soma, n]} sobre TODOS os pontos (inclusive o contexto)
    ndrop = 0
    for (entity, day), pts in sorted(buf.items(), key=lambda kv: (order[kv[0][0]], kv[0][1])):
        ext = [[m, pts[m]] for m in sorted(pts)]           # com as 3 h de contexto: so' o ajuste
        points = [p for p in ext if _in_day(p[0])]         # o que e' desenhado e medido
        reg = _regress(ext)
        drop = {x for x in reg.pop("dropped") if _in_day(x)}
        ndrop += len(drop)
        out["series"].append({
            "entity": entity, "day": day, "points": points, "dropped": sorted(drop),
            "total": round(sum(v for m, v in ext if _in_day(m)), 4) if mode == "delta" else None,
            **reg,
        })
        a = acc.setdefault(entity, {})
        for m, v in pts.items():
            s = a.setdefault(m, [0.0, 0])
            s[0] += v
            s[1] += 1

    for entity in requested:
        a = acc.get(entity)
        if not a:
            continue
        ext = [[m, round(a[m][0] / a[m][1], 4)] for m in sorted(a)]
        reg = _regress(ext)
        reg.pop("dropped", None)
        out["means"].append({"entity": entity, "points": [p for p in ext if _in_day(p[0])],
                             "days": max(v[1] for v in a.values()), **reg})
    out["dropped_total"] = ndrop
    return out
