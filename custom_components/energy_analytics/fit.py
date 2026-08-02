"""Regressao polinomial por TRECHO (subida / descida) sobre a nuvem de pontos.

A curva NAO interpola os pontos: cada ponto e' um dado estatistico e a linha desenhada e' o
minimo-quadrado de um polinomio dentro do trecho onde o sinal sobe ou desce. Cada trecho tem
equacao propria (`coef`, ascendente em `t`), o R^2 e o intervalo `[x0, x1]` em minutos do dia.

Pipeline:
  1. suavizacao robusta (mediana movel -> media movel) so' para ACHAR os extremos;
  2. segmentacao em trechos monotonos, fundindo trechos curtos ou de amplitude irrelevante
     (prominencia) nos vizinhos — senao o ruido de 5 min viraria dezenas de trechos;
  3. minimos quadrados sobre os pontos CRUS de cada trecho, com `t = (x-x0)/(x1-x0)` em [0,1]
     (normalizar e' o que segura o condicionamento da Vandermonde ate' grau 5);
  4. escolha do grau: menor grau cujo R^2 ajustado fica a menos de 0.01 do melhor;
  5. amostragem densa da curva, com blend linear na fronteira entre trechos (a curva sai continua).
"""
import math
import statistics

MAX_DEG = 5
_EPS = 1e-12


# ---------------------------------------------------------------- algebra
def _solve(a, b):
    """Elimincao de Gauss com pivotamento parcial. `a` NxN (mutavel), `b` N. None se singular."""
    n = len(b)
    m = [row[:] + [b[i]] for i, row in enumerate(a)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(m[r][c]))
        if abs(m[p][c]) < _EPS:
            return None
        m[c], m[p] = m[p], m[c]
        for r in range(c + 1, n):
            f = m[r][c] / m[c][c]
            if f:
                for k in range(c, n + 1):
                    m[r][k] -= f * m[c][k]
    x = [0.0] * n
    for r in range(n - 1, -1, -1):
        s = m[r][n] - sum(m[r][k] * x[k] for k in range(r + 1, n))
        x[r] = s / m[r][r]
    return x


def polyval(coef, t):
    y = 0.0
    for c in reversed(coef):
        y = y * t + c
    return y


def _lstsq(ts, ys, deg):
    """Equacoes normais da Vandermonde em `t` (ja normalizado). Retorna coef ascendente."""
    n = deg + 1
    pw = [[t ** k for k in range(2 * deg + 1)] for t in ts]
    ata = [[sum(p[i + j] for p in pw) for j in range(n)] for i in range(n)]
    atb = [sum(p[i] * y for p, y in zip(pw, ys)) for i in range(n)]
    return _solve(ata, atb)


def _r2(ts, ys, coef):
    mean = sum(ys) / len(ys)
    sst = sum((y - mean) ** 2 for y in ys)
    sse = sum((y - polyval(coef, t)) ** 2 for t, y in zip(ts, ys))
    if sst < _EPS:
        return 1.0 if sse < _EPS else 0.0
    return 1.0 - sse / sst


def _best_fit(ts, ys, degree, cap=MAX_DEG):
    """(coef, r2, grau). `degree`='auto' -> menor grau a <0.01 do melhor R^2 ajustado."""
    n = len(ys)
    hi = min(cap, MAX_DEG, n - 2)
    if hi < 1:
        c = [sum(ys) / n]
        return c, _r2(ts, ys, c), 0
    if degree != "auto":
        d = max(1, min(int(degree), hi))
        c = _lstsq(ts, ys, d)
        return (c, _r2(ts, ys, c), d) if c else ([sum(ys) / n], 0.0, 0)

    # Selecao por AICc (nao por tolerancia de R^2): R^2 sempre sobe com o grau e uma tolerancia
    # fixa aceitava reta onde a rampa e' visivelmente curva. AICc penaliza parametro e corrige
    # amostra pequena — a comparacao e' entre modelos com o MESMO conjunto de pontos.
    cand = []
    for d in range(1, hi + 1):
        c = _lstsq(ts, ys, d)
        if not c:
            continue
        sse = sum((y - polyval(c, t)) ** 2 for t, y in zip(ts, ys))
        k = d + 2                                  # coeficientes + variancia
        if n - k - 1 <= 0:
            continue
        aicc = n * math.log(max(sse, _EPS) / n) + 2 * k + 2 * k * (k + 1) / (n - k - 1)
        cand.append((aicc, d, c))
    if not cand:
        c = _lstsq(ts, ys, 1) or [sum(ys) / n]
        return c, _r2(ts, ys, c), 1 if len(c) > 1 else 0
    aicc, d, c = min(cand, key=lambda x: (x[0], x[1]))
    return c, _r2(ts, ys, c), d


# ---------------------------------------------------------------- segmentacao
def _smooth(ys, w):
    """Mediana movel seguida de media movel (janela impar `w`)."""
    if w < 3 or len(ys) < w:
        return list(ys)
    h = w // 2
    med = [sorted(ys[max(0, i - h):i + h + 1])[len(ys[max(0, i - h):i + h + 1]) // 2]
           for i in range(len(ys))]
    return [sum(med[max(0, i - h):i + h + 1]) / len(med[max(0, i - h):i + h + 1])
            for i in range(len(med))]


def _runs(ys, min_len, eps, k=1):
    """Trechos `[i0, i1, dir]` por run-length do SINAL da inclinacao, com banda morta `eps`.

    Banda morta e' o que separa o plato (madrugada zerada, standby) da rampa: sem ela um
    "nao-decrescente" gruda a noite inteira no comeco da subida e o polinomio tem de descrever
    as duas coisas com uma equacao so'. A inclinacao e' medida por diferenca CENTRAL sobre `k`
    passos — a diferenca de vizinhos imediatos e' ruido puro numa serie de 5 min.
    """
    n = len(ys)
    if n < 3:
        return [[0, n - 1, 0]]
    d = []
    for i in range(n - 1):
        a, b = max(0, i - k + 1), min(n - 1, i + k)
        s = (ys[b] - ys[a]) / (b - a)
        d.append(1 if s > eps else (-1 if s < -eps else 0))
    runs, st = [], 0
    for i in range(1, len(d)):
        if d[i] != d[i - 1]:
            runs.append([st, i, d[i - 1]])
            st = i
    runs.append([st, n - 1, d[-1]])

    # funde o trecho mais curto (< min_len) no vizinho mais longo, ate' todos terem tamanho
    while len(runs) > 1:
        k = min(range(len(runs)), key=lambda j: runs[j][1] - runs[j][0])
        if runs[k][1] - runs[k][0] + 1 >= min_len:
            break
        if k == 0:
            j = 1
        elif k == len(runs) - 1:
            j = len(runs) - 2
        else:
            j = k - 1 if (runs[k - 1][1] - runs[k - 1][0]) >= (runs[k + 1][1] - runs[k + 1][0]) else k + 1
        a, b = min(k, j), max(k, j)
        runs[a] = [runs[a][0], runs[b][1], runs[j][2]]
        runs.pop(b)

    merged = [runs[0]]
    for r in runs[1:]:
        if r[2] == merged[-1][2]:
            merged[-1][1] = r[1]
        else:
            merged.append(r)
    return merged


def _fmt(v, sig=5):
    if v == 0:
        return "0"
    a = abs(v)
    return f"{v:.{sig}g}" if 1e-4 <= a < 1e6 else f"{v:.{sig - 1}e}"


def _equation(coef):
    parts = []
    for k, c in enumerate(coef):
        if abs(c) < _EPS:
            continue
        p = "" if k == 0 else ("·t" if k == 1 else f"·t^{k}")
        if not parts:
            parts.append(("−" if c < 0 else "") + _fmt(abs(c)) + p)
        else:
            parts.append(("− " if c < 0 else "+ ") + _fmt(abs(c)) + p)
    return "y = " + (" ".join(parts) if parts else "0")


# ---------------------------------------------------------------- API
def fit(points, degree="auto", sample=2, step_min=5):
    """points: [[minuto, valor]] ordenados. -> {curve:[[x,y]], segments:[...]}.

    `curve` e' a regressao amostrada (NAO passa pelos pontos); `segments` traz a equacao de
    cada trecho de subida/descida com R^2, grau e dominio em minutos.
    """
    pts = [(float(x), float(y)) for x, y in points if y is not None]
    if len(pts) < 3:
        return {"curve": [[x, round(y, 4)] for x, y in pts], "segments": [], "dropped": []}

    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    rng = max(ys) - min(ys)
    win = 5 if len(ys) >= 15 else 3
    sm = _smooth(ys, win)
    min_len = max(4, len(ys) // 16)
    eps = max(0.004 * rng, _EPS)         # banda morta da inclinacao (plato x rampa)
    runs = _runs(sm, min_len, eps, k=max(1, min_len // 3))

    _DIR = {1: "up", -1: "down", 0: "flat"}
    segs, dropped = [], []
    for i0, i1, dr in runs:
        sx, sy = xs[i0:i1 + 1], ys[i0:i1 + 1]
        if len(sx) < 2:
            continue
        x0, x1 = sx[0], sx[-1]
        span = (x1 - x0) or 1.0
        ts = [(x - x0) / span for x in sx]
        # trecho praticamente plano em relacao a serie inteira: grau alto so' ondularia ruido
        cap = 2 if (max(sy) - min(sy)) < 0.08 * rng else MAX_DEG
        coef, r2, deg = _best_fit(ts, sy, degree, cap)

        # Rejeicao pelo RESIDUO contra o proprio ajuste: |y - p(t)| > max(3 sigma_res, piso).
        # `sigma_res` e' robusto (MAD dos residuos) e o piso (5% da amplitude da serie) evita
        # que um trecho quase liso, de sigma minusculo, expulse metade dos seus pontos.
        # Descartado sai da media, sai da escala do eixo e volta marcado no payload.
        keep = [True] * len(sy)
        res = [y - polyval(coef, t) for t, y in zip(ts, sy)]
        if len(sy) >= 6:
            med = statistics.median(res)
            sig = statistics.median([abs(r - med) for r in res]) * 1.4826
            thr = max(3.0 * sig, 0.05 * (rng or 1))
            bad = sorted((i for i, r in enumerate(res) if abs(r) > thr),
                         key=lambda i: -abs(res[i]))
            for i in bad[:max(0, int(0.2 * len(sy)))]:      # no maximo 20% do trecho
                keep[i] = False
        kx = [x for x, ok in zip(sx, keep) if ok]
        ky = [y for y, ok in zip(sy, keep) if ok]
        dropped += [x for x, ok in zip(sx, keep) if not ok]

        if len(ky) != len(sy) and len(ky) >= deg + 2:       # refit sem os descartados
            kt = [(x - x0) / span for x in kx]
            c2, r22, d2 = _best_fit(kt, ky, degree, cap)
            coef, r2, deg = c2, r22, d2
        if not ky:
            ky = sy
        # Envelope do trecho (so' com os pontos MANTIDOS): polinomio de grau alto dispara para
        # fora dos dados nas bordas. O DESENHO e' limitado a esta faixa; coeficientes e R^2 nao.
        mrg = 0.05 * ((max(ky) - min(ky)) or rng or 1)
        segs.append({
            "x0": x0, "x1": x1, "n": len(ky), "degree": deg,
            "ylo": round(min(ky) - mrg, 4), "yhi": round(max(ky) + mrg, 4),
            "direction": _DIR[dr],
            "coef": [round(c, 8) for c in coef], "r2": round(r2, 4),
            "equation": _equation(coef), "t": f"t = (x − {x0:.0f}) / {span:.0f}",
        })
    if not segs:
        return {"curve": [[x, round(y, 4)] for x, y in pts], "segments": [], "dropped": []}

    def _eval(seg, x):
        span = (seg["x1"] - seg["x0"]) or 1.0
        y = polyval(seg["coef"], (x - seg["x0"]) / span)
        return min(max(y, seg["ylo"]), seg["yhi"])

    # amostragem + blend linear na fronteira (a curva sai continua entre trechos)
    blend = max(step_min, sample * 2)
    curve = []
    x = segs[0]["x0"]
    end = segs[-1]["x1"]
    while x <= end + 1e-9:
        k = 0
        while k < len(segs) - 1 and x > segs[k]["x1"]:
            k += 1
        y = _eval(segs[k], x)
        if k < len(segs) - 1 and x > segs[k]["x1"] - blend:
            w = (x - (segs[k]["x1"] - blend)) / (2 * blend)
            y = (1 - w) * y + w * _eval(segs[k + 1], x)
        elif k > 0 and x < segs[k]["x0"] + blend:
            w = ((segs[k]["x0"] + blend) - x) / (2 * blend)
            y = (1 - w) * y + w * _eval(segs[k - 1], x)
        curve.append([round(x, 2), round(y, 4)])
        x += sample
    return {"curve": curve, "segments": segs, "dropped": sorted(dropped)}
