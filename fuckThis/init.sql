-- Drop existing resources if they exist (to handle re-runs)
DROP DATABASE IF EXISTS gmail_api_db;
DROP USER IF EXISTS gmail_user;

-- Create database and user
CREATE DATABASE gmail_api_db;
CREATE USER gmail_user WITH ENCRYPTED PASSWORD 'secure_password_123';
GRANT ALL PRIVILEGES ON DATABASE gmail_api_db TO gmail_user;

-- Connect to the database
\c gmail_api_db;

-- Grant schema permissions
GRANT ALL ON SCHEMA public TO gmail_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO gmail_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO gmail_user;

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create indexes for better performance (will be created by SQLAlchemy, but can be added manually)
-- These are handled by the SQLAlchemy models, but listed here for reference:

-- Users table indexes:
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_google_id ON users(google_user_id);
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_email ON users(email);
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_active ON users(is_active);

-- Emails table indexes:
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_email_user_gmail_id ON emails(user_id, gmail_message_id);
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_email_user_date ON emails(user_id, date_sent);
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_email_user_read ON emails(user_id, is_read);
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_email_sender ON emails(sender);

-- Full-text search index for email content (optional advanced feature)
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_email_search ON emails USING gin(to_tsvector('english', subject || ' ' || COALESCE(body_text, '')));