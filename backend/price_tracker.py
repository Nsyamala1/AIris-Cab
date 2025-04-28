from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.orm import Session
from models import SessionLocal, TrackedRoute, PriceHistory
import os
from dotenv import load_dotenv
from utils import calculate_price, get_distance_matrix
from twilio.rest import Client

load_dotenv()

# Twilio configuration
twilio_client = Client(
    os.getenv("TWILIO_ACCOUNT_SID"),
    os.getenv("TWILIO_AUTH_TOKEN")
)
TWILIO_FROM_NUMBER = os.getenv("TWILIO_FROM_NUMBER")

async def check_price_and_notify(route_id: int, db: Session):
    """Check current prices for a tracked route and notify if below target"""
    route = db.query(TrackedRoute).filter(TrackedRoute.id == route_id).first()
    if not route or not route.is_active:
        return
    
    # Get current prices
    route_data = get_mock_distance(route.pickup, route.dropoff)
    current_prices = {
        "Uber": calculate_price(route_data['distance'], 'Uber'),
        "Lyft": calculate_price(route_data['distance'], 'Lyft'),
        "UberXL": calculate_price(route_data['distance'], 'UberXL'),
        "Bike": calculate_price(route_data['distance'], 'Bike') if route.passenger_count <= 2 else float('inf')
    }
    
    # Find the cheapest price
    cheapest_price = min(current_prices.values())
    cheapest_service = min(current_prices.items(), key=lambda x: x[1])[0]
    
    # Check if price is below target
    if cheapest_price <= route.target_price:
        # Send SMS notification
        message = twilio_client.messages.create(
            body=f"🚗 Price Alert! Your ride from {route.pickup} to {route.dropoff} is now ${cheapest_price:.2f} with {cheapest_service}. Book now to get this rate!",
            from_=TWILIO_FROM_NUMBER,
            to=route.phone_number
        )
        
        # Mark route as notified
        route.is_active = False
        db.commit()
    
    # Save price history
    for service, price in current_prices.items():
        history = PriceHistory(
            route_id=route_id,
            service=service,
            price=price
        )
        db.add(history)
    
    # Find cheapest valid option
    valid_prices = {
        service: price for service, price in current_prices.items()
        if (service != "Bike" or route.passenger_count <= 2) and
        (service != "UberXL" or route.passenger_count <= 7) and
        (service not in ["Uber", "Lyft"] or route.passenger_count <= 4)
    }
    
    cheapest_price = min(valid_prices.values())
    cheapest_service = min(valid_prices.items(), key=lambda x: x[1])[0]
    
    # Check if price is below target
    if cheapest_price <= route.target_price:
        # Send email notification
        message = MessageSchema(
            subject="Price Alert: Your ride is now cheaper!",
            recipients=[route.email],
            body=f"""Good news! The price for your route from {route.pickup} to {route.dropoff} 
            has dropped to ${cheapest_price:.2f} with {cheapest_service}.
            
            This is below your target price of ${route.target_price:.2f}.
            
            Book now to lock in this rate!
            """
        )
        await fastmail.send_message(message)
        
        # Deactivate the route after notification
        route.is_active = False
        
    db.commit()

# Initialize scheduler
scheduler = AsyncIOScheduler()

def start_price_tracking(route_id: int):
    """Start tracking prices for a route every 15 minutes"""
    db = SessionLocal()
    scheduler.add_job(
        check_price_and_notify,
        'interval',
        minutes=15,
        args=[route_id, db],
        id=f"route_{route_id}"
    )

def stop_price_tracking(route_id: int):
    """Stop tracking prices for a route"""
    scheduler.remove_job(f"route_{route_id}")

# Start the scheduler
scheduler.start()
