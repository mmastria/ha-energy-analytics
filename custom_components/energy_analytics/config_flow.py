"""Config flow: instancia unica, sem campos. As opcoes cabem no OptionsFlow."""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import CONF_MAX_DAYS, DEFAULT_MAX_DAYS, DOMAIN, MAX_DAYS_CEILING, PANEL_TITLE


class EnergyAnalyticsConfigFlow(ConfigFlow, domain=DOMAIN):
    """Uma unica entry: o painel e' global, nao ha o que instanciar duas vezes."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=vol.Schema({}))
        return self.async_create_entry(title=PANEL_TITLE, data={})

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return EnergyAnalyticsOptionsFlow()


class EnergyAnalyticsOptionsFlow(OptionsFlow):
    """`max_days` = teto do intervalo pedido de uma vez (custo por request no recorder)."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        current = self.config_entry.options.get(CONF_MAX_DAYS, DEFAULT_MAX_DAYS)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(CONF_MAX_DAYS, default=current): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1, max=MAX_DAYS_CEILING, step=1,
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
            }),
        )
