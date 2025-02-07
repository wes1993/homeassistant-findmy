"""Config flow for the Find My integration."""

from __future__ import annotations

import logging
from plistlib import InvalidFileException
from typing import Any

import aiohttp
from findmy.errors import (
    InvalidCredentialsError,
    UnauthorizedError,
    UnhandledProtocolError,
)
from findmy.reports.state import LoginState
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, CONF_URL
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import CONF_2FA_CODE, CONF_2FA_METHOD, CONF_ACCOUNT, CONF_PLIST, DOMAIN
from .findmy_hub import FindMyHub

_LOGGER = logging.getLogger(__name__)


STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(
            CONF_URL,
            default="http://localhost:6969",
        ): TextSelector(TextSelectorConfig(type=TextSelectorType.URL)),
        vol.Required(CONF_EMAIL): str,
        vol.Required(CONF_PASSWORD): str,
    }
)

STEP_2FA_CODE_DATA_SCHEMA = vol.Schema({vol.Required(CONF_2FA_CODE): str})

STEP_PLIST_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_PLIST): TextSelector(TextSelectorConfig(multiline=True)),
    }
)


class ConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Find My."""

    VERSION = 1

    def __init__(self):
        """Initialize config flow."""
        self.url: str | None = None
        self.email: str | None = None
        self.hub: FindMyHub | None = None
        self.two_factor_method: int | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                self.url = user_input[CONF_URL]
                self.email = user_input[CONF_EMAIL]
                self.hub = FindMyHub(user_input[CONF_URL])
                state = await self.hub.authenticate(
                    user_input[CONF_EMAIL], user_input[CONF_PASSWORD]
                )

                _LOGGER.debug("Login state: %s", state)

                if state == LoginState.REQUIRE_2FA:
                    methods = [
                        SelectOptionDict(label=label, value=value)
                        for (value, label) in await self.hub.get_2fa_methods()
                    ]

                    two_factor_schema = vol.Schema(
                        {
                            vol.Required(CONF_2FA_METHOD): SelectSelector(
                                SelectSelectorConfig(options=methods)
                            )
                        }
                    )

                    return self.async_show_form(
                        step_id="2fa_method", data_schema=two_factor_schema
                    )
                if state == LoginState.LOGGED_IN:
                    return self.async_show_form(
                        step_id="plist", data_schema=STEP_PLIST_DATA_SCHEMA
                    )

                errors["base"] = "invalid_auth"
            except aiohttp.ClientConnectorError:
                errors["base"] = "cannot_connect"
            except (InvalidCredentialsError, UnauthorizedError):
                errors["base"] = "invalid_auth"
            except Exception as e:
                _LOGGER.exception("Unexpected exception", exc_info=e)
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_2fa_method(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the two-factor method step."""

        if user_input is not None and self.hub is not None:
            self.two_factor_method = int(user_input[CONF_2FA_METHOD])

            try:
                await self.hub.request_two_factor(self.two_factor_method)
            except UnhandledProtocolError:
                return self.async_abort(reason="unknown")

            return self.async_show_form(
                step_id="2fa_code", data_schema=STEP_2FA_CODE_DATA_SCHEMA
            )

        return self.async_abort(reason="invalid input")

    async def async_step_2fa_code(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the two-factor step."""

        if user_input and self.hub and self.two_factor_method is not None:
            state = await self.hub.submit_two_factor(
                self.two_factor_method, user_input[CONF_2FA_CODE]
            )

            if state not in (LoginState.LOGGED_IN, LoginState.AUTHENTICATED):
                return self.async_abort(reason="invalid_2fa_code")

            return self.async_show_form(
                step_id="plist", data_schema=STEP_PLIST_DATA_SCHEMA
            )

        return self.async_abort(reason="invalid input")

    async def async_step_plist(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the plist step."""
        errors: dict[str, str] = {}

        if user_input and self.hub and self.email:
            try:
                self.hub.load_plist(user_input[CONF_PLIST])

                return self.async_create_entry(
                    title=self.email,
                    data={
                        CONF_URL: self.url,
                        CONF_ACCOUNT: self.hub.get_account_credentials(),
                        CONF_PLIST: user_input[CONF_PLIST],
                    },
                )
            except InvalidFileException:
                errors["base"] = "invalid_file"

                return self.async_show_form(
                    step_id="plist", data_schema=STEP_PLIST_DATA_SCHEMA, errors=errors
                )

        return self.async_abort(reason="invalid input")
