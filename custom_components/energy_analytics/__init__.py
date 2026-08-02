"""Energy Analytics — perfis diarios de 24 h sobrepostos das entidades do Energy Dashboard.

Registra: os arquivos estaticos do painel, o painel na sidebar e os comandos WebSocket.
Nao cria entidades — e' uma integracao de servico, so' leitura sobre o recorder.
"""
from __future__ import annotations

from pathlib import Path

from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from . import websocket
from .const import (
    CONF_MAX_DAYS,
    DEFAULT_MAX_DAYS,
    DOMAIN,
    PANEL_ELEMENT,
    PANEL_ICON,
    PANEL_TITLE,
    PANEL_URL,
    STATIC_URL,
)

_STATIC_DONE = "static_registered"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    data = hass.data.setdefault(DOMAIN, {})
    data[CONF_MAX_DAYS] = entry.options.get(CONF_MAX_DAYS, DEFAULT_MAX_DAYS)

    # O router do aiohttp nao aceita o mesmo prefixo duas vezes: registrar uma unica vez por
    # processo, mesmo que a entry seja recarregada.
    if not data.get(_STATIC_DONE):
        await hass.http.async_register_static_paths([
            StaticPathConfig(STATIC_URL, str(Path(__file__).parent / "www"), False)
        ])
        data[_STATIC_DONE] = True

    websocket.async_register(hass)

    await panel_custom.async_register_panel(
        hass,
        frontend_url_path=PANEL_URL,
        webcomponent_name=PANEL_ELEMENT,
        module_url=f"{STATIC_URL}/panel.js",
        sidebar_title=PANEL_TITLE,
        sidebar_icon=PANEL_ICON,
        require_admin=True,
        embed_iframe=False,
    )

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Tira o painel da sidebar.

    Sem isto, o proximo `async_setup_entry` estoura `ValueError: Overwriting panel`. Os
    arquivos estaticos e os comandos WebSocket ficam: registra-los de novo e' idempotente.
    """
    frontend.async_remove_panel(hass, PANEL_URL)
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
