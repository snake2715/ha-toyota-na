import asyncio
import logging
from typing import Any

from toyota_na.vehicle.base_vehicle import ToyotaVehicle, VehicleFeatures
from toyota_na.vehicle.entity_types.ToyotaLockableOpening import ToyotaLockableOpening
from toyota_na.vehicle.entity_types.ToyotaOpening import ToyotaOpening
from toyota_na.vehicle.entity_types.ToyotaRemoteStart import ToyotaRemoteStart


from homeassistant.components.lock import (
    LockEntity,
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .base_entity import ToyotaNABaseEntity
from .const import COMMAND_MAP, DOMAIN, DOOR_LOCK, DOOR_UNLOCK

_LOGGER = logging.getLogger(__name__)

# Constants for command timing
COMMAND_INITIAL_WAIT = 1  # Wait 1 second after sending command before first poll
COMMAND_POLL_INTERVAL = 1  # Poll every 1 second
COMMAND_MAX_POLLS = 5     # Poll up to 5 times (total 5 seconds)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_devices: AddEntitiesCallback,
):
    """Set up the binary_sensor platform."""
    locks = []

    coordinator: DataUpdateCoordinator[list[ToyotaVehicle]] = hass.data[DOMAIN][
        config_entry.entry_id
    ]["coordinator"]

    for vehicle in coordinator.data:
        if vehicle.subscribed is False:
            continue
        locks.append(
            ToyotaLock(
                coordinator,
                "",
                vehicle.vin,
            )
        )

    async_add_devices(locks, True)


class ToyotaLock(ToyotaNABaseEntity, LockEntity):

    _state_changing = False
    _target_state = None  # Will be True for locking, False for unlocking
    _command_progress = 0  # Progress indicator (0-100%)
    _last_lock_state = None  # Track the last known lock state
    _force_state = None  # Force a specific state after a command
    _force_state_expiry = 0  # When to stop forcing the state

    def __init__(
        self,
        coordinator,
        *args: Any,
    ):
        super().__init__(coordinator, *args)
        self._state_changing = False
        self._target_state = None
        self._command_progress = 0
        self._last_lock_state = None
        self._force_state = None
        self._force_state_expiry = 0

    @property
    def icon(self):
        """Return the icon to use in the frontend."""
        if self._state_changing:
            return "mdi:lock-clock" if self._target_state else "mdi:lock-open-variant-outline"
        return "mdi:lock" if self.is_locked else "mdi:lock-open-variant"

    @property
    def name(self):
        """Return the name of the lock."""
        if self.vehicle and hasattr(self.vehicle, 'nickname') and self.vehicle.nickname:
            return f"{self.vehicle.nickname} Lock"
        return f"Toyota Lock {self.vin[-6:]}"

    @property
    def is_locked(self):
        """Return true if the vehicle is locked."""
        # Check if we're forcing a specific state
        current_time = asyncio.get_event_loop().time()
        if self._force_state is not None and current_time < self._force_state_expiry:
            _LOGGER.debug(f"Vehicle {self.vin} using forced state: {self._force_state}")
            return self._force_state
            
        # If we're in a state transition, return the expected end state
        if self._state_changing and self._target_state is not None:
            return self._target_state
            
        _is_locked = False  # Default to unlocked if we can't determine
        lock_states = {}

        if self.vehicle is not None:
            # Get all lockable openings from the vehicle
            all_locks = [
                feature
                for feature in self.vehicle.features.values()
                if isinstance(feature, ToyotaLockableOpening)
            ]
            
            # If no locks are found, return the last known state or default to False
            if not all_locks:
                _LOGGER.debug(f"No lock features found for vehicle {self.vin}, using last known state: {self._last_lock_state}")
                return self._last_lock_state if self._last_lock_state is not None else False
            
            # Check if any lock is locked - if ANY lock is locked, consider the vehicle locked
            # This matches Toyota app behavior
            for lock in all_locks:
                # Store the lock state for logging
                if hasattr(lock, 'name'):
                    lock_name = lock.name
                else:
                    lock_name = "Unknown"
                
                # Get the actual lock state
                if hasattr(lock, 'locked'):
                    lock_states[lock_name] = lock.locked
                    if lock.locked is True:
                        _is_locked = True
                else:
                    lock_states[lock_name] = None
        else:
            _LOGGER.debug(f"Vehicle {self.vin} not found in coordinator data")
        
        # Log detailed lock state information at debug level
        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug(f"Vehicle {self.vin} lock states: {lock_states}, overall state: {_is_locked}")
        
        # Store the current state for future reference
        self._last_lock_state = _is_locked
        
        return _is_locked

    @property
    def is_locking(self):
        """Return true if the vehicle is locking."""
        return self._state_changing is True and self._target_state is True

    @property
    def is_unlocking(self):
        """Return true if the vehicle is unlocking."""
        return self._state_changing is True and self._target_state is False
        
    @property
    def extra_state_attributes(self):
        """Return the state attributes of the lock."""
        attrs = {}
        
        # Add command progress information during state changes
        if self._state_changing:
            attrs["command_progress"] = self._command_progress
            attrs["command_type"] = "locking" if self._target_state else "unlocking"
            attrs["command_in_progress"] = True
        else:
            attrs["command_in_progress"] = False
        
        # Add lock status information
        attrs["lock_state"] = "locked" if self.is_locked else "unlocked"
        
        # Add last update timestamp to attributes
        if self.vehicle and hasattr(self.vehicle, 'features'):
            # Try to get the last timestamp from the vehicle
            from toyota_na.vehicle.base_vehicle import VehicleFeatures
            timestamp_feature = self.vehicle.features.get(VehicleFeatures.LastTimeStamp)
            if timestamp_feature and hasattr(timestamp_feature, 'value'):
                attrs["last_update_timestamp"] = timestamp_feature.value
        
        return attrs

    async def async_lock(self, **kwargs):
        """Lock all or specified locks. A code to lock the lock with may optionally be specified."""
        await self.toggle_lock(DOOR_LOCK)

    async def async_unlock(self, **kwargs):
        """Unlock all or specified locks. A code to unlock the lock with may optionally be specified."""
        await self.toggle_lock(DOOR_UNLOCK)

    async def toggle_lock(self, command: str):
        """Set the lock state via the provided command string."""
        if self.vehicle is not None:
            try:
                # Set state changing flag and target state
                self._state_changing = True
                self._target_state = (command == DOOR_LOCK)
                self._command_progress = 10  # Starting progress
                
                # Force the state to match what we expect after the command
                # This ensures the UI shows the correct state immediately
                self._force_state = self._target_state
                self._force_state_expiry = asyncio.get_event_loop().time() + 30  # Force for 30 seconds max
                
                # Immediately update the UI to show locking/unlocking state
                self.async_write_ha_state()
                
                _LOGGER.info(f"Starting {command} command for vehicle {self.vehicle.vin}")
                
                # Send the command to this specific vehicle
                await self.vehicle.send_command(COMMAND_MAP[command])
                self._command_progress = 30
                self.async_write_ha_state()
                
                # Poll for vehicle refresh in background
                await self.vehicle.poll_vehicle_refresh()
                self._command_progress = 50
                self.async_write_ha_state()
                
                # Wait a short time for the command to take effect
                await asyncio.sleep(COMMAND_INITIAL_WAIT)
                
                # Poll the vehicle state at regular intervals
                success = False
                for i in range(COMMAND_MAX_POLLS):
                    try:
                        # Update progress indicator
                        self._command_progress = 50 + ((i + 1) * 10)
                        self.async_write_ha_state()
                        
                        # Try to update the vehicle state
                        await self.vehicle.update()
                        
                        # Check if the state matches what we expect
                        # For this check, bypass the forced state
                        self._force_state = None  # Temporarily disable forced state
                        current_locked = self.is_locked
                        self._force_state = self._target_state  # Restore forced state
                        expected_state = self._target_state
                        
                        _LOGGER.debug(f"Poll {i+1}: Current state: {current_locked}, Expected: {expected_state}")
                        
                        if current_locked == expected_state:
                            _LOGGER.info(f"Vehicle {self.vehicle.vin} {command} command successful")
                            success = True
                            break
                            
                        await asyncio.sleep(COMMAND_POLL_INTERVAL)
                    except Exception as e:
                        _LOGGER.debug(f"Poll {i+1} failed during {command}: {str(e)}")
                        await asyncio.sleep(COMMAND_POLL_INTERVAL)
                
                # Set progress to 100% regardless of outcome
                self._command_progress = 100
                self.async_write_ha_state()
                
                if not success:
                    # Force one more update with a longer timeout
                    try:
                        _LOGGER.warning(f"Vehicle {self.vehicle.vin} {command} command may not have completed successfully, forcing final update")
                        await self.vehicle.poll_vehicle_refresh()
                        await asyncio.sleep(2)  # Wait a bit longer for the final update
                        await self.vehicle.update()
                        
                        # Check state one more time
                        self._force_state = None  # Temporarily disable forced state
                        current_locked = self.is_locked
                        self._force_state = self._target_state  # Restore forced state
                        expected_state = self._target_state
                        
                        if current_locked == expected_state:
                            _LOGGER.info(f"Vehicle {self.vehicle.vin} {command} command successful after final check")
                            success = True
                    except Exception as e:
                        _LOGGER.error(f"Final update failed after {command}: {str(e)}")
                
                # Reset state changing flags but keep the forced state for a bit longer
                self._state_changing = False
                self._target_state = None
                self._command_progress = 0
                
                # If successful, keep the forced state for 10 more seconds
                # If not successful, clear the forced state
                if success:
                    self._force_state = expected_state
                    self._force_state_expiry = asyncio.get_event_loop().time() + 10
                else:
                    self._force_state = None
                
                # Force a final update of this entity
                self.async_write_ha_state()
                
            except Exception as e:
                _LOGGER.error(f"Error sending {command} command to vehicle {self.vehicle.vin}: {str(e)}")
                # Reset all state flags
                self._state_changing = False
                self._target_state = None
                self._command_progress = 0
                self._force_state = None
                # Force an update of this entity only
                self.async_write_ha_state()

    @property
    def available(self):
        return self.vehicle is not None
