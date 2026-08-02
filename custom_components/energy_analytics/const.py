"""Constantes da integracao Energy Analytics."""

DOMAIN = "energy_analytics"

# Painel na sidebar
PANEL_URL = "energy-analytics"
PANEL_TITLE = "Energy Analytics"
PANEL_ICON = "mdi:chart-bell-curve-cumulative"
PANEL_ELEMENT = "energy-analytics-panel"
STATIC_URL = "/energy_analytics_static"

# Opcoes
CONF_MAX_DAYS = "max_days"
DEFAULT_MAX_DAYS = 60
MAX_DAYS_CEILING = 120

# Piso da janela de datas do painel (antes disso a historia desta casa nao presta).
MIN_DATE = "2024-01-01"

# Tabelas do recorder. Sem prefixo de schema: a sessao do recorder ja vem no search_path certo.
TBL_STATES = "states"
TBL_STATES_META = "states_meta"
TBL_STATISTICS = "statistics"
TBL_STATISTICS_SHORT_TERM = "statistics_short_term"
TBL_STATISTICS_META = "statistics_meta"
