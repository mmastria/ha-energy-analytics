"""API do painel: comandos WebSocket (substituem as rotas Flask `/api/*`).

WebSocket em vez de `HomeAssistantView` porque o painel ja roda dentro de uma sessao autenticada
do frontend: sem Bearer token no fetch, sem CORS, sem token expirando no meio da sessao.
"""
from __future__ import annotations

import datetime as dt

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util import dt as dt_util

from . import series, tree as tree_mod
from .const import CONF_MAX_DAYS, DEFAULT_MAX_DAYS, DOMAIN, MIN_DATE
from .energy_tree import async_get_tree


def _max_days(hass: HomeAssistant) -> int:
    # O NumberSelector do options flow devolve float; o teto e' contagem de dias.
    return int(hass.data.get(DOMAIN, {}).get(CONF_MAX_DAYS) or DEFAULT_MAX_DAYS)


@callback
def async_register(hass: HomeAssistant) -> None:
    """Registra os comandos. Re-registrar sobrescreve o handler — seguro no reload."""
    websocket_api.async_register_command(hass, ws_tree)
    websocket_api.async_register_command(hass, ws_series)


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/tree"})
@websocket_api.async_response
async def ws_tree(hass: HomeAssistant, connection, msg) -> None:
    """Arvore do Energy Dashboard + fontes + limites de data do painel."""
    try:
        tree = await async_get_tree(hass)
    except HomeAssistantError as err:
        connection.send_error(msg["id"], "energy_not_configured", str(err))
        return
    connection.send_result(msg["id"], {
        "nodes": tree_mod.nodes(hass, tree),
        "sources": series.source_options(),
        "max_days": _max_days(hass),
        "min_date": MIN_DATE,
        "today": dt_util.now().date().isoformat(),
    })


@websocket_api.websocket_command({
    vol.Required("type"): f"{DOMAIN}/series",
    vol.Required("entities"): [str],
    vol.Required("from"): str,
    vol.Required("to"): str,
    vol.Optional("source", default="states"): str,
    vol.Optional("degree", default="auto"): str,
})
@websocket_api.async_response
async def ws_series(hass: HomeAssistant, connection, msg) -> None:
    """Series por (entidade, dia) + regressao. Mesmo payload do antigo `GET /api/series`."""
    try:
        d_from = dt.date.fromisoformat(msg["from"])
        d_to = dt.date.fromisoformat(msg["to"])
    except ValueError:
        connection.send_error(msg["id"], "invalid_date", "data invalida (YYYY-MM-DD)")
        return
    try:
        tree = await async_get_tree(hass)
        result = await series.fetch(hass, tree, msg["entities"], d_from, d_to,
                                    msg["source"], msg["degree"],
                                    max_days=_max_days(hass))
    except ValueError as err:
        connection.send_error(msg["id"], "invalid_request", str(err))
        return
    except HomeAssistantError as err:
        connection.send_error(msg["id"], "energy_not_configured", str(err))
        return
    connection.send_result(msg["id"], result)
