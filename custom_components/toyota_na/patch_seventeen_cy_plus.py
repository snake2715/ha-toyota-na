import datetime
import logging
import aiohttp

from toyota_na.client import ToyotaOneClient
from toyota_na.vehicle.base_vehicle import (
    ApiVehicleGeneration,
    RemoteRequestCommand,
    ToyotaVehicle,
    VehicleFeatures,
)
from toyota_na.vehicle.entity_types.ToyotaLocation import ToyotaLocation
from toyota_na.vehicle.entity_types.ToyotaLockableOpening import ToyotaLockableOpening
from toyota_na.vehicle.entity_types.ToyotaNumeric import ToyotaNumeric
from toyota_na.vehicle.entity_types.ToyotaOpening import ToyotaOpening
from toyota_na.vehicle.entity_types.ToyotaRemoteStart import ToyotaRemoteStart

_LOGGER = logging.getLogger(__name__)

class SeventeenCYPlusToyotaVehicle(ToyotaVehicle):

    _has_remote_subscription = False
    _has_electric = False
    _nickname = None

    _command_map = {
        RemoteRequestCommand.DoorLock: "door-lock",
        RemoteRequestCommand.DoorUnlock: "door-unlock",
        RemoteRequestCommand.EngineStart: "engine-start",
        RemoteRequestCommand.EngineStop: "engine-stop",
        RemoteRequestCommand.HazardsOn: "hazard-on",
        RemoteRequestCommand.HazardsOff: "hazard-off",
        RemoteRequestCommand.Refresh: "refresh",
    }

    #  We'll parse these keys out in the parser by mapping the category and section types to a string literal
    _vehicle_status_category_map = {
        "Driver Side Door": VehicleFeatures.FrontDriverDoor,
        "Driver Side Window": VehicleFeatures.FrontDriverWindow,
        "Passenger Side Door": VehicleFeatures.FrontPassengerDoor,
        "Passenger Side Window": VehicleFeatures.FrontPassengerWindow,
        "Driver Side Rear Door": VehicleFeatures.RearDriverDoor,
        "Driver Side Rear Window": VehicleFeatures.RearDriverWindow,
        "Passenger Side Rear Door": VehicleFeatures.RearPassengerDoor,
        "Passenger Side Rear Window": VehicleFeatures.RearPassengerWindow,
        "Other Hatch": VehicleFeatures.Trunk,
        "Other Moonroof": VehicleFeatures.Moonroof,
        "Other Hood": VehicleFeatures.Hood,
    }

    _vehicle_telemetry_map = {
        "distanceToEmpty": VehicleFeatures.DistanceToEmpty,
        "flTirePressure": VehicleFeatures.FrontDriverTire,
        "frTirePressure": VehicleFeatures.FrontPassengerTire,
        "rlTirePressure": VehicleFeatures.RearDriverTire,
        "rrTirePressure": VehicleFeatures.RearPassengerTire,
        "fuelLevel": VehicleFeatures.FuelLevel,
        "odometer": VehicleFeatures.Odometer,
        "spareTirePressure": VehicleFeatures.SpareTirePressure,
        "tripA": VehicleFeatures.TripDetailsA,
        "tripB": VehicleFeatures.TripDetailsB,
        "vehicleLocation": VehicleFeatures.ParkingLocation,
        "nextService": VehicleFeatures.NextService,
        "speed": VehicleFeatures.Speed,
    }

    def __init__(
        self,
        client: ToyotaOneClient,
        has_remote_subscription: bool,
        has_electric: bool,
        model_name: str,
        model_year: str,
        vin: str,
    ):
        self._has_remote_subscription = has_remote_subscription
        self._has_electric = has_electric
        self._nickname = None

        ToyotaVehicle.__init__(
            self,
            client,
            has_remote_subscription,
            has_electric,
            model_name,
            model_year,
            vin,
            ApiVehicleGeneration.CY17PLUS,
        )

    @property
    def nickname(self) -> str:
        """Return the nickname of the vehicle."""
        return self._nickname

    @property
    def has_remote_subscription(self) -> bool:
        """Return whether the vehicle has a remote subscription."""
        return self._has_remote_subscription

    async def update(self):

        try:
            # Always try to get telemetry for all vehicles, even unsubscribed ones
            try:
                telemetry = await self._client.get_telemetry(self._vin)
                self._parse_telemetry(telemetry)
            except Exception as e:
                # Log the error but continue with other updates
                logging.error(f"Error getting telemetry: {e}")
                
            if self._has_remote_subscription:
                try:
                    vehicle_status = await self._client.get_vehicle_status(self._vin)
                    self._parse_vehicle_status(vehicle_status)
                except Exception as e:
                    # Log the error but continue with other updates
                    logging.error(f"Error getting vehicle status: {e}")
                
                try:
                    # Try to get engine status, but handle 400 errors gracefully
                    engine_status = await self._client.get_engine_status(self._vin)
                    self._parse_engine_status(engine_status)
                except aiohttp.ClientResponseError as e:
                    if e.status == 400:
                        logging.warning(f"Engine status endpoint returned 400 Bad Request. This may be due to API changes or subscription limitations. Skipping engine status update.")
                    else:
                        logging.error(f"Error getting engine status: {e}")
                except Exception as e:
                    logging.error(f"Error getting engine status: {e}")
            else:
                logging.debug(f"Vehicle {self._model_year} {self._model_name} ({self.vin}) does not have an active remote subscription. Some updates skipped.")
        except Exception as e:
            _LOGGER.error(e)
            pass

        try:
            if self._has_electric:
                # electric_status
                electric_status = await self._client.get_electric_status(self.vin)
                if electric_status is not None:
                    self._parse_electric_status(electric_status)
        except Exception as e:
            _LOGGER.error(e)
            pass

    async def poll_vehicle_refresh(self) -> None:
        """Instructs Toyota's systems to ping the vehicle to upload a fresh status. Useful when certain actions have been taken, such as locking or unlocking doors."""
        await self._client.send_refresh_status(self._vin)

    async def send_command(self, command: RemoteRequestCommand) -> None:
        """Send a remote command to the vehicle with robust error handling."""
        try:
            await self._client.remote_request(self._vin, self._command_map[command])
            _LOGGER.info(f"Successfully sent command {command} to vehicle {self._vin}")
        except aiohttp.ClientResponseError as e:
            _LOGGER.error(f"Error sending command {command} to vehicle {self._vin}: HTTP {e.status} - {e.message}")
            if e.status == 400:
                _LOGGER.warning(f"Bad Request (400) when sending command. This may be due to API changes, subscription limitations, or vehicle state.")
            elif e.status == 401 or e.status == 403:
                _LOGGER.warning(f"Authentication error ({e.status}) when sending command. Tokens may need to be refreshed.")
                # Try to refresh tokens
                try:
                    # Use login instead of refresh_tokens which might be failing
                    if hasattr(self._client.auth, 'username') and hasattr(self._client.auth, 'password'):
                        await self._client.auth.login(self._client.auth.username, self._client.auth.password)
                    else:
                        await self._client.auth.refresh_tokens()
                    _LOGGER.info("Successfully refreshed authentication tokens")
                    # Try the command again after refreshing tokens
                    try:
                        await self._client.remote_request(self._vin, self._command_map[command])
                        _LOGGER.info(f"Successfully sent command {command} to vehicle {self._vin} after token refresh")
                    except Exception as retry_e:
                        _LOGGER.error(f"Still failed to send command after token refresh: {retry_e}")
                except Exception as auth_e:
                    _LOGGER.error(f"Failed to refresh authentication tokens: {auth_e}")
                    # Don't raise the exception to prevent integration disconnection
        except Exception as e:
            _LOGGER.error(f"Unexpected error sending command {command} to vehicle {self._vin}: {e}")
            # Don't raise the exception to prevent integration disconnection

    #
    # engine_status
    #

    def _parse_engine_status(self, engine_status: dict) -> None:

        self._features[VehicleFeatures.RemoteStartStatus] = ToyotaRemoteStart(
            date=engine_status.get("date"),
            on=engine_status["status"] == "1",
            timer=engine_status.get("timer"),
        )
    
    #
    # electric_status
    #

    def _parse_electric_status(self, electric_status: dict) -> None:
        self._features[VehicleFeatures.ChargeDistance] = ToyotaNumeric(electric_status["vehicleInfo"]["chargeInfo"]["evDistance"], electric_status["vehicleInfo"]["chargeInfo"]["evDistanceUnit"])
        self._features[VehicleFeatures.ChargeDistanceAC] = ToyotaNumeric(electric_status["vehicleInfo"]["chargeInfo"]["evDistanceAC"], electric_status["vehicleInfo"]["chargeInfo"]["evDistanceUnit"])
        self._features[VehicleFeatures.ChargeLevel] = ToyotaNumeric(electric_status["vehicleInfo"]["chargeInfo"]["chargeRemainingAmount"], "%")
        self._features[VehicleFeatures.PlugStatus] = ToyotaNumeric(electric_status["vehicleInfo"]["chargeInfo"]["plugStatus"], "")
        self._features[VehicleFeatures.RemainingChargeTime] = ToyotaNumeric(electric_status["vehicleInfo"]["chargeInfo"]["remainingChargeTime"], "")
        self._features[VehicleFeatures.EvTravelableDistance] = ToyotaNumeric(electric_status["vehicleInfo"]["chargeInfo"]["evTravelableDistance"], "")
        self._features[VehicleFeatures.ChargeType] = ToyotaNumeric(electric_status["vehicleInfo"]["chargeInfo"]["chargeType"], "")
        self._features[VehicleFeatures.ConnectorStatus] = ToyotaNumeric(electric_status["vehicleInfo"]["chargeInfo"]["connectorStatus"], "")
        self._features[VehicleFeatures.ChargingStatus] = ToyotaOpening(electric_status["vehicleInfo"]["chargeInfo"]["connectorStatus"] != 5)

    #
    # vehicle_health_status
    #

    def _isClosed(self, section) -> bool:
        return section["values"][0]["value"].lower() == "closed"

    def _isLocked(self, section) -> bool:
        return section["values"][1]["value"].lower() == "locked"

    def _parse_vehicle_status(self, vehicle_status: dict) -> None:

        # Real-time location is a one-off, so we'll just parse it out here
        if "latitude" in vehicle_status and "longitude" in vehicle_status:
            self._features[VehicleFeatures.ParkingLocation] = ToyotaLocation(
                vehicle_status["latitude"], vehicle_status["longitude"]
            )

        for category in vehicle_status["vehicleStatus"]:
            for section in category["sections"]:

                category_type = category["category"]
                section_type = section["section"]

                key = f"{category_type} {section_type}"

                # We don't support all features necessarily. So avoid throwing on a key error.
                if self._vehicle_status_category_map.get(key) is not None:

                    # CLOSED is always the first value entry. So we can use it to determine which subtype to instantiate
                    if section["values"].__len__() == 1:
                        self._features[
                            self._vehicle_status_category_map[key]
                        ] = ToyotaOpening(self._isClosed(section))
                    else:
                        self._features[
                            self._vehicle_status_category_map[key]
                        ] = ToyotaLockableOpening(
                            closed=self._isClosed(section),
                            locked=self._isLocked(section),
                        )

    #
    # get_telemetry
    #

    def _parse_telemetry(self, telemetry: dict) -> None:
        for key, value in telemetry.items():

            # last time stamp is a primitive
            if key == "lastTimestamp" and value is not None:
                # Parse the timestamp and store it as a formatted string instead of Unix timestamp
                dt = datetime.datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
                # Convert to local time
                local_dt = dt.astimezone()
                # Format as a readable string
                formatted_time = local_dt.strftime("%Y-%m-%d %H:%M:%S")
                self._features[VehicleFeatures.LastTimeStamp] = ToyotaNumeric(formatted_time, "")
                continue

            # tire pressure time stamp is a primitive
            if key == "tirePressureTimestamp" and value is not None:
                # Parse the timestamp and store it as a formatted string instead of Unix timestamp
                dt = datetime.datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
                # Convert to local time
                local_dt = dt.astimezone()
                # Format as a readable string
                formatted_time = local_dt.strftime("%Y-%m-%d %H:%M:%S")
                self._features[VehicleFeatures.LastTirePressureTimeStamp] = ToyotaNumeric(formatted_time, "")
                continue
                
            # fuel level is a primitive
            if key == "fuelLevel" and value is not None:
                self._features[VehicleFeatures.FuelLevel] = ToyotaNumeric(value, "%")
                continue

            # vehicle_location has a different shape and different target entity class
            if key == "vehicleLocation" and value is not None:
                self._features[VehicleFeatures.RealTimeLocation] = ToyotaLocation(
                    value["latitude"], value["longitude"]
                )
                continue

            if self._vehicle_telemetry_map.get(key) is not None and value is not None:
                self._features[self._vehicle_telemetry_map[key]] = ToyotaNumeric(
                    value["value"], value["unit"]
                )
                continue