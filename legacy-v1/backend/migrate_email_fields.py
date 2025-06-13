"""
Database migration script to add new email fields: is_starred, is_read, urgency
Run this script to update your existing emails table with the new fields
"""

from sqlalchemy import create_engine, text
from models import engine
import os

def run_email_fields_migration():
    """Run database migration to add new email fields"""
    
    print("🔄 Starting email fields migration...")
    
    try:
        # Connect to database
        connection = engine.connect()
        
        print("📝 Adding new fields to emails table...")
        
        migration_queries = [
            # Add is_starred field if it doesn't exist
            """
            DO $$ 
            BEGIN 
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                              WHERE table_name='emails' AND column_name='is_starred') 
                THEN
                    ALTER TABLE emails ADD COLUMN is_starred BOOLEAN DEFAULT FALSE;
                END IF;
            END $$;
            """,
            
            # Add is_read field if it doesn't exist
            """
            DO $$ 
            BEGIN 
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                              WHERE table_name='emails' AND column_name='is_read') 
                THEN
                    ALTER TABLE emails ADD COLUMN is_read BOOLEAN DEFAULT FALSE;
                END IF;
            END $$;
            """,
            
            # Add urgency field if it doesn't exist
            """
            DO $$ 
            BEGIN 
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                              WHERE table_name='emails' AND column_name='urgency') 
                THEN
                    ALTER TABLE emails ADD COLUMN urgency INTEGER DEFAULT 50;
                END IF;
            END $$;
            """,
            
            # Create index on is_starred for faster filtering
            """
            CREATE INDEX IF NOT EXISTS idx_emails_is_starred ON emails(is_starred);
            """,
            
            # Create index on is_read for faster filtering
            """
            CREATE INDEX IF NOT EXISTS idx_emails_is_read ON emails(is_read);
            """,
            
            # Create index on urgency for sorting
            """
            CREATE INDEX IF NOT EXISTS idx_emails_urgency ON emails(urgency);
            """,
            
            # Create index on category for filtering
            """
            CREATE INDEX IF NOT EXISTS idx_emails_category ON emails(category);
            """
        ]
        
        # Execute migration queries
        for query in migration_queries:
            try:
                connection.execute(text(query))
                connection.commit()
                print("✅ Migration query executed successfully")
            except Exception as e:
                print(f"⚠️  Warning: {e}")
                connection.rollback()
        
        print("✅ Email fields migration completed successfully!")
        
        # Verify new columns exist
        result = connection.execute(text("""
            SELECT column_name, data_type, column_default 
            FROM information_schema.columns 
            WHERE table_name = 'emails' 
            AND column_name IN ('is_starred', 'is_read', 'urgency', 'category')
            ORDER BY column_name;
        """))
        
        columns = [(row[0], row[1], row[2]) for row in result]
        print("📋 New email fields:")
        for col_name, col_type, col_default in columns:
            print(f"  - {col_name}: {col_type} (default: {col_default})")
        
        connection.close()
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        raise

if __name__ == "__main__":
    run_email_fields_migration()