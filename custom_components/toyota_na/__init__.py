from ctypes import cast
from datetime import timedelta, datetime
import logging
import asyncio

from toyota_na.auth import ToyotaOneAuth
from toyota_na.client import ToyotaOneClient

# Patch client code
from .patch_client import get_electric_status, api_request
ToyotaOneClient.get_electric_status = get_electric_status
ToyotaOneClient.api_request = api_request

# Patch base_vehicle
import toyota_na.vehicle.base_vehicle
from .patch_base_vehicle import ApiVehicleGeneration
toyota_na.vehicle.base_vehicle.ApiVehicleGeneration = ApiVehicleGeneration
from .patch_base_vehicle import VehicleFeatures
toyota_na.vehicle.base_vehicle.VehicleFeatures = VehicleFeatures
from .patch_base_vehicle import RemoteRequestCommand
toyota_na.vehicle.base_vehicle.RemoteRequestCommand = RemoteRequestCommand
from .patch_base_vehicle import ToyotaVehicle
toyota_na.vehicle.base_vehicle.ToyotaVehicle = ToyotaVehicle

# Patch seventeen_cy_plus
from toyota_na.vehicle.vehicle_generations.seventeen_cy_plus import SeventeenCYPlusToyotaVehicle
from .patch_seventeen_cy_plus import SeventeenCYPlusToyotaVehicle
toyota_na.vehicle.vehicle_generations.seventeen_cy_plus.SeventeenCYPlusToyotaVehicle = SeventeenCYPlusToyotaVehicle

# Patch seventeen_cy
from toyota_na.vehicle.vehicle_generations.seventeen_cy import SeventeenCYToyotaVehicle
from .patch_seventeen_cy import SeventeenCYToyotaVehicle
toyota_na.vehicle.vehicle_generations.seventeen_cy.SeventeenCYToyotaVehicle = SeventeenCYToyotaVehicle

from toyota_na.exceptions import AuthError, LoginError
from toyota_na.vehicle.base_vehicle import RemoteRequestCommand, ToyotaVehicle

#Patch get_vehicles
from .patch_vehicle import get_vehicles
#from toyota_na.vehicle.vehicle import get_vehicles

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import device_registry as dr, service
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    COMMAND_MAP,
    DOMAIN,
    ENGINE_START,
    ENGINE_STOP,
    HAZARDS_ON,
    HAZARDS_OFF,
    DOOR_LOCK,
    DOOR_UNLOCK,
    REFRESH,
    UPDATE_INTERVAL,
    REFRESH_STATUS_INTERVAL,
    CONF_UPDATE_INTERVAL,
    CONF_REFRESH_STATUS_INTERVAL
)

_LOGGER = logging.getLogger(__name__)
PLATFORMS = ["binary_sensor", "device_tracker", "lock", "sensor"]

async def async_setup(hass: HomeAssistant, _processed_config) -> bool:
    @service.verify_domain_control(hass, DOMAIN)
    async def async_service_handle(service_call: ServiceCall) -> None:
        """Handle dispatched services."""

        device_registry = dr.async_get(hass)
        device = device_registry.async_get(service_call.data["vehicle"])
        remote_action = service_call.service

        if device is None:
            _LOGGER.warning("Device does not exist")
            return

        # There is currently not a case with this integration where
        # the device will have more or less than one config entry
        if len(device.config_entries) != 1:
            _LOGGER.warning("Device missing config entry")
            return

        entry_id = list(device.config_entries)[0]

        if entry_id not in hass.data[DOMAIN]:
            _LOGGER.warning("Config entry not found")
            return

        if "coordinator" not in hass.data[DOMAIN][entry_id]:
            _LOGGER.warning("Coordinator not found")
            return

        coordinator = hass.data[DOMAIN][entry_id]["coordinator"]

        if coordinator.data is None:
            _LOGGER.warning("No coordinator data")
            return

        for identifier in device.identifiers:
            if identifier[0] == DOMAIN:

                vin = identifier[1]
                for vehicle in coordinator.data:
                    if vehicle.vin == vin and remote_action.upper() == "REFRESH" and vehicle.subscribed:
                        await vehicle.poll_vehicle_refresh()
                        # TODO: This works great and prevents us from unnecessarily hitting Toyota. But we can and should
                        # probably do stuff like this in the library where we can better control which APIs we hit to refresh our in-memory data.
                        coordinator.async_set_updated_data(coordinator.data)
                        await asyncio.sleep(10)
                        await coordinator.async_request_refresh()
                    elif vehicle.vin == vin and vehicle.subscribed:
                        await vehicle.send_command(COMMAND_MAP[remote_action])
                        break

                _LOGGER.info("Handling service call %s for %s ", remote_action, vin)

        return

    hass.services.async_register(DOMAIN, ENGINE_START, async_service_handle)
    hass.services.async_register(DOMAIN, ENGINE_STOP, async_service_handle)
    hass.services.async_register(DOMAIN, HAZARDS_ON, async_service_handle)
    hass.services.async_register(DOMAIN, HAZARDS_OFF, async_service_handle)
    hass.services.async_register(DOMAIN, DOOR_LOCK, async_service_handle)
    hass.services.async_register(DOMAIN, DOOR_UNLOCK, async_service_handle)
    hass.services.async_register(DOMAIN, REFRESH, async_service_handle)

    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Toyota NA from a config entry."""
    hass.data.setdefault(DOMAIN, {}).setdefault(entry.entry_id, {})

    # Use a single client instance
    client = ToyotaOneClient(
        ToyotaOneAuth(
            initial_tokens=entry.data["tokens"],
            callback=lambda tokens: update_tokens(tokens, hass, entry),
        )
    )
    
    # Initialize client with existing tokens
    client.auth.set_tokens(entry.data["tokens"])
    
    # Try to check tokens, but don't fail if it doesn't work
    try:
        await client.auth.check_tokens()
    except AuthError:
        _LOGGER.warning("Token refresh failed, attempting to re-login with username/password")
        try:
            await client.auth.login(entry.data["username"], entry.data["password"], None)
        except Exception as e:
            _LOGGER.error(f"Re-authentication failed: {str(e)}")
            raise ConfigEntryAuthFailed("Failed to authenticate with Toyota API") from e

    # Store client in hass.data
    hass.data[DOMAIN][entry.entry_id]["toyota_na_client"] = client

    # Get update interval from options or use default
    update_interval_seconds = entry.options.get(CONF_UPDATE_INTERVAL, UPDATE_INTERVAL)
    
    # Create coordinator with appropriate update interval
    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=DOMAIN,
        update_method=lambda: update_vehicles_status(hass, client, entry),
        update_interval=timedelta(seconds=update_interval_seconds),
    )
    
    # Store coordinator in hass.data
    hass.data[DOMAIN][entry.entry_id]["coordinator"] = coordinator
    
    # Do first refresh
    await coordinator.async_config_entry_first_refresh()

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def update_vehicles_status(hass: HomeAssistant, client: ToyotaOneClient, entry: ConfigEntry):
    """Update vehicle status."""
    # Check if we need to refresh all vehicles
    need_refresh = False
    need_refresh_before = datetime.utcnow().timestamp() - REFRESH_STATUS_INTERVAL
    
    # Get refresh interval from options
    refresh_interval = entry.options.get(CONF_REFRESH_STATUS_INTERVAL, REFRESH_STATUS_INTERVAL)
    need_refresh_before = datetime.utcnow().timestamp() - refresh_interval
    
    if "last_refreshed_at" not in entry.data or entry.data["last_refreshed_at"] < need_refresh_before:
        need_refresh = True
        _LOGGER.debug(f"Full refresh needed. Last refresh: {entry.data.get('last_refreshed_at', 'never')}")
    
    try:
        # Get vehicles with a single API call
        _LOGGER.debug("Fetching vehicles from Toyota API")
        raw_vehicles = await get_vehicles(client)
        vehicles: list[ToyotaVehicle] = []
        
        # Process each vehicle
        for vehicle in raw_vehicles:
            # Check subscription
            if vehicle.subscribed is not True:
                _LOGGER.debug(
                    f"Vehicle {vehicle.vin} ({vehicle.model_year} {vehicle.model_name}) needs a subscription"
                )
            
            # Only refresh subscribed vehicles when needed
            if need_refresh and vehicle.subscribed:
                _LOGGER.debug(f"Refreshing vehicle {vehicle.vin}")
                try:
                    await vehicle.poll_vehicle_refresh()
                except Exception as e:
                    _LOGGER.warning(f"Error refreshing vehicle {vehicle.vin}: {str(e)}")
            
            # Add to list
            vehicles.append(vehicle)
        
        # Update last refreshed timestamp
        if need_refresh:
            entry_data = dict(entry.data)
            entry_data["last_refreshed_at"] = datetime.utcnow().timestamp()
            hass.config_entries.async_update_entry(entry, data=entry_data)
        
        return vehicles
        
    except AuthError:
        _LOGGER.warning("Authentication error during update, attempting to re-login")
        try:
            # Try to login again
            await client.auth.login(entry.data["username"], entry.data["password"], None)
            
            # Try again after successful login
            raw_vehicles = await get_vehicles(client)
            vehicles: list[ToyotaVehicle] = []
            
            for vehicle in raw_vehicles:
                vehicles.append(vehicle)
                
            return vehicles
            
        except Exception as e:
            _LOGGER.error(f"Re-authentication failed during update: {str(e)}")
            raise ConfigEntryAuthFailed("Failed to authenticate with Toyota API") from e
            
    except Exception as e:
        _LOGGER.error(f"Error fetching vehicle data: {str(e)}")
        raise UpdateFailed(f"Error updating vehicle data: {str(e)}") from e


def update_tokens(tokens: dict[str, str], hass: HomeAssistant, entry: ConfigEntry):
    _LOGGER.info("Tokens refreshed, updating ConfigEntry")
    data = dict(entry.data)
    data["tokens"] = tokens
    hass.config_entries.async_update_entry(entry, data=data)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
