import random

def calculate_price(distance: float, service_type: str) -> float:
    # Base prices for different service types
    service_rates = {
        "UberXL": {"base": 3.50, "per_mile": 2.50},
        "Uber": {"base": 2.00, "per_mile": 1.50},
        "Lyft": {"base": 2.50, "per_mile": 1.75},
        "Bike": {"base": 1.00, "per_mile": 0.75}
    }
    
    rates = service_rates.get(service_type, {"base": 2.00, "per_mile": 1.50})
    surge_multiplier = random.uniform(1.0, 1.3)  # Random surge between 1.0-1.3x
    return (rates["base"] + distance * rates["per_mile"]) * surge_multiplier

def get_mock_distance(pickup: str, dropoff: str) -> dict:
    """Get mock distance and duration between two locations."""
    # Check if we have exact match in our mock data
    for (loc1, loc2), data in LOCATION_DISTANCES.items():
        if (pickup == loc1 and dropoff == loc2) or (pickup == loc2 and dropoff == loc1):
            return data
    
    # If no exact match, generate random but reasonable data
    distance = random.uniform(5.0, 30.0)  # Random distance between 5-30 miles
    duration = int(distance * 120)  # Rough estimate: 2 minutes per mile
    return {"distance": distance, "duration": duration}

# Mock data for common locations and their approximate distances
LOCATION_DISTANCES = {
    ("New York", "Boston"): {"distance": 215.0, "duration": 14400},  # 4 hours
    ("New York", "Philadelphia"): {"distance": 97.0, "duration": 7200},  # 2 hours
    ("Boston", "Philadelphia"): {"distance": 308.0, "duration": 18000},  # 5 hours
    ("Manhattan", "Brooklyn"): {"distance": 8.0, "duration": 1800},  # 30 mins
    ("Manhattan", "Queens"): {"distance": 10.0, "duration": 2400},  # 40 mins
    ("Brooklyn", "Queens"): {"distance": 9.0, "duration": 1800},  # 30 mins
    ("Guntur", "AP"): {"distance": 15.0, "duration": 1800},  # 30 mins
    ("Vijayawada", "AP"): {"distance": 15.0, "duration": 1800},  # 30 mins
}
