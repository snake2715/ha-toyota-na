import logging

from homeassistant import config_entries
import voluptuous as vol

from toyota_na import ToyotaOneAuth, ToyotaOneClient
from toyota_na.exceptions import AuthError

# Patch auth code
from .patch_auth import authorize, login
ToyotaOneAuth.authorize = authorize
ToyotaOneAuth.login = login
import json

from .const import DOMAIN, CONF_USERNAME, CONF_PASSWORD, CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL, UPDATE_INTERVAL_OPTIONS, CONF_REFRESH_STATUS_INTERVAL, DEFAULT_REFRESH_STATUS_INTERVAL, REFRESH_STATUS_INTERVAL_OPTIONS

_LOGGER = logging.getLogger(__name__)


class ToyotaNAConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Toyota (North America) connected services"""

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                self.client = ToyotaOneClient()
                self.user_info = user_input
                await self.client.auth.authorize(user_input[CONF_USERNAME], user_input[CONF_PASSWORD])
                return await self.async_step_otp()
            except AuthError:
                errors["base"] = "not_logged_in"
                _LOGGER.error("Not logged in with username and password")
            except Exception as e:
                errors["base"] = "unknown"
                _LOGGER.exception(f"Unknown error with username and password: {str(e)}")
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {vol.Required(CONF_USERNAME): str, vol.Required(CONF_PASSWORD): str}
            ),
            errors=errors,
        )

    async def async_step_otp(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                self.otp_info = user_input
                data = await self.async_get_entry_data(self.client, errors)
                if data:
                    return await self.async_create_or_update_entry(data=data)
            except AuthError:
                errors["base"] = "not_logged_in"
                _LOGGER.error("Not logged in with one time password")
            except Exception as e:
                errors["base"] = "unknown"
                _LOGGER.exception(f"Unknown error with one time password: {str(e)}")
        return self.async_show_form(
            step_id="otp",
            data_schema=vol.Schema(
                {vol.Required("code"): str}
            ),
            errors=errors,
        )

    async def async_get_entry_data(self, client, errors):
        try:
            await client.auth.login(self.user_info[CONF_USERNAME], self.user_info[CONF_PASSWORD], self.otp_info["code"])
            id_info = await client.auth.get_id_info()
            return {
                "tokens": client.auth.get_tokens(),
                "email": id_info["email"],
                CONF_USERNAME: self.user_info[CONF_USERNAME],
                CONF_PASSWORD: self.user_info[CONF_PASSWORD],
            }
        except AuthError:
            errors["base"] = "otp_not_logged_in"
            _LOGGER.error("Invalid Verification Code")
        except Exception as e:
            errors["base"] = "unknown"
            _LOGGER.exception(f"Unknown error: {str(e)}")

    async def async_create_or_update_entry(self, data):
        existing_entry = await self.async_set_unique_id(f"{DOMAIN}:{data['email']}")
        if existing_entry:
            self.hass.config_entries.async_update_entry(existing_entry, data=data)
            await self.hass.config_entries.async_reload(existing_entry.entry_id)
            return self.async_abort(reason="reauth_successful")
        return self.async_create_entry(title=data["email"], data=data)

    async def async_step_reauth(self, data):
        return await self.async_step_user()

    @staticmethod
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return ToyotaNAOptionsFlow(config_entry)


class ToyotaNAOptionsFlow(config_entries.OptionsFlow):
    """Handle Toyota NA options."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = self.config_entry.options
        
        # Get current values or use defaults
        update_interval = options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
        refresh_status_interval = options.get(CONF_REFRESH_STATUS_INTERVAL, DEFAULT_REFRESH_STATUS_INTERVAL)

        # Create options form
        options_schema = vol.Schema(
            {
                vol.Required(
                    CONF_UPDATE_INTERVAL, 
                    default=update_interval,
                    description="API Check Frequency"
                ): vol.In(UPDATE_INTERVAL_OPTIONS),
                vol.Required(
                    CONF_REFRESH_STATUS_INTERVAL, 
                    default=refresh_status_interval,
                    description="Vehicle Wake-up Frequency"
                ): vol.In(REFRESH_STATUS_INTERVAL_OPTIONS),
            }
        )

        return self.async_show_form(
            step_id="init", 
            data_schema=options_schema,
            description_placeholders={
                "title": "Toyota NA Integration Settings",
                "description": "Configure how often your Toyota vehicle data is updated.",
                "update_info": "**API Check Frequency**: How often Home Assistant checks Toyota's servers for data.\n\n"
                               "• This is a lightweight operation that only involves API calls\n"
                               "• Does not wake up your vehicle or impact battery life\n"
                               "• Recommended: 5-15 minutes for regular use\n"
                               "• Use shorter intervals (1-5 min) if you need more responsive updates\n"
                               "• Use longer intervals (30-60 min) to reduce API calls if you're experiencing errors",
                "refresh_info": "**Vehicle Wake-up Frequency**: How often Toyota's servers ping your vehicle for fresh data.\n\n"
                                "• This operation wakes up your vehicle to get fresh data\n"
                                "• Has a higher impact on your vehicle's battery\n"
                                "• Recommended: 1-2 hours for most users\n"
                                "• Use longer intervals (4-8 hours) if you're concerned about battery drain\n"
                                "• Shorter intervals provide more up-to-date information but increase battery usage"
            }
        )
