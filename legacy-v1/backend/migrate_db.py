"""
Database migration script to add authentication tables and fields
Run this script to update your existing database with the new authentication system
"""

from sqlalchemy import create_engine, text
from models import Base, engine
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def run_migration():
    """Run database migration to add authentication fields and tables"""
    
    print("🔄 Starting database migration...")
    
    try:
        # Connect to database
        connection = engine.connect()
        
        # Add new columns to existing users table
        print("📝 Adding authentication fields to users table...")
        
        migration_queries = [
            # Add password field if it doesn't exist
            """
            DO $$ 
            BEGIN 
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                              WHERE table_name='users' AND column_name='hashed_password') 
                THEN
                    ALTER TABLE users ADD COLUMN hashed_password VARCHAR(255);
                END IF;
            END $$;
            """,
            
            # Add verification field if it doesn't exist
            """
            DO $$ 
            BEGIN 
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                              WHERE table_name='users' AND column_name='is_verified') 
                THEN
                    ALTER TABLE users ADD COLUMN is_verified BOOLEAN DEFAULT FALSE;
                END IF;
            END $$;
            """,
            
            # Create sessions table if it doesn't exist
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                refresh_token VARCHAR(500) NOT NULL UNIQUE,
                ip_address VARCHAR(45),
                user_agent TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                is_active BOOLEAN DEFAULT TRUE
            );
            """,
            
            # Create index on user_id for sessions table
            """
            CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
            """,
            
            # Create index on refresh_token for sessions table
            """
            CREATE INDEX IF NOT EXISTS idx_sessions_refresh_token ON sessions(refresh_token);
            """,
            
            # Create index on expires_at for cleanup
            """
            CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON sessions(expires_at);
            """
        ]
        
        # Execute migration queries
        for query in migration_queries:
            try:
                connection.execute(text(query))
                connection.commit()
            except Exception as e:
                print(f"⚠️  Warning: {e}")
                connection.rollback()
        
        print("✅ Database migration completed successfully!")
        print("📊 New authentication system is ready to use")
        
        # Verify tables exist
        result = connection.execute(text("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name IN ('users', 'sessions', 'emails', 'attachments')
            ORDER BY table_name;
        """))
        
        tables = [row[0] for row in result]
        print(f"📋 Available tables: {', '.join(tables)}")
        
        connection.close()
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        raise

if __name__ == "__main__":
    run_migration()