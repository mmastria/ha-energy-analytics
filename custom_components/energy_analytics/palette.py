"""Cores do dashboard de Energia do HA (src/.../energy + common/color)."""
# Cores-BASE das fontes = as CSS vars `--energy-*-color` de color.globals.ts. Elas são a
# BORDA da barra; o PREENCHIMENTO é sempre `fade()` delas (ver `fade`).
GRID_IN = "#488fc2"    # --energy-grid-consumption-color
GRID_OUT = "#a280db"   # --energy-grid-return-color: #8353d1 no light, mas `darkColorStyles`
                       # sobrescreve p/ #a280db — e este dashboard é dark-only (:root --bg:#111).
SOLAR = "#ff9800"      # --energy-solar-color
BATT_OUT = "#4db6ac"   # --energy-battery-out-color (descarga)
BATT_IN = "#f06292"    # --energy-battery-in-color (carga)
UNTRACKED = "#9e9e9e"  # nao monitorado (cards de fonte)
HOME = "#e0e0e0"       # raiz `Total consumed`: neutro claro, nao colide com nenhuma cor de device
HIST_UNKNOWN = "#606060"  # --history-unknown-color do HA (untracked do gráfico de detalhe)

# paleta ciclica de devices = `--color-1`..`--color-54` de
# src/resources/theme/color/color.globals.ts (o tema padrão do HA não define nenhum
# `--graph-color-N`, então `getGraphColorByIndex` sempre cai no `getColorByIndex`).
DEVICE_COLORS = [
    "#4269d0", "#f4bd4a", "#ff725c", "#6cc5b0", "#a463f2", "#ff8ab7", "#9c6b4e",
    "#97bbf5", "#01ab63", "#094bad", "#c99000", "#d84f3e", "#49a28f", "#048732",
    "#d96895", "#8043ce", "#7599d1", "#7a4c31", "#6989f4", "#ffd444", "#ff957c",
    "#8fe9d3", "#62cc71", "#ffadda", "#c884ff", "#badeff", "#bf8b6d", "#927acc",
    "#97ee3f", "#bf3947", "#9f5b00", "#f48758", "#8caed6", "#f2b94f", "#eff26e",
    "#e43872", "#d9b100", "#9d7a00", "#698cff", "#00d27e", "#d06800", "#009f82",
    "#c49200", "#cbe8ff", "#fecddf", "#c27eb6", "#8cd2ce", "#c4b8d9", "#f883b0",
    "#a49100", "#f48800", "#27d0df", "#a04a9b", "#4269d0",
]
COLORS_COUNT = 54  # `COLORS_COUNT` do HA (src/common/color/colors.ts)


def device(i):
    """`getGraphColorByIndex(i)`: `i` = índice do device em `prefs.device_consumption`.

    A cor é presa à POSIÇÃO NAS PREFS — nunca à ordem de empilhamento/ordenação do
    gráfico — para que a mesma entidade tenha a mesma cor em todos os cards.
    """
    return DEVICE_COLORS[i % COLORS_COUNT]


def fade(hex_color):
    """Anexa 50% de alpha (sufixo '7F') = `getEnergyColor(..., background=true, ...)`.

    Regra do HA (common/color.ts) em TODOS os gráficos do painel de Energia, não só no de
    detalhe: cada série tem DUAS cores — preenchimento `cor + "7F"` e borda `cor` cheia.
    (`compare=true` usaria "32"/"7F"; este app não tem modo de comparação.)
    """
    return hex_color + "7F"
