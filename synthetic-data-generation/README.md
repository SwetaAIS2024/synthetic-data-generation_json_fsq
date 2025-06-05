# Synthetic Data Generation Demos

A modern web application for synthetic data generation with a React frontend and FastAPI backend.

## Project Structure

```
demos/synthetic-data-generation/
├── backend/            # Python FastAPI backend
│   ├── api/            # API endpoints
│   ├── models/         # Data models
│   ├── modules/        # Core functionality modules
│   ├── config/         # Configuration settings
│   ├── datasets/       # Dataset storage
│   ├── main.py         # Entry point for the API
│   └── requirements.txt # Python dependencies
├── web/                # React frontend
│   ├── src/            # React source code
│   ├── public/         # Static assets
│   └── package.json    # NPM dependencies
└── venv/               # Python virtual environment
```

## Getting Started

### Environment Setup

Before running the application, you need to set up environment variables. Create a `.env` file in the `backend` directory with the following variables:

```
FIREWORKS_API_KEY=your_secret_key_here
FIREWORKS_ACCOUNT_ID=your_acct_id_here
```

Adjust these values according to your setup.

### Backend Setup

1. Create and activate the virtual environment:
   ```bash
   cd demos/synthetic-data-generation
   python -m venv venv
   source venv/bin/activate   # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

3. Run the backend server:
   ```bash
   docker compose build
   docker compose up
   ```

### Frontend Setup

1. Install dependencies:
   ```bash
   cd web
   npm install
   ```

2. Start the development server:
   ```bash
   npm run dev
   ```
   The frontend will be available at http://localhost:3001.

## Features

- FastAPI backend with automatic API documentation
- React frontend with TanStack Router
- Tailwind CSS for styling
- WebSocket support for real-time updates
- Docker support for containerized deployment
