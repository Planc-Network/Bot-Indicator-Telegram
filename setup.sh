#!/bin/bash

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create necessary directories
mkdir -p logs
mkdir -p data

# Initialize database
python -c "from src.database.connection import DatabaseManager; DatabaseManager().create_tables()"

# Create .env file if not exists
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Please update .env with your credentials"
fi

echo "Setup completed successfully!" 