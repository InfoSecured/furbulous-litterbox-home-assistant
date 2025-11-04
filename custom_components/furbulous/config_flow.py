"""Config flow for Furbulous Cat integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.data_entry_flow import FlowResult

from .const import CONF_ACCOUNT_TYPE, CONF_TOKEN, DEFAULT_ACCOUNT_TYPE, DOMAIN
from .furbulous_api import FurbulousCatAPI, FurbulousCatAuthError

_LOGGER = logging.getLogger(__name__)

from .const import CONF_ACCOUNT_TYPE, CONF_TOKEN, CONF_REGION, DEFAULT_ACCOUNT_TYPE, DOMAIN

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_TOKEN): str,
        vol.Optional(CONF_EMAIL): str,
        vol.Optional(CONF_PASSWORD): str,
        vol.Optional(CONF_ACCOUNT_TYPE, default=DEFAULT_ACCOUNT_TYPE): int,
    }
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Furbulous Cat."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            _LOGGER.debug("Config flow started with input")
            
            try:
                # Check if user provided a token directly
                if CONF_TOKEN in user_input and user_input[CONF_TOKEN]:
                    _LOGGER.debug("Using token authentication")
                    api = FurbulousCatAPI(
                        email="",
                        password="",
                        account_type=DEFAULT_ACCOUNT_TYPE,
                        token=user_input[CONF_TOKEN]
                    )
                    
                    _LOGGER.debug("Testing token by fetching device list")
                    devices = await self.hass.async_add_executor_job(api.get_devices)
                    _LOGGER.info("Token validated successfully, found %d devices", len(devices))
                    
                    await self.async_set_unique_id(f"furbulous_token_{user_input[CONF_TOKEN][:10]}")
                    self._abort_if_unique_id_configured()
                    
                    return self.async_create_entry(
                        title="Furbulous Cat (Token)",
                        data={CONF_TOKEN: user_input[CONF_TOKEN]},
                    )
                
                # Otherwise use email/password authentication
                _LOGGER.debug("Using email/password authentication")
                
                if not user_input.get(CONF_EMAIL) or not user_input.get(CONF_PASSWORD):
                    _LOGGER.warning("Missing credentials")
                    errors["base"] = "missing_credentials"
                    return self.async_show_form(
                        step_id="user",
                        data_schema=STEP_USER_DATA_SCHEMA,
                        errors=errors,
                    )
                
                api = FurbulousCatAPI(
                    email=user_input[CONF_EMAIL],
                    password=user_input[CONF_PASSWORD],
                    account_type=user_input.get(CONF_ACCOUNT_TYPE, DEFAULT_ACCOUNT_TYPE)
                    # REMOVED: region=user_input.get(CONF_REGION, DEFAULT_REGION)
                )
                
                _LOGGER.debug("Attempting authentication for email: %s", user_input[CONF_EMAIL])
                await self.hass.async_add_executor_job(api.authenticate)
                _LOGGER.info("Authentication successful for %s", user_input[CONF_EMAIL])

                await self.async_set_unique_id(user_input[CONF_EMAIL])
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"Furbulous Cat ({user_input[CONF_EMAIL]})",
                    data=user_input,
                )

            except FurbulousCatAuthError as err:
                _LOGGER.error("Authentication failed: %s", err)
                errors["base"] = "invalid_auth"
            except Exception as err:
                _LOGGER.exception("Unexpected exception during config flow: %s", err)
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )