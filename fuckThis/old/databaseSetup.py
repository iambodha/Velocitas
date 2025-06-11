# gmail_database_setup.py
from sqlalchemy import (
    create_engine, MetaData, Table, Column, UUID, String, DateTime, 
    Boolean, Text, ForeignKey, DDL, Integer, BigInteger, 
    Index, CheckConstraint, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import BYTEA, JSONB, ENUM
from sqlalchemy.sql import text
import uuid
import os
from typing import Optional

# Configuration with environment variables
DATABASE_URI = os.getenv(
    "DATABASE_URI", 
    "postgresql+psycopg2://bodha@localhost:5432/email_db"
)

# Connection pooling for scalability
engine = create_engine(
    DATABASE_URI,
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False  # Set to True for debugging
)

metadata = MetaData()

# Define ENUMs for better data integrity
oauth_provider_enum = ENUM(
    'google', 'microsoft', 'apple', 'custom',
    name='oauth_provider_type',
    create_type=False
)

processing_status_enum = ENUM(
    'queued', 'processing', 'completed', 'failed', 'retrying',
    name='processing_status_type',
    create_type=False
)

# Organizations table for multi-tenancy (simplified for Gmail API)
organizations = Table(
    'organizations', metadata,
    Column('org_id', UUID, primary_key=True, default=uuid.uuid4),
    Column('name', String(255), nullable=False),
    Column('domain', String(255), nullable=False, unique=True),
    Column('encryption_key_id', String(255), nullable=False, default='default-key'),
    Column('retention_days', Integer, default=2555),  # 7 years default
    Column('max_users', Integer, default=1000),
    Column('created_at', DateTime, server_default=text('NOW()')),
    Column('is_active', Boolean, default=True),
    Column('subscription_tier', String(50), default='standard'),
    Column('settings', JSONB, default=text("'{}'::jsonb")),
    
    # Constraints
    CheckConstraint('retention_days > 0', name='valid_retention'),
    CheckConstraint('max_users > 0', name='valid_max_users')
)

# Enhanced users table for Gmail API
users = Table(
    'users', metadata,
    Column('user_id', UUID, primary_key=True, default=uuid.uuid4),
    Column('org_id', UUID, ForeignKey('organizations.org_id', ondelete='CASCADE'), nullable=False),
    Column('email', String(320), nullable=False),  # RFC 5321 max length
    Column('oauth_provider', oauth_provider_enum, nullable=False, default='google'),
    Column('oauth_subject', String(255), nullable=False),
    Column('oauth_credentials', JSONB),  # Store encrypted OAuth tokens
    Column('display_name', String(255)),
    Column('created_at', DateTime, server_default=text('NOW()')),
    Column('last_login', DateTime),
    Column('last_sync', DateTime),
    Column('is_active', Boolean, default=True),
    Column('is_verified', Boolean, default=False),
    Column('user_encryption_key_id', String(255)),
    Column('preferences', JSONB, default=text("'{}'::jsonb")),
    Column('quota_used_bytes', BigInteger, default=0),
    Column('quota_limit_bytes', BigInteger, default=10737418240),  # 10GB default
    
    # Multi-column unique constraint
    UniqueConstraint('oauth_provider', 'oauth_subject', name='unique_oauth_user'),
    UniqueConstraint('org_id', 'email', name='unique_org_email'),
    
    # Constraints
    CheckConstraint('quota_used_bytes >= 0', name='valid_quota_used'),
    CheckConstraint('quota_limit_bytes > 0', name='valid_quota_limit')
)

# Simplified emails table for Gmail API caching
emails = Table(
    'emails', metadata,
    Column('email_id', UUID, primary_key=True, default=uuid.uuid4),
    Column('user_id', UUID, ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False),
    Column('org_id', UUID, ForeignKey('organizations.org_id', ondelete='CASCADE'), nullable=False),
    Column('external_id', String(255), nullable=False),  # Gmail message ID
    Column('thread_id', String(255)),  # Gmail thread ID
    Column('raw_email_encrypted', BYTEA, nullable=False),  # Full email JSON from Gmail API
    Column('headers_encrypted', BYTEA),  # Extracted headers
    Column('sender_hash', String(64)),  # For searching without decryption
    Column('subject_hash', String(64)),  # For searching without decryption
    Column('sender_encrypted', BYTEA),
    Column('subject_encrypted', BYTEA),
    Column('received_at', DateTime, nullable=False),
    Column('email_size_bytes', Integer, nullable=False),
    Column('has_attachments', Boolean, default=False),
    Column('attachment_count', Integer, default=0),
    Column('labels', JSONB, default=text("'[]'::jsonb")),  # Gmail labels
    Column('is_processed', Boolean, default=False),
    Column('processing_priority', Integer, default=5),
    Column('created_at', DateTime, server_default=text('NOW()')),
    Column('updated_at', DateTime, server_default=text('NOW()')),
    
    # Unique constraint for Gmail message ID per org
    UniqueConstraint('external_id', 'org_id', name='unique_gmail_message'),
    
    # Constraints
    CheckConstraint('email_size_bytes > 0', name='valid_email_size'),
    CheckConstraint('attachment_count >= 0', name='valid_attachment_count'),
    CheckConstraint('processing_priority BETWEEN 1 AND 10', name='valid_priority')
)

# Email attachments table
email_attachments = Table(
    'email_attachments', metadata,
    Column('attachment_id', UUID, primary_key=True, default=uuid.uuid4),
    Column('email_id', UUID, ForeignKey('emails.email_id', ondelete='CASCADE'), nullable=False),
    Column('org_id', UUID, ForeignKey('organizations.org_id', ondelete='CASCADE'), nullable=False),
    Column('filename_encrypted', BYTEA, nullable=False),
    Column('content_type', String(255)),
    Column('size_bytes', Integer, nullable=False),
    Column('content_encrypted', BYTEA),  # Store in object storage for large files
    Column('storage_location', String(500)),  # S3/Azure blob path
    Column('checksum', String(64), nullable=False),
    Column('created_at', DateTime, server_default=text('NOW()')),
    
    CheckConstraint('size_bytes > 0', name='valid_attachment_size')
)

# Summaries table for AI-generated summaries
summaries = Table(
    'summaries', metadata,
    Column('summary_id', UUID, primary_key=True, default=uuid.uuid4),
    Column('email_id', UUID, ForeignKey('emails.email_id', ondelete='CASCADE'), nullable=False),
    Column('org_id', UUID, ForeignKey('organizations.org_id', ondelete='CASCADE'), nullable=False),
    Column('summary_type', String(50), nullable=False),  # 'brief', 'detailed', 'action_items'
    Column('summary_encrypted', BYTEA, nullable=False),
    Column('confidence_score', Integer),  # AI confidence 0-100
    Column('word_count', Integer),
    Column('created_at', DateTime, server_default=text('NOW()')),
    Column('ai_model_version', String(100), nullable=False),
    Column('processing_time_ms', Integer),
    Column('tokens_used', Integer),
    
    CheckConstraint('confidence_score BETWEEN 0 AND 100', name='valid_confidence'),
    CheckConstraint('word_count >= 0', name='valid_word_count'),
    CheckConstraint('processing_time_ms >= 0', name='valid_processing_time'),
    CheckConstraint('tokens_used >= 0', name='valid_tokens')
)

# Email processing queue for background tasks
processing_queue = Table(
    'processing_queue', metadata,
    Column('queue_id', UUID, primary_key=True, default=uuid.uuid4),
    Column('email_id', UUID, ForeignKey('emails.email_id', ondelete='CASCADE'), nullable=False),
    Column('org_id', UUID, ForeignKey('organizations.org_id', ondelete='CASCADE'), nullable=False),
    Column('task_type', String(100), nullable=False),  # 'summary', 'classification', 'extraction'
    Column('status', processing_status_enum, nullable=False, default='queued'),
    Column('priority', Integer, default=5),
    Column('retry_count', Integer, default=0),
    Column('max_retries', Integer, default=3),
    Column('scheduled_at', DateTime, server_default=text('NOW()')),
    Column('started_at', DateTime),
    Column('completed_at', DateTime),
    Column('error_message', Text),
    Column('result_data', JSONB),
    Column('created_at', DateTime, server_default=text('NOW()')),
    
    CheckConstraint('priority BETWEEN 1 AND 10', name='valid_queue_priority'),
    CheckConstraint('retry_count >= 0', name='valid_retry_count'),
    CheckConstraint('max_retries >= 0', name='valid_max_retries')
)

# Analytics table for email insights
email_analytics = Table(
    'email_analytics', metadata,
    Column('analytics_id', UUID, primary_key=True, default=uuid.uuid4),
    Column('user_id', UUID, ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False),
    Column('org_id', UUID, ForeignKey('organizations.org_id', ondelete='CASCADE'), nullable=False),
    Column('date', DateTime, nullable=False),
    Column('emails_received', Integer, default=0),
    Column('emails_processed', Integer, default=0),
    Column('total_size_bytes', BigInteger, default=0),
    Column('attachments_count', Integer, default=0),
    Column('summary_requests', Integer, default=0),
    Column('top_senders', JSONB, default=text("'[]'::jsonb")),
    Column('category_breakdown', JSONB, default=text("'{}'::jsonb")),
    Column('created_at', DateTime, server_default=text('NOW()')),
    
    # Unique constraint for daily analytics per user
    UniqueConstraint('user_id', 'date', name='unique_daily_analytics'),
    
    CheckConstraint('emails_received >= 0', name='valid_emails_received'),
    CheckConstraint('emails_processed >= 0', name='valid_emails_processed'),
    CheckConstraint('total_size_bytes >= 0', name='valid_total_size')
)

# System logs table for audit and debugging
system_logs = Table(
    'system_logs', metadata,
    Column('log_id', UUID, primary_key=True, default=uuid.uuid4),
    Column('user_id', UUID, ForeignKey('users.user_id', ondelete='SET NULL')),
    Column('org_id', UUID, ForeignKey('organizations.org_id', ondelete='SET NULL')),
    Column('level', String(20), nullable=False),  # 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'
    Column('message', Text, nullable=False),
    Column('module', String(100)),
    Column('function_name', String(100)),
    Column('line_number', Integer),
    Column('request_id', String(100)),
    Column('session_id', String(100)),
    Column('ip_address', String(45)),  # IPv6 compatible
    Column('user_agent', String(500)),
    Column('additional_data', JSONB),
    Column('created_at', DateTime, server_default=text('NOW()')),
    
    CheckConstraint("level IN ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')", name='valid_log_level')
)

# Create indexes for better performance
indexes = [
    # Users table indexes
    Index('idx_users_email', users.c.email),
    Index('idx_users_org_id', users.c.org_id),
    Index('idx_users_last_login', users.c.last_login),
    Index('idx_users_oauth_provider_subject', users.c.oauth_provider, users.c.oauth_subject),
    
    # Emails table indexes
    Index('idx_emails_user_id', emails.c.user_id),
    Index('idx_emails_org_id', emails.c.org_id),
    Index('idx_emails_external_id', emails.c.external_id),
    Index('idx_emails_thread_id', emails.c.thread_id),
    Index('idx_emails_received_at', emails.c.received_at),
    Index('idx_emails_sender_hash', emails.c.sender_hash),
    Index('idx_emails_subject_hash', emails.c.subject_hash),
    Index('idx_emails_is_processed', emails.c.is_processed),
    Index('idx_emails_labels', emails.c.labels, postgresql_using='gin'),
    
    # Attachments indexes
    Index('idx_attachments_email_id', email_attachments.c.email_id),
    Index('idx_attachments_org_id', email_attachments.c.org_id),
    
    # Summaries indexes
    Index('idx_summaries_email_id', summaries.c.email_id),
    Index('idx_summaries_org_id', summaries.c.org_id),
    Index('idx_summaries_type', summaries.c.summary_type),
    
    # Processing queue indexes
    Index('idx_queue_status_priority', processing_queue.c.status, processing_queue.c.priority),
    Index('idx_queue_scheduled_at', processing_queue.c.scheduled_at),
    Index('idx_queue_email_id', processing_queue.c.email_id),
    
    # Analytics indexes
    Index('idx_analytics_user_date', email_analytics.c.user_id, email_analytics.c.date),
    Index('idx_analytics_org_date', email_analytics.c.org_id, email_analytics.c.date),
    
    # System logs indexes
    Index('idx_logs_created_at', system_logs.c.created_at),
    Index('idx_logs_level', system_logs.c.level),
    Index('idx_logs_user_id', system_logs.c.user_id),
    Index('idx_logs_request_id', system_logs.c.request_id),
]

# Function to create all tables and enums
def create_database_schema():
    """Create the entire database schema including enums, tables, and indexes"""
    
    # Create ENUMs first
    oauth_provider_enum.create(engine, checkfirst=True)
    processing_status_enum.create(engine, checkfirst=True)
    
    # Create all tables
    metadata.create_all(engine)
    
    # Create indexes
    for index in indexes:
        try:
            index.create(engine, checkfirst=True)
        except Exception as e:
            print(f"Warning: Could not create index {index.name}: {e}")
    
    print("Database schema created successfully!")

# Function to drop all tables (use with caution!)
def drop_database_schema():
    """Drop the entire database schema - USE WITH CAUTION!"""
    metadata.drop_all(engine)
    
    # Drop ENUMs
    try:
        engine.execute(text("DROP TYPE IF EXISTS oauth_provider_type CASCADE"))
        engine.execute(text("DROP TYPE IF EXISTS processing_status_type CASCADE"))
    except Exception as e:
        print(f"Warning: Could not drop enums: {e}")
    
    print("Database schema dropped!")

# Function to create a default organization for single-user setup
def create_default_organization(name: str = "Default Organization", domain: str = "localhost"):
    """Create a default organization for development/single-user setup"""
    from sqlalchemy import insert
    
    org_id = str(uuid.uuid4())
    
    stmt = insert(organizations).values(
        org_id=org_id,
        name=name,
        domain=domain,
        encryption_key_id="default-key",
        retention_days=2555,
        max_users=1000,
        is_active=True,
        subscription_tier="standard",
        settings={}
    )
    
    with engine.connect() as conn:
        try:
            conn.execute(stmt)
            conn.commit()
            print(f"Default organization created with ID: {org_id}")
            return org_id
        except Exception as e:
            print(f"Error creating default organization: {e}")
            return None

# Function to check database connection
def test_connection():
    """Test database connection"""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1 as test"))
            print("Database connection successful!")
            return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False

# Migration utilities
def add_update_trigger():
    """Add trigger to automatically update 'updated_at' column"""
    trigger_sql = """
    CREATE OR REPLACE FUNCTION update_updated_at_column()
    RETURNS TRIGGER AS $$
    BEGIN
        NEW.updated_at = NOW();
        RETURN NEW;
    END;
    $$ language 'plpgsql';
    
    DROP TRIGGER IF EXISTS update_emails_updated_at ON emails;
    CREATE TRIGGER update_emails_updated_at
        BEFORE UPDATE ON emails
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    """
    
    with engine.connect() as conn:
        try:
            conn.execute(text(trigger_sql))
            conn.commit()
            print("Update trigger created successfully!")
        except Exception as e:
            print(f"Error creating update trigger: {e}")

# Main execution
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "create":
            print("Creating database schema...")
            create_database_schema()
            add_update_trigger()
            
        elif command == "drop":
            confirm = input("Are you sure you want to drop all tables? (yes/no): ")
            if confirm.lower() == "yes":
                drop_database_schema()
            else:
                print("Operation cancelled.")
                
        elif command == "test":
            test_connection()
            
        elif command == "setup":
            print("Setting up database for development...")
            create_database_schema()
            add_update_trigger()
            create_default_organization()
            
        else:
            print("Usage: python gmail_database_setup.py [create|drop|test|setup]")
    else:
        print("Usage: python gmail_database_setup.py [create|drop|test|setup]")
        print("Commands:")
        print("  create - Create all tables and indexes")
        print("  drop   - Drop all tables (use with caution!)")
        print("  test   - Test database connection")
        print("  setup  - Complete setup for development (create + default org)")