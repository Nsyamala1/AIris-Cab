# AIris-Cab Price Comparison

A real-time cab price comparison application that fetches prices from various ride-sharing services and provides AI-powered assistance.

## Features

- Real-time price comparison between ride-sharing services
- Address to coordinates conversion using Google Maps API
- AI-powered chat interface for assistance
- Modern, responsive UI built with React and Material UI

## Prerequisites

- Node.js (v14 or higher)
- Python (v3.8 or higher)
- API Keys for:
  - Google Maps API
  - OpenAI API
  - Lyft API (Client ID and Secret)

## Setup

### Backend Setup

1. Navigate to the backend directory:
```bash
cd backend
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file based on `.env.example` and add your API keys:
```bash
cp .env.example .env
```

5. Start the backend server:
```bash
uvicorn main:app --reload
```

### Frontend Setup

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm start
```

The application will be available at:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

## API Integration Notes

- The Lyft API integration requires OAuth2 authentication
- For Uber integration, we'll need to implement a workaround as direct API access might be limited
- Google Maps API is used for geocoding addresses to coordinates
- OpenAI GPT is used for the chat interface

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a new Pull Request
