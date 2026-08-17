"""Config flow for the Virtual Device Manager integration."""

from __future__ import annotations

from typing import Any

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the Virtual Device Manager config flow."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Handle the initial setup step."""

        if user_input is not None:
            return self.async_create_entry(
                title="Virtual Device Manager",
                data={},
            )

        return self.async_show_form(
            step_id="user",
        )
