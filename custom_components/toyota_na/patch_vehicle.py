from toyota_na.client import ToyotaOneClient
from toyota_na.vehicle.base_vehicle import (
    ApiVehicleGeneration,
    ToyotaVehicle,
)
from toyota_na.vehicle.vehicle_generations.seventeen_cy import SeventeenCYToyotaVehicle
from toyota_na.vehicle.vehicle_generations.seventeen_cy_plus import SeventeenCYPlusToyotaVehicle
import logging
import asyncio

async def get_vehicles(client: ToyotaOneClient) -> list[ToyotaVehicle]:
    _LOGGER = logging.getLogger(__name__)
    
    try:
        _LOGGER.debug("Fetching vehicle list from Toyota API")
        api_vehicles = await client.get_user_vehicle_list()
        
        # Simplified logging - just log the count
        _LOGGER.debug("Toyota API returned %d vehicles", len(api_vehicles))
        
        supportedGenerations = dict((item.value, item) for item in ApiVehicleGeneration)
        vehicles = []
        update_tasks = []

        for (i, vehicle) in enumerate(api_vehicles):
            if vehicle["generation"] not in supportedGenerations:
                continue
                
            # Get the nickname directly from the 'nickName' field
            nickname = vehicle.get("nickName") if "nickName" in vehicle else None
            
            # Check remote subscription status but don't exclude vehicles without active subscriptions
            has_remote_subscription = vehicle.get("remoteSubscriptionStatus") == "ACTIVE"
            
            # Create vehicle object based on generation
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

            # Add to vehicles list immediately
            vehicles.append(vehicle_obj)
            
            # Create update task but don't await it yet
            update_tasks.append(vehicle_obj.update())
        
        # Run all update tasks in parallel
        if update_tasks:
            await asyncio.gather(*update_tasks)
            
        return vehicles
    except Exception as e:
        _LOGGER.exception("Error in get_vehicles: %s", str(e))
        raise
