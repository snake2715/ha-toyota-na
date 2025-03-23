from toyota_na.client import ToyotaOneClient
from toyota_na.vehicle.base_vehicle import (
    ApiVehicleGeneration,
    ToyotaVehicle,
)
from toyota_na.vehicle.vehicle_generations.seventeen_cy import SeventeenCYToyotaVehicle
from toyota_na.vehicle.vehicle_generations.seventeen_cy_plus import SeventeenCYPlusToyotaVehicle
import logging

async def get_vehicles(client: ToyotaOneClient) -> list[ToyotaVehicle]:
    _LOGGER = logging.getLogger(__name__)
    
    try:
        _LOGGER.debug("Fetching vehicle list from Toyota API")
        api_vehicles = await client.get_user_vehicle_list()
        
        # Log the entire API response for debugging
        _LOGGER.debug("Toyota API returned %d vehicles", len(api_vehicles))
        for i, vehicle_data in enumerate(api_vehicles):
            _LOGGER.debug("Vehicle %d data:", i+1)
            for key, value in vehicle_data.items():
                _LOGGER.debug("  %s: %s", key, value)
        
        supportedGenerations = dict((item.value, item) for item in ApiVehicleGeneration)
        vehicles = []

        # Log the first vehicle's data to see what fields are available
        if api_vehicles and len(api_vehicles) > 0:
            _LOGGER.debug("Vehicle data fields available: %s", list(api_vehicles[0].keys()))
            _LOGGER.debug("Full vehicle data for first vehicle: %s", api_vehicles[0])

        for (i, vehicle) in enumerate(api_vehicles):
            if vehicle["generation"] not in supportedGenerations:
                continue
                
            # Get the nickname directly from the 'nickName' field
            nickname = None
            if "nickName" in vehicle and vehicle["nickName"]:
                nickname = vehicle["nickName"]
                _LOGGER.debug("Found nickname '%s' for vehicle %s", 
                             nickname, vehicle.get("vin", "Unknown"))
            
            # Check remote subscription status but don't exclude vehicles without active subscriptions
            has_remote_subscription = vehicle.get("remoteSubscriptionStatus") == "ACTIVE"
            
            # Log subscription status once at debug level instead of showing warnings
            if not has_remote_subscription:
                _LOGGER.debug(
                    "Vehicle %s (%s %s) does not have an active remote subscription. Some features may be limited.",
                    vehicle.get("vin", "Unknown"),
                    vehicle.get("modelYear", ""),
                    vehicle.get("modelName", "")
                )
                
            # Store the nickname in the vehicle object for later use
            if (
                ApiVehicleGeneration(vehicle["generation"]) == ApiVehicleGeneration.CY17PLUS
                or ApiVehicleGeneration(vehicle["generation"]) == ApiVehicleGeneration.MM21
            ):
                vehicle_obj = SeventeenCYPlusToyotaVehicle(
                    client=client,
                    has_remote_subscription=has_remote_subscription,
                    has_electric=vehicle.get("evVehicle", False) == True,
                    model_name=vehicle.get("modelName", "Unknown"),
                    model_year=vehicle.get("modelYear", "Unknown"),
                    vin=vehicle.get("vin", "Unknown"),
                )
                # Set the nickname after creation
                vehicle_obj._nickname = nickname

            elif ApiVehicleGeneration(vehicle["generation"]) == ApiVehicleGeneration.CY17:
                vehicle_obj = SeventeenCYToyotaVehicle(
                    client=client,
                    has_remote_subscription=has_remote_subscription,
                    has_electric=vehicle.get("evVehicle", False) == True,
                    model_name=vehicle.get("modelName", "Unknown"),
                    model_year=vehicle.get("modelYear", "Unknown"),
                    vin=vehicle.get("vin", "Unknown"),
                )
                # Set the nickname after creation
                vehicle_obj._nickname = nickname

            await vehicle_obj.update()
            vehicles.append(vehicle_obj)

        return vehicles
    except Exception as e:
        _LOGGER.exception("Error in get_vehicles: %s", str(e))
        raise
