from fastapi import FastAPI, HTTPException, Query, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session
from models import SessionLocal, TrackedRoute, PriceHistory
from price_tracker import check_price_and_notify
from utils import calculate_price, get_distance_matrix
from datetime import datetime
import traceback
import os

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

# List of major cities for autocomplete
CITIES = [
    # US Cities
    "New York", "Los Angeles", "Chicago", "Houston", "Phoenix",
    "Philadelphia", "San Antonio", "San Diego", "Dallas", "San Jose",
    "Austin", "Jacksonville", "Fort Worth", "Columbus", "San Francisco",
    "Charlotte", "Indianapolis", "Seattle", "Denver", "Boston",
    # Indian Cities
    "Mumbai", "Delhi", "Bangalore", "Hyderabad", "Chennai",
    "Kolkata", "Pune", "Ahmedabad", "Surat", "Jaipur",
    "Lucknow", "Kanpur", "Nagpur", "Indore", "Thane",
    "Bhopal", "Visakhapatnam", "Pimpri-Chinchwad", "Patna", "Vadodara"
]

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
async def compare_prices(location: LocationRequest, request: Request):
    print(f"Received compare-prices request: {location}")
    try:
        if not os.getenv('GOOGLE_MAPS_API_KEY'):
            return JSONResponse(
                status_code=500,
                content={"error": "Google Maps API key not configured"}
            )

        # Get real distance and duration from Google Maps API
        try:
            route_data = get_distance_matrix(location.pickup_address, location.dropoff_address)
        except Exception as e:
            error_message = str(e)
            if 'API key' in error_message:
                return JSONResponse(
                    status_code=500,
                    content={"error": f"Google Maps API error: {error_message}"}
                )
            raise e
        
        # Get all available services based on passenger count
        available_services = []
        
        # Calculate prices for regular services
        base_distance = route_data['distance']
        base_duration = route_data['duration']
        
        # Regular Uber/Lyft for 1-4 passengers
        if location.passenger_count <= 4:
            uber_price = calculate_price(base_distance, base_duration // 60, 'Uber')
            lyft_price = calculate_price(base_distance, base_duration // 60, 'Lyft')
            
            available_services.extend([
                {
                    "service": "Uber",
                    "price_estimate": f"${uber_price:.2f}",
                    "duration": base_duration,
                    "duration_in_traffic": route_data.get('duration_in_traffic'),
                    "distance": base_distance,
                    "pickup": location.pickup_address,
                    "dropoff": location.dropoff_address,
                    "recommended": False,  # Will be updated later
                    "capacity": "1-4 passengers",
                    "urls": get_service_urls("Uber", location.pickup_address, location.dropoff_address)
                },
                {
                    "service": "Lyft",
                    "price_estimate": f"${lyft_price:.2f}",
                    "duration": base_duration,
                    "duration_in_traffic": route_data.get('duration_in_traffic'),
                    "distance": base_distance,
                    "pickup": location.pickup_address,
                    "dropoff": location.dropoff_address,
                    "recommended": False,  # Will be updated later
                    "capacity": "1-4 passengers",
                    "urls": get_service_urls("Lyft", location.pickup_address, location.dropoff_address)
                }
            ])

        # XL services for 5+ passengers
        if location.passenger_count >= 5:
            uberxl_price = calculate_price(base_distance, base_duration // 60, 'UberXL')
            lyftxl_price = calculate_price(base_distance, base_duration // 60, 'UberXL')
            
            available_services.extend([
                {
                    "service": "UberXL",
                    "price_estimate": f"${uberxl_price:.2f}",
                    "duration": base_duration,
                    "duration_in_traffic": route_data.get('duration_in_traffic'),
                    "distance": base_distance,
                    "pickup": location.pickup_address,
                    "dropoff": location.dropoff_address,
                    "recommended": False,  # Will be updated later
                    "capacity": "1-7 passengers",
                    "urls": get_service_urls("Uber", location.pickup_address, location.dropoff_address)
                },
                {
                    "service": "LyftXL",
                    "price_estimate": f"${lyftxl_price:.2f}",
                    "duration": base_duration,
                    "duration_in_traffic": route_data.get('duration_in_traffic'),
                    "distance": base_distance,
                    "pickup": location.pickup_address,
                    "dropoff": location.dropoff_address,
                    "recommended": False,
                    "capacity": "5-6 passengers",
                    "urls": get_service_urls("Lyft", location.pickup_address, location.dropoff_address)
                }
            ])
        
        # Find the cheapest service and mark it as recommended
        if available_services:
            # Convert price strings to floats for comparison
            for service in available_services:
                service['price_float'] = float(service['price_estimate'].replace('$', ''))
            
            # Filter services that can accommodate the passenger count
            valid_services = [service for service in available_services 
                            if int(service['capacity'].split('-')[1].split()[0]) >= location.passenger_count]
            
            if valid_services:
                min_price = min(service['price_float'] for service in valid_services)
                for service in valid_services:
                    if service['price_float'] == min_price:
                        service['recommended'] = True
                        break
            
            # Remove the temporary price_float field
            for service in available_services:
                del service['price_float']
        
        # Sort services by price
        available_services.sort(key=lambda x: float(x['price_estimate'].replace('$', '')))
        
        return {
            "services": available_services,
            "distance": route_data['distance'],
            "duration": route_data['duration'],
            "duration_in_traffic": route_data.get('duration_in_traffic', route_data['duration'])
        }
    except Exception as e:
        print(f"Error in compare-prices: {e}")
        print("Request body:", location)
        print("Traceback:")
        print(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error",
                "type": str(type(e).__name__),
                "message": str(e)
            }
        )

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
        print(f"Error in compare-prices: {e}")
        print("Request body:", location)
        print("Traceback:")
        print(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error",
                "type": str(type(e).__name__),
                "message": str(e)
            }
        )

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
        print(f"Error in compare-prices: {e}")
        print("Request body:", location)
        print("Traceback:")
        print(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error",
                "type": str(type(e).__name__),
                "message": str(e)
            }
        )

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
        print(f"Error in compare-prices: {e}")
        print("Request body:", location)
        print("Traceback:")
        print(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error",
                "type": str(type(e).__name__),
                "message": str(e)
            }
        )

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
