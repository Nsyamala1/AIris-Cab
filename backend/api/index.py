from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import sys
import os
import traceback
from mangum import Mangum

# Add the parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for now
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Error handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    print(f"Validation error: {exc}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": exc.body},
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    print(f"Unhandled error: {exc}")
    print("Traceback:")
    print(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "type": str(type(exc).__name__),
            "message": str(exc)
        },
    )

# Add root route with error handling
@app.get("/")
async def root():
    try:
        return {"message": "Welcome to AIris-Cab API", "status": "healthy"}
    except Exception as e:
        print(f"Error in root route: {e}")
        print(traceback.format_exc())
        raise

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Create handler for AWS Lambda
handler = Mangum(app, lifespan="off")
