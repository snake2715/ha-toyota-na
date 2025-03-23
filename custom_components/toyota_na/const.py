from toyota_na.vehicle.base_vehicle import VehicleFeatures

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.sensor import SensorStateClass
from homeassistant.const import PERCENTAGE, UnitOfPressure, CONF_USERNAME, CONF_PASSWORD

from toyota_na.vehicle.base_vehicle import RemoteRequestCommand


DOMAIN = "toyota_na"

DOOR_LOCK = "door_lock"
DOOR_UNLOCK = "door_unlock"
ENGINE_START = "engine_start"
ENGINE_STOP = "engine_stop"
HAZARDS_ON = "hazards_on"
HAZARDS_OFF = "hazards_off"
REFRESH = "refresh"

# Default update intervals
DEFAULT_UPDATE_INTERVAL = 300  # 5 minutes
DEFAULT_REFRESH_STATUS_INTERVAL = 3600  # 1 hour

# Current update intervals (can be changed via options flow)
UPDATE_INTERVAL = DEFAULT_UPDATE_INTERVAL
REFRESH_STATUS_INTERVAL = DEFAULT_REFRESH_STATUS_INTERVAL

# Options
CONF_UPDATE_INTERVAL = "update_interval"
CONF_REFRESH_STATUS_INTERVAL = "refresh_status_interval"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"

# Update interval options (in seconds)
UPDATE_INTERVAL_OPTIONS = {
    60: "1 minute",
    300: "5 minutes",
    600: "10 minutes",
    900: "15 minutes",
    1800: "30 minutes",
    3600: "1 hour"
}

# Refresh status interval options (in seconds)
REFRESH_STATUS_INTERVAL_OPTIONS = {
    1800: "30 minutes",
    3600: "1 hour",
    7200: "2 hours",
    14400: "4 hours",
    28800: "8 hours"
}

COMMAND_MAP = {
    DOOR_LOCK: RemoteRequestCommand.DoorLock,
    DOOR_UNLOCK: RemoteRequestCommand.DoorUnlock,
    ENGINE_START: RemoteRequestCommand.EngineStart,
    ENGINE_STOP: RemoteRequestCommand.EngineStop,
    HAZARDS_ON: RemoteRequestCommand.HazardsOn,
    HAZARDS_OFF: RemoteRequestCommand.HazardsOff,
    REFRESH: RemoteRequestCommand.Refresh,
}

BINARY_SENSORS = [
    {
        "device_class": BinarySensorDeviceClass.DOOR,
        "feature": VehicleFeatures.FrontDriverDoor,
        "icon": "mdi:car-door",
        "name": "Front Driver Door",
        "subscription": True,
        "electric": False,
    },
    {
        "device_class": BinarySensorDeviceClass.DOOR,
        "feature": VehicleFeatures.FrontPassengerDoor,
        "icon": "mdi:car-door",
        "name": "Front Passenger Door",
        "subscription": True,
        "electric": False,
    },
    {
        "device_class": BinarySensorDeviceClass.DOOR,
        "feature": VehicleFeatures.RearDriverDoor,
        "icon": "mdi:car-door",
        "name": "Rear Driver Door",
        "subscription": True,
        "electric": False,
    },
    {
        "device_class": BinarySensorDeviceClass.DOOR,
        "feature": VehicleFeatures.RearPassengerDoor,
        "icon": "mdi:car-door",
        "name": "Rear Passenger Door",
        "subscription": True,
        "electric": False,
    },
    {
        "device_class": BinarySensorDeviceClass.DOOR,
        "feature": VehicleFeatures.Hood,
        "icon": "mdi:car-door",
        "name": "Hood",
        "subscription": True,
        "electric": False,
    },
    {
        "device_class": BinarySensorDeviceClass.DOOR,
        "feature": VehicleFeatures.Trunk,
        "icon": "mdi:car-door",
        "name": "Trunk",
        "subscription": True,
        "electric": False,
    },
    {
        "device_class": BinarySensorDeviceClass.WINDOW,
        "feature": VehicleFeatures.Moonroof,
        "icon": "mdi:window-closed-variant",
        "name": "Moonroof",
        "subscription": True,
        "electric": False,
    },
    {
        "device_class": BinarySensorDeviceClass.WINDOW,
        "feature": VehicleFeatures.FrontDriverWindow,
        "icon": "mdi:window-closed-variant",
        "name": "Front Driver Window",
        "subscription": True,
        "electric": False,
    },
    {
        "device_class": BinarySensorDeviceClass.WINDOW,
        "feature": VehicleFeatures.FrontPassengerWindow,
        "icon": "mdi:window-closed-variant",
        "name": "Front Passenger Window",
        "subscription": True,
        "electric": False,
    },
    {
        "device_class": BinarySensorDeviceClass.WINDOW,
        "feature": VehicleFeatures.RearDriverWindow,
        "icon": "mdi:window-closed-variant",
        "name": "Rear Driver Window",
        "subscription": True,
        "electric": False,
    },
    {
        "device_class": BinarySensorDeviceClass.WINDOW,
        "feature": VehicleFeatures.RearPassengerWindow,
        "icon": "mdi:window-closed-variant",
        "name": "Rear Passenger Window",
        "subscription": True,
        "electric": False,
    },
    {
        "device_class": BinarySensorDeviceClass.LOCK,
        "feature": VehicleFeatures.FrontDriverDoor,
        "icon": "mdi:car-door-lock",
        "name": "Front Driver Door Lock",
        "subscription": True,
        "electric": False,
    },
    {
        "device_class": BinarySensorDeviceClass.LOCK,
        "feature": VehicleFeatures.FrontPassengerDoor,
        "icon": "mdi:car-door-lock",
        "name": "Front Passenger Door Lock",
        "subscription": True,
        "electric": False,
    },
    {
        "device_class": BinarySensorDeviceClass.LOCK,
        "feature": VehicleFeatures.RearDriverDoor,
        "icon": "mdi:car-door-lock",
        "name": "Rear Driver Door Lock",
        "subscription": True,
        "electric": False,
    },
    {
        "device_class": BinarySensorDeviceClass.LOCK,
        "feature": VehicleFeatures.RearPassengerDoor,
        "icon": "mdi:car-door-lock",
        "name": "Rear Passenger Door Lock",
        "subscription": True,
        "electric": False,
    },
    {
        "device_class": BinarySensorDeviceClass.RUNNING,
        "feature": VehicleFeatures.RemoteStartStatus,
        "icon": "mdi:car-hatchback",
        "name": "Remote Start",
        "subscription": False,
        "electric": False,
    },
    {
        "device_class": BinarySensorDeviceClass.BATTERY_CHARGING,
        "feature": VehicleFeatures.ChargingStatus,
        "icon": "mdi:ev-station",
        "name": "Charging Status",
        "subscription": True,
        "electric": True,
    },
]

SENSORS = [
    {
        "state_class": SensorStateClass.MEASUREMENT,
        "icon": "mdi:gauge",
        "feature": VehicleFeatures.DistanceToEmpty,
        "name": "Distance To Empty",
        "unit": "MI_OR_KM",
        "subscription": False,
        "electric": False,
    },
    {
        "state_class": SensorStateClass.MEASUREMENT,
        "icon": "mdi:gauge",
        "feature": VehicleFeatures.FuelLevel,
        "name": "Fuel Level",
        "unit": PERCENTAGE,
        "subscription": False,
        "electric": False,
    },
    {
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "icon": "mdi:counter",
        "feature": VehicleFeatures.Odometer,
        "name": "Odometer",
        "unit": "MI_OR_KM",
        "subscription": False,
        "electric": False,
    },
    {
        "state_class": SensorStateClass.MEASUREMENT,
        "icon": "mdi:counter",
        "feature": VehicleFeatures.TripDetailsA,
        "name": "Trip Details A",
        "unit": "MI_OR_KM",
        "subscription": False,
        "electric": False,
    },
    {
        "state_class": SensorStateClass.MEASUREMENT,
        "icon": "mdi:counter",
        "feature": VehicleFeatures.TripDetailsB,
        "name": "Trip Details B",
        "unit": "MI_OR_KM",
        "subscription": False,
        "electric": False,
    },
    {
        "state_class": SensorStateClass.MEASUREMENT,
        "icon": "mdi:car-tire-alert",
        "feature": VehicleFeatures.FrontDriverTire,
        "name": "Front Driver Tire",
        "unit": UnitOfPressure.PSI,
        "subscription": False,
        "electric": False,
    },
    {
        "state_class": SensorStateClass.MEASUREMENT,
        "icon": "mdi:car-tire-alert",
        "feature": VehicleFeatures.FrontPassengerTire,
        "name": "Front Passenger Tire",
        "unit": UnitOfPressure.PSI,
        "subscription": False,
        "electric": False,
    },
    {
        "state_class": SensorStateClass.MEASUREMENT,
        "icon": "mdi:car-tire-alert",
        "feature": VehicleFeatures.RearDriverTire,
        "name": "Rear Driver Tire",
        "unit": UnitOfPressure.PSI,
        "subscription": False,
        "electric": False,
    },
    {
        "state_class": SensorStateClass.MEASUREMENT,
        "icon": "mdi:car-tire-alert",
        "feature": VehicleFeatures.RearPassengerTire,
        "name": "Rear Passenger Tire",
        "unit": UnitOfPressure.PSI,
        "subscription": False,
        "electric": False,
    },
    {
        "state_class": SensorStateClass.MEASUREMENT,
        "icon": "mdi:car-tire-alert",
        "feature": VehicleFeatures.SpareTirePressure,
        "name": "Spare Tire Pressure",
        "unit": UnitOfPressure.PSI,
        "subscription": False,
        "electric": False,
    },
    {
        "state_class": SensorStateClass.MEASUREMENT,
        "icon": "mdi:wrench-clock",
        "feature": VehicleFeatures.NextService,
        "name": "Next Service",
        "unit": "MI_OR_KM",
        "subscription": False,
        "electric": False,
    },
    {
        "state_class": SensorStateClass.MEASUREMENT,
        "icon": "mdi:gauge",
        "feature": VehicleFeatures.ChargeDistance,
        "name": "EV Range",
        "unit": "MI_OR_KM",
        "subscription": True,
        "electric": True,
    },
    {
        "state_class": SensorStateClass.MEASUREMENT,
        "icon": "mdi:gauge",
        "feature": VehicleFeatures.ChargeDistanceAC,
        "name": "EV Range AC",
        "unit": "MI_OR_KM",
        "subscription": True,
        "electric": True,
    },
    {
        "state_class": SensorStateClass.MEASUREMENT,
        "icon": "mdi:gauge",
        "feature": VehicleFeatures.ChargeLevel,
        "name": "EV Battery Level",
        "unit": PERCENTAGE,
        "subscription": True,
        "electric": True,
    },
    {
        "state_class": SensorStateClass.MEASUREMENT,
        "icon": "mdi:gauge",
        "feature": VehicleFeatures.LastTimeStamp,
        "name": "Last Update Timestamp",
        "unit": "",
        "subscription": False,
        "electric": False,
    },
    {
        "state_class": SensorStateClass.MEASUREMENT,
        "icon": "mdi:gauge",
        "feature": VehicleFeatures.LastTirePressureTimeStamp,
        "name": "Last Tire Pressure Update Timestamp",
        "unit": "",
        "subscription": False,
        "electric": False,
    },
    {
        "state_class": SensorStateClass.MEASUREMENT,
        "icon": "mdi:gauge",
        "feature": VehicleFeatures.Speed,
        "name": "Speed",
        "unit": "km/h",
        "subscription": False,
        "electric": False,
    },
    {
        "state_class": SensorStateClass.MEASUREMENT,
        "icon": "mdi:ev-plug-type1",
        "feature": VehicleFeatures.PlugStatus,
        "name": "Plug Status",
        "unit": "",
        "subscription": True,
        "electric": True,
    },
    {
        "state_class": SensorStateClass.MEASUREMENT,
        "icon": "mdi:clock-outline",
        "feature": VehicleFeatures.RemainingChargeTime,
        "name": "Remaining Charge Time",
        "unit": "",
        "subscription": True,
        "electric": True,
    },
    {
        "state_class": SensorStateClass.MEASUREMENT,
        "icon": "mdi:gauge",
        "feature": VehicleFeatures.EvTravelableDistance,
        "name": "EV Travelable Distance",
        "unit": "",
        "subscription": True,
        "electric": True,
    },
    {
        "state_class": SensorStateClass.MEASUREMENT,
        "icon": "mdi:ev-plug-type1",
        "feature": VehicleFeatures.ChargeType,
        "name": "Charge Type",
        "unit": "",
        "subscription": True,
        "electric": True,
    },
    {
        "state_class": SensorStateClass.MEASUREMENT,
        "icon": "mdi:ev-plug-type1",
        "feature": VehicleFeatures.ConnectorStatus,
        "name": "Connector Status",
        "unit": "",
        "subscription": True,
        "electric": True,
    },
]
