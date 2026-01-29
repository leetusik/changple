-- Changple AI Database Initialization
-- This script runs on first container startup

-- Create additional databases
CREATE DATABASE changple_langgraph;

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE changple TO changple;
GRANT ALL PRIVILEGES ON DATABASE changple_langgraph TO changple;

-- Connect to main database and create extensions
\c changple;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Connect to langgraph database and create extensions
\c changple_langgraph;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
