from typing import Union

from toyota_na.vehicle.base_vehicle import ToyotaVehicle, VehicleFeatures

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import DOMAIN


class ToyotaNABaseEntity(CoordinatorEntity[list[ToyotaVehicle]]):
    def __init__(
        self,
        coordinator: DataUpdateCoordinator[list[ToyotaVehicle]],
        sensor_name: str,
        vin: str,
    ) -> None:
        super().__init__(coordinator)
        self.sensor_name = sensor_name
        self.vin = vin

    def feature(self, feature: VehicleFeatures):
        """Return the feature dict."""
        if self.vehicle is None:
            return None
        return self.vehicle.features.get(feature)

    @property
    def available(self):
        """Return if entity is available."""
        # Only check if the vehicle exists in the coordinator data
        # This matches the original implementation's behavior
        return next((v for v in self.coordinator.data if v.vin == self.vin), None) is not None

    @property
    def name(self):
        if self.vehicle is not None:
            return f"{self.sensor_name} {self.device_info['name']}"

    @property
    def unique_id(self):
        return f"{self.vin}.{self.sensor_name}"

    @property
    def device_info(self) -> DeviceInfo:
        model = None
        name = None

        if self.vehicle is not None:
            model = f"{self.vehicle.model_year} {self.vehicle.model_name}"
            # Use the nickname if available, otherwise use the model information
            if hasattr(self.vehicle, 'nickname') and self.vehicle.nickname:
                name = self.vehicle.nickname
            else:
                name = model

        return {
            "identifiers": {(DOMAIN, self.vin)},
            "name": name,
            "model": model,
            "manufacturer": "Toyota Motor North America",
        }

    @property
    def vehicle(self) -> Union[ToyotaVehicle, None]:
        """Return the vehicle."""
        if not self.coordinator.data:
            return None
        return next((v for v in self.coordinator.data if v.vin == self.vin), None)
