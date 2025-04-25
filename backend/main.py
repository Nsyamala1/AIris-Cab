from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session
from models import SessionLocal, TrackedRoute, PriceHistory
from price_tracker import check_price_and_notify
from utils import calculate_price, get_mock_distance
import random
from datetime import datetime

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "https://*.vercel.app", "https://*.now.sh"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class LocationRequest(BaseModel):
    pickup_address: str
    dropoff_address: str
    passenger_count: int

class TrackRouteRequest(BaseModel):
    pickup_address: str
    dropoff_address: str
    passenger_count: int
    phone_number: str  # E.164 format (+1XXXXXXXXXX)
    target_price: float

# Mock cities data
CITIES = [
    "Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island",
    "Guntur", "Vijayawada", "Hyderabad", "Chennai", "Bangalore",
    "Mumbai", "Delhi", "Kolkata", "AP", "Telangana"
]

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

def get_service_urls(service: str, pickup: str, dropoff: str) -> dict:
    """Generate both deep linking and web fallback URLs for ride services."""
    encoded_pickup = pickup.replace(' ', '%20')
    encoded_dropoff = dropoff.replace(' ', '%20')
    
    if service == "Uber":
        return {
            "app_url": f"uber://?action=setPickup&pickup={encoded_pickup}&dropoff={encoded_dropoff}",
            "web_url": "https://m.uber.com/looking"
        }
    elif service == "Lyft":
        return {
            "app_url": f"lyft://ridetype?id=lyft&pickup[address]={encoded_pickup}&destination[address]={encoded_dropoff}",
            "web_url": "https://ride.lyft.com"
        }
    elif service == "Rapido":
        return {
            "app_url": f"rapido://book?pickup={encoded_pickup}&dropoff={encoded_dropoff}",
            "web_url": "https://www.rapido.bike"
        }
    return {"app_url": "", "web_url": ""}

@app.post("/compare-prices")
async def compare_prices(location: LocationRequest):
    try:
        # Get mock distance and duration
        route_data = get_mock_distance(location.pickup_address, location.dropoff_address)
        
        # Get all available services based on passenger count
        available_services = []
        
        # Always show bike option for 1-2 passengers
        if location.passenger_count <= 2:
            available_services.append({
                "service": "Bike",
                "price_estimate": calculate_price(route_data['distance'], 'Bike'),
                "duration": int(route_data['duration'] * 1.5),  # Bikes take longer
                "distance": route_data['distance'],
                "pickup": location.pickup_address,
                "dropoff": location.dropoff_address,
                "recommended": False,  # Will be updated later
                "capacity": "1-2 passengers",
                **get_service_urls("Rapido", location.pickup_address, location.dropoff_address)
            })
        
        # Always show standard options
        available_services.extend([
            {
                "service": "Uber",
                "price_estimate": calculate_price(route_data['distance'], 'Uber'),
                "duration": route_data['duration'],
                "distance": route_data['distance'],
                "pickup": location.pickup_address,
                "dropoff": location.dropoff_address,
                "recommended": False,  # Will be updated later
                "capacity": "1-4 passengers",
                **get_service_urls("Uber", location.pickup_address, location.dropoff_address)
            },
            {
                "service": "Lyft",
                "price_estimate": calculate_price(route_data['distance'], 'Lyft'),
                "duration": route_data['duration'],
                "distance": route_data['distance'],
                "pickup": location.pickup_address,
                "dropoff": location.dropoff_address,
                "recommended": False,  # Will be updated later
                "capacity": "1-4 passengers",
                **get_service_urls("Lyft", location.pickup_address, location.dropoff_address)
            }
        ])
        
        # Always show XL option
        available_services.append({
            "service": "UberXL",
            "price_estimate": calculate_price(route_data['distance'], 'UberXL'),
            "duration": route_data['duration'],
            "distance": route_data['distance'],
            "pickup": location.pickup_address,
            "dropoff": location.dropoff_address,
            "recommended": False,  # Will be updated later
            "capacity": "1-7 passengers",
            **get_service_urls("Uber", location.pickup_address, location.dropoff_address)
        })
        
        # Find the cheapest service that can accommodate the passenger count
        valid_services = [service for service in available_services 
                         if int(service['capacity'].split('-')[1].split()[0]) >= location.passenger_count]
        
        if valid_services:
            cheapest_service = min(valid_services, key=lambda x: x['price_estimate'])
            
            # Format all price estimates and mark the cheapest as recommended
            for service in available_services:
                service['price_estimate'] = f"${service['price_estimate']:.2f}"
                if service['service'] == cheapest_service['service'] and service in valid_services:
                    service['recommended'] = True
        
        estimates = available_services
        return estimates
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/track-route")
async def track_route(request: TrackRouteRequest, db: Session = Depends(get_db)):
    try:
        # Create new tracked route
        # Validate phone number format (E.164)
        if not request.phone_number.startswith('+') or not request.phone_number[1:].isdigit():
            raise HTTPException(status_code=400, detail="Phone number must be in E.164 format (+1XXXXXXXXXX)")

        route = TrackedRoute(
            pickup=request.pickup_address,
            dropoff=request.dropoff_address,
            passenger_count=request.passenger_count,
            phone_number=request.phone_number,
            target_price=request.target_price
        )
        db.add(route)
        db.commit()
        db.refresh(route)
        
        # Start tracking prices for this route
        await check_price_and_notify(route.id, db)
        
        return {"message": "Route tracking started", "route_id": route.id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tracked-routes/{phone_number}")
async def get_tracked_routes(phone_number: str, db: Session = Depends(get_db)):
    try:
        # Ensure phone number is in E.164 format
        if not phone_number.startswith('+') or not phone_number[1:].isdigit():
            raise HTTPException(
                status_code=400,
                detail="Phone number must be in E.164 format (+1XXXXXXXXXX)"
            )

        routes = db.query(TrackedRoute).filter(TrackedRoute.phone_number == phone_number).all()
        return routes
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/tracked-routes/{route_id}")
async def delete_tracked_route(route_id: int, db: Session = Depends(get_db)):
    try:
        route = db.query(TrackedRoute).filter(TrackedRoute.id == route_id).first()
        if not route:
            raise HTTPException(status_code=404, detail="Route not found")
        
        # Mark route as inactive
        route.is_active = False
        db.commit()
        
        # Delete route
        db.delete(route)
        db.commit()
        
        return {"message": "Route tracking stopped and deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/cities/autocomplete")
async def autocomplete_cities(query: str = Query(None)):
    """Return city suggestions based on the query string."""
    if not query:
        return []
    query = query.lower()
    suggestions = [city for city in CITIES if query in city.lower()]
    return suggestions[:5]  # Limit to top 5 matches

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/")
async def root():
    return {"message": "Welcome to AIris-Cab API"}

@app.get("/deploy")
async def deploy():
    return {"status": "deployed"}
