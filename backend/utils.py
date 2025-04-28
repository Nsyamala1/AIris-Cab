import os
import googlemaps
from datetime import datetime
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Google Maps client
gmaps = googlemaps.Client(key=os.getenv('GOOGLE_MAPS_API_KEY'))

def get_distance_matrix(pickup: str, dropoff: str) -> Dict[str, Any]:
    """Get distance and duration between two locations using Google Maps API."""
    try:
        # Request distance matrix from Google Maps
        result = gmaps.distance_matrix(
            origins=[pickup],
            destinations=[dropoff],
            mode="driving",
            departure_time=datetime.now()
        )

        if result['status'] != 'OK':
            raise Exception(f"Google Maps API error: {result['status']}")

        # Extract distance and duration from response
        element = result['rows'][0]['elements'][0]
        if element['status'] != 'OK':
            raise Exception(f"Route calculation error: {element['status']}")

        return {
            "distance": element['distance']['value'] / 1609.34,  # Convert meters to miles
            "duration": element['duration']['value'],  # Duration in seconds
            "duration_in_traffic": element.get('duration_in_traffic', {}).get('value', element['duration']['value'])
        }
    except Exception as e:
        print(f"Error getting distance matrix: {str(e)}")
        raise

def calculate_price(distance: float, duration: int, service_type: str) -> float:
    """Calculate ride price based on distance, duration, and service type."""
    # Service-specific rates
    service_rates = {
        "UberXL": {
            "base_fare": 3.00,
            "cost_per_mile": 2.00,
            "cost_per_minute": 0.35,
            "booking_fee": 2.50
        },
        "Uber": {
            "base_fare": 2.00,
            "cost_per_mile": 1.50,
            "cost_per_minute": 0.25,
            "booking_fee": 2.00
        },
        "Lyft": {
            "base_fare": 2.00,
            "cost_per_mile": 1.50,
            "cost_per_minute": 0.25,
            "booking_fee": 2.00
        },
        "LyftXL": {
            "base_fare": 3.00,
            "cost_per_mile": 2.00,
            "cost_per_minute": 0.35,
            "booking_fee": 2.50
        }
    }

    # Get rates for the service type, default to Uber rates if service type not found
    rates = service_rates.get(service_type, service_rates["Uber"])
    
    # Calculate fare components
    base_fare = rates["base_fare"]
    distance_fare = distance * rates["cost_per_mile"]
    time_fare = (duration / 60) * rates["cost_per_minute"]  # Convert seconds to minutes
    booking_fee = rates["booking_fee"]

    # Calculate total fare
    total_fare = base_fare + distance_fare + time_fare + booking_fee

    # Apply dynamic pricing (surge) based on time of day and demand
    hour = datetime.now().hour
    surge_multiplier = 1.0

    # Peak hours: 7-9 AM and 4-7 PM on weekdays
    if datetime.now().weekday() < 5:  # Monday-Friday
        if (7 <= hour <= 9) or (16 <= hour <= 19):
            surge_multiplier = 1.5

    return round(total_fare * surge_multiplier, 2)
