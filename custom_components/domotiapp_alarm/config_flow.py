"""Config flow voor DomotiApp Alarm.

Bewust leeg: één bevestigingsstap zonder invoervelden, zodat de integratie via
de UI toe te voegen is. Er valt niets in te stellen — de wekkers komen straks
per person-entiteit uit de opslag, niet uit een config entry.

Geen options flow in deze fase.
"""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import DOMAIN


class DomotiappAlarmConfigFlow(ConfigFlow, domain=DOMAIN):
    """Lege flow — er valt niets te configureren."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Bevestigingsstap zonder velden."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if user_input is None:
            return self.async_show_form(step_id="user")

        return self.async_create_entry(title="DomotiApp Alarm", data={})
