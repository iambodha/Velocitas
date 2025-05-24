# enterprise_database_setup.py
from sqlalchemy import (
    create_engine, MetaData, Table, Column, UUID, String, DateTime, 
    Boolean, Text, ForeignKey, DDL, event, Integer, BigInteger, 
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

# Organizations table for multi-tenancy
organizations = Table(
    'organizations', metadata,
    Column('org_id', UUID, primary_key=True, default=uuid.uuid4),
    Column('name', String(255), nullable=False),
    Column('domain', String(255), nullable=False, unique=True),
    Column('encryption_key_id', String(255), nullable=False),  # KMS key ID
    Column('retention_days', Integer, default=2555),  # 7 years default
    Column('max_users', Integer, default=1000),
    Column('created_at', DateTime, server_default=text('NOW()')),
    Column('is_active', Boolean, default=True),
    Column('subscription_tier', String(50), default='standard'),
    Column('settings', JSONB),  # Org-specific settings
    
    # Constraints
    CheckConstraint('retention_days > 0', name='valid_retention'),
    CheckConstraint('max_users > 0', name='valid_max_users')
)

# Enhanced users table
users = Table(
    'users', metadata,
    Column('user_id', UUID, primary_key=True, default=uuid.uuid4),
    Column('org_id', UUID, ForeignKey('organizations.org_id', ondelete='CASCADE'), nullable=False),
    Column('email', String(320), nullable=False),  # RFC 5321 max length
    Column('oauth_provider', oauth_provider_enum, nullable=False),
    Column('oauth_subject', String(255), nullable=False),
    Column('display_name', String(255)),
    Column('created_at', DateTime, server_default=text('NOW()')),
    Column('last_login', DateTime),
    Column('last_sync', DateTime),
    Column('is_active', Boolean, default=True),
    Column('is_verified', Boolean, default=False),
    Column('user_encryption_key_id', String(255)),  # Individual user key
    Column('preferences', JSONB),
    Column('quota_used_bytes', BigInteger, default=0),
    Column('quota_limit_bytes', BigInteger, default=10737418240),  # 10GB default
    
    # Multi-column unique constraint
    UniqueConstraint('oauth_provider', 'oauth_subject', name='unique_oauth_user'),
    UniqueConstraint('org_id', 'email', name='unique_org_email'),
    
    # Constraints
    CheckConstraint('quota_used_bytes >= 0', name='valid_quota_used'),
    CheckConstraint('quota_limit_bytes > 0', name='valid_quota_limit')
)

# Email attachments table with org_id included
email_attachments = Table(
    'email_attachments', metadata,
    Column('attachment_id', UUID, primary_key=True, default=uuid.uuid4),
    Column('email_id', UUID, nullable=False),
    Column('org_id', UUID, nullable=False),  # Add org_id column
    Column('filename_encrypted', BYTEA, nullable=False),
    Column('content_type', String(255)),
    Column('size_bytes', Integer, nullable=False),
    Column('content_encrypted', BYTEA),  # Store in object storage for large files
    Column('storage_location', String(500)),  # S3/Azure blob path
    Column('checksum', String(64), nullable=False),
    Column('created_at', DateTime, server_default=text('NOW()')),
    
    CheckConstraint('size_bytes > 0', name='valid_attachment_size')
)

# Enhanced summaries table with org_id included
summaries = Table(
    'summaries', metadata,
    Column('summary_id', UUID, primary_key=True, default=uuid.uuid4),
    Column('email_id', UUID, nullable=False),
    Column('org_id', UUID, nullable=False),  # Add org_id column
    Column('summary_type', String(50), nullable=False),  # 'brief', 'detailed', 'action_items'
    Column('summary_encrypted', BYTEA, nullable=False),
    Column('confidence_score', Integer),  # AI confidence 0-100
    Column('word_count', Integer),
    Column('created_at', DateTime, server_default=text('NOW()')),
    Column('ai_model_version', String(100), nullable=False),
    Column('processing_time_ms', Integer),
    Column('tokens_used', Integer),
    
    CheckConstraint('confidence_score BETWEEN 0 AND 100', name='valid_confidence'),
    CheckConstraint('word_count >= 0', name='valid_word_count')
)

# Processing queue with org_id included
processing_queue = Table(
    'processing_queue', metadata,
    Column('task_id', UUID, primary_key=True, default=uuid.uuid4),
    Column('email_id', UUID, nullable=False),
    Column('org_id', UUID, nullable=False),  # Add org_id column
    Column('task_type', String(50), nullable=False),  # 'summarize', 'extract', 'classify'
    Column('status', processing_status_enum, nullable=False, default='queued'),
    Column('priority', Integer, default=5),
    Column('created_at', DateTime, server_default=text('NOW()')),
    Column('started_at', DateTime),
    Column('completed_at', DateTime),
    Column('retries', Integer, default=0),
    Column('max_retries', Integer, default=3),
    Column('error_message', Text),
    Column('worker_id', String(255)),
    Column('estimated_duration_ms', Integer),
    
    CheckConstraint('retries >= 0', name='valid_retries'),
    CheckConstraint('max_retries >= 0', name='valid_max_retries'),
    CheckConstraint('priority BETWEEN 1 AND 10', name='valid_task_priority')
)

# Data retention policies table
data_retention = Table(
    'data_retention_policies', metadata,
    Column('policy_id', UUID, primary_key=True, default=uuid.uuid4),
    Column('org_id', UUID, ForeignKey('organizations.org_id', ondelete='CASCADE'), nullable=False),
    Column('data_type', String(50), nullable=False),  # 'emails', 'summaries', 'audit_logs'
    Column('retention_days', Integer, nullable=False),
    Column('auto_delete', Boolean, default=True),
    Column('archive_before_delete', Boolean, default=True),
    Column('created_at', DateTime, server_default=text('NOW()')),
    Column('updated_at', DateTime, server_default=text('NOW()')),
    
    UniqueConstraint('org_id', 'data_type', name='unique_org_data_type'),
    CheckConstraint('retention_days > 0', name='valid_retention_days')
)

# Encryption key rotation log
key_rotation_log = Table(
    'key_rotation_log', metadata,
    Column('rotation_id', UUID, primary_key=True, default=uuid.uuid4),
    Column('org_id', UUID, ForeignKey('organizations.org_id', ondelete='CASCADE'), nullable=False),
    Column('old_key_id', String(255), nullable=False),
    Column('new_key_id', String(255), nullable=False),
    Column('rotation_date', DateTime, server_default=text('NOW()')),
    Column('status', String(50), nullable=False),  # 'in_progress', 'completed', 'failed'
    Column('records_migrated', BigInteger, default=0),
    Column('total_records', BigInteger),
    Column('completed_at', DateTime)
)

def create_extensions():
    """Create required PostgreSQL extensions"""
    extensions_sql = DDL("""
        CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
        CREATE EXTENSION IF NOT EXISTS "pg_trgm";
        CREATE EXTENSION IF NOT EXISTS "btree_gin";
    """)
    return extensions_sql

def drop_existing_tables():
    """Drop existing tables if they exist (for clean setup)"""
    drop_sql = DDL("""
        -- Drop tables in reverse dependency order
        DROP TABLE IF EXISTS key_rotation_log CASCADE;
        DROP TABLE IF EXISTS data_retention_policies CASCADE;
        DROP TABLE IF EXISTS processing_queue CASCADE;
        DROP TABLE IF EXISTS summaries CASCADE;
        DROP TABLE IF EXISTS email_attachments CASCADE;
        DROP TABLE IF EXISTS emails CASCADE;
        DROP TABLE IF EXISTS audit_logs CASCADE;
        DROP TABLE IF EXISTS users CASCADE;
        DROP TABLE IF EXISTS organizations CASCADE;
        
        -- Drop partition tables if they exist
        DROP TABLE IF EXISTS emails_part_0 CASCADE;
        DROP TABLE IF EXISTS emails_part_1 CASCADE;
        DROP TABLE IF EXISTS emails_part_2 CASCADE;
        DROP TABLE IF EXISTS emails_part_3 CASCADE;
        DROP TABLE IF EXISTS emails_part_4 CASCADE;
        DROP TABLE IF EXISTS emails_part_5 CASCADE;
        DROP TABLE IF EXISTS emails_part_6 CASCADE;
        DROP TABLE IF EXISTS emails_part_7 CASCADE;
        
        DROP TABLE IF EXISTS audit_logs_y2024m12 CASCADE;
        DROP TABLE IF EXISTS audit_logs_y2025m01 CASCADE;
        DROP TABLE IF EXISTS audit_logs_y2025m02 CASCADE;
        DROP TABLE IF EXISTS audit_logs_y2025m03 CASCADE;
        DROP TABLE IF EXISTS audit_logs_y2025m04 CASCADE;
        DROP TABLE IF EXISTS audit_logs_y2025m05 CASCADE;
        DROP TABLE IF EXISTS audit_logs_y2025m06 CASCADE;
    """)
    return drop_sql

def create_partitioned_tables():
    """Create partitioned tables that can't be defined with SQLAlchemy"""
    partitioned_tables_sql = DDL("""
        -- Create emails table with hash partitioning
        CREATE TABLE emails (
            email_id UUID DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL,
            org_id UUID NOT NULL,
            external_id VARCHAR(255),
            thread_id VARCHAR(255),
            raw_email_encrypted BYTEA NOT NULL,
            headers_encrypted BYTEA,
            sender_hash VARCHAR(64),
            subject_hash VARCHAR(64),
            sender_encrypted BYTEA,
            subject_encrypted BYTEA,
            received_at TIMESTAMP NOT NULL,
            email_size_bytes INTEGER NOT NULL CHECK (email_size_bytes > 0),
            has_attachments BOOLEAN DEFAULT FALSE,
            attachment_count INTEGER DEFAULT 0 CHECK (attachment_count >= 0),
            labels JSONB,
            is_processed BOOLEAN DEFAULT FALSE,
            processing_priority INTEGER DEFAULT 5 CHECK (processing_priority BETWEEN 1 AND 10),
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW(),
            
            -- Composite primary key that includes the partition key
            PRIMARY KEY (email_id, org_id),
            
            -- All unique constraints must include the partitioning column (org_id)
            UNIQUE (external_id, org_id),
            UNIQUE (thread_id, org_id)
        ) PARTITION BY HASH (org_id);
        
        -- Create email partitions
        CREATE TABLE emails_part_0 PARTITION OF emails
            FOR VALUES WITH (MODULUS 8, REMAINDER 0);
        CREATE TABLE emails_part_1 PARTITION OF emails
            FOR VALUES WITH (MODULUS 8, REMAINDER 1);
        CREATE TABLE emails_part_2 PARTITION OF emails
            FOR VALUES WITH (MODULUS 8, REMAINDER 2);
        CREATE TABLE emails_part_3 PARTITION OF emails
            FOR VALUES WITH (MODULUS 8, REMAINDER 3);
        CREATE TABLE emails_part_4 PARTITION OF emails
            FOR VALUES WITH (MODULUS 8, REMAINDER 4);
        CREATE TABLE emails_part_5 PARTITION OF emails
            FOR VALUES WITH (MODULUS 8, REMAINDER 5);
        CREATE TABLE emails_part_6 PARTITION OF emails
            FOR VALUES WITH (MODULUS 8, REMAINDER 6);
        CREATE TABLE emails_part_7 PARTITION OF emails
            FOR VALUES WITH (MODULUS 8, REMAINDER 7);
        
        -- Create audit_logs table with range partitioning
        CREATE TABLE audit_logs (
            log_id UUID DEFAULT gen_random_uuid(),
            org_id UUID NOT NULL,
            user_id UUID,
            action VARCHAR(100) NOT NULL,
            resource_type VARCHAR(50) NOT NULL,
            resource_id UUID,
            timestamp TIMESTAMP DEFAULT NOW(),
            ip_address VARCHAR(45),
            user_agent TEXT,
            success BOOLEAN NOT NULL,
            error_code VARCHAR(50),
            additional_data JSONB,
            session_id UUID,
            partition_date DATE DEFAULT DATE_TRUNC('month', NOW()),
            
            -- Composite primary key that includes the partition key
            PRIMARY KEY (log_id, partition_date)
        ) PARTITION BY RANGE (partition_date);
        
        -- Create initial audit log partitions for current and next 6 months
        CREATE TABLE audit_logs_y2024m12 PARTITION OF audit_logs
            FOR VALUES FROM ('2024-12-01') TO ('2025-01-01');
        CREATE TABLE audit_logs_y2025m01 PARTITION OF audit_logs
            FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
        CREATE TABLE audit_logs_y2025m02 PARTITION OF audit_logs
            FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');
        CREATE TABLE audit_logs_y2025m03 PARTITION OF audit_logs
            FOR VALUES FROM ('2025-03-01') TO ('2025-04-01');
        CREATE TABLE audit_logs_y2025m04 PARTITION OF audit_logs
            FOR VALUES FROM ('2025-04-01') TO ('2025-05-01');
        CREATE TABLE audit_logs_y2025m05 PARTITION OF audit_logs
            FOR VALUES FROM ('2025-05-01') TO ('2025-06-01');
        CREATE TABLE audit_logs_y2025m06 PARTITION OF audit_logs
            FOR VALUES FROM ('2025-06-01') TO ('2025-07-01');
        
        -- Create unique indexes that include partition keys
        CREATE UNIQUE INDEX idx_emails_email_id ON emails (email_id, org_id);
        CREATE UNIQUE INDEX idx_audit_logs_log_id ON audit_logs (log_id, partition_date);
    """)
    return partitioned_tables_sql

def add_foreign_key_constraints():
    """Add foreign key constraints after all tables are created"""
    fk_sql = DDL("""
        -- Add foreign keys that reference both email_id and org_id
        ALTER TABLE email_attachments 
        ADD CONSTRAINT fk_email_attachments_email_id 
        FOREIGN KEY (email_id, org_id) REFERENCES emails(email_id, org_id) ON DELETE CASCADE;
        
        ALTER TABLE summaries 
        ADD CONSTRAINT fk_summaries_email_id 
        FOREIGN KEY (email_id, org_id) REFERENCES emails(email_id, org_id) ON DELETE CASCADE;
        
        ALTER TABLE processing_queue 
        ADD CONSTRAINT fk_processing_queue_email_id 
        FOREIGN KEY (email_id, org_id) REFERENCES emails(email_id, org_id) ON DELETE CASCADE;
        
        -- Add foreign key constraint for emails to users
        ALTER TABLE emails 
        ADD CONSTRAINT fk_emails_user_id 
        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE;
        
        ALTER TABLE emails 
        ADD CONSTRAINT fk_emails_org_id 
        FOREIGN KEY (org_id) REFERENCES organizations(org_id) ON DELETE CASCADE;
    """)
    return fk_sql

def create_security_policies():
    """Create comprehensive Row Level Security policies"""
    security_sql = DDL("""
        -- Create application roles
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'app_read') THEN
                CREATE ROLE app_read NOLOGIN;
            END IF;
            IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'app_write') THEN
                CREATE ROLE app_write NOLOGIN;
            END IF;
            IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'app_admin') THEN
                CREATE ROLE app_admin NOLOGIN;
            END IF;
        END
        $$;
        
        -- Grant basic permissions
        GRANT CONNECT ON DATABASE email_db TO app_read, app_write, app_admin;
        GRANT USAGE ON SCHEMA public TO app_read, app_write, app_admin;
        GRANT SELECT ON ALL TABLES IN SCHEMA public TO app_read;
        GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_write;
        GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO app_admin;
        
        -- Enable RLS on all sensitive tables
        ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
        ALTER TABLE users ENABLE ROW LEVEL SECURITY;
        ALTER TABLE emails ENABLE ROW LEVEL SECURITY;
        ALTER TABLE email_attachments ENABLE ROW LEVEL SECURITY;
        ALTER TABLE summaries ENABLE ROW LEVEL SECURITY;
        ALTER TABLE processing_queue ENABLE ROW LEVEL SECURITY;
        ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
        
        -- Organization policies
        DROP POLICY IF EXISTS org_isolation ON organizations;
        CREATE POLICY org_isolation ON organizations
            USING (org_id = current_setting('app.current_org_id', true)::UUID);
        
        -- User policies
        DROP POLICY IF EXISTS user_org_isolation ON users;
        CREATE POLICY user_org_isolation ON users
            USING (org_id = current_setting('app.current_org_id', true)::UUID);
        
        DROP POLICY IF EXISTS user_self_access ON users;
        CREATE POLICY user_self_access ON users
            USING (user_id = current_setting('app.current_user_id', true)::UUID);
        
        -- Email policies
        DROP POLICY IF EXISTS email_user_access ON emails;
        CREATE POLICY email_user_access ON emails
            USING (
                user_id = current_setting('app.current_user_id', true)::UUID
                AND org_id = current_setting('app.current_org_id', true)::UUID
            );
        
        -- Attachment policies
        DROP POLICY IF EXISTS attachment_access ON email_attachments;
        CREATE POLICY attachment_access ON email_attachments
            USING (email_id IN (
                SELECT email_id FROM emails 
                WHERE user_id = current_setting('app.current_user_id', true)::UUID
            ));
        
        -- Summary policies
        DROP POLICY IF EXISTS summary_access ON summaries;
        CREATE POLICY summary_access ON summaries
            USING (email_id IN (
                SELECT email_id FROM emails 
                WHERE user_id = current_setting('app.current_user_id', true)::UUID
            ));
        
        -- Processing queue policies
        DROP POLICY IF EXISTS queue_access ON processing_queue;
        CREATE POLICY queue_access ON processing_queue
            USING (email_id IN (
                SELECT email_id FROM emails 
                WHERE user_id = current_setting('app.current_user_id', true)::UUID
            ));
        
        -- Audit logs (org-level access for admins only)
        DROP POLICY IF EXISTS audit_org_access ON audit_logs;
        CREATE POLICY audit_org_access ON audit_logs
            USING (
                org_id = current_setting('app.current_org_id', true)::UUID
                AND current_setting('app.user_role', true) = 'admin'
            );
    """)
    return security_sql

def create_indexes():
    """Create performance indexes"""
    indexes_sql = DDL("""
        -- User indexes
        CREATE INDEX IF NOT EXISTS idx_users_org_id ON users (org_id);
        CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);
        CREATE INDEX IF NOT EXISTS idx_users_oauth ON users (oauth_provider, oauth_subject);
        CREATE INDEX IF NOT EXISTS idx_users_last_login ON users (last_login);
        
        -- Email indexes
        CREATE INDEX IF NOT EXISTS idx_emails_user_id ON emails (user_id);
        CREATE INDEX IF NOT EXISTS idx_emails_org_id ON emails (org_id);
        CREATE INDEX IF NOT EXISTS idx_emails_received_at ON emails (received_at DESC);
        CREATE INDEX IF NOT EXISTS idx_emails_unprocessed ON emails (is_processed, created_at) 
            WHERE is_processed = FALSE;
        CREATE INDEX IF NOT EXISTS idx_emails_external_id ON emails (external_id);
        CREATE INDEX IF NOT EXISTS idx_emails_thread_id ON emails (thread_id);
        CREATE INDEX IF NOT EXISTS idx_emails_labels ON emails USING GIN (labels);
        
        -- Summary indexes
        CREATE INDEX IF NOT EXISTS idx_summaries_email_id ON summaries (email_id);
        CREATE INDEX IF NOT EXISTS idx_summaries_type ON summaries (summary_type);
        CREATE INDEX IF NOT EXISTS idx_summaries_created_at ON summaries (created_at DESC);
        
        -- Processing queue indexes
        CREATE INDEX IF NOT EXISTS idx_queue_status ON processing_queue (status, priority DESC, created_at);
        CREATE INDEX IF NOT EXISTS idx_queue_email_id ON processing_queue (email_id);
        CREATE INDEX IF NOT EXISTS idx_queue_worker ON processing_queue (worker_id, status);
        
        -- Audit log indexes
        CREATE INDEX IF NOT EXISTS idx_audit_org_timestamp ON audit_logs (org_id, timestamp DESC);
        CREATE INDEX IF NOT EXISTS idx_audit_user_timestamp ON audit_logs (user_id, timestamp DESC);
        CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_logs (action);
        CREATE INDEX IF NOT EXISTS idx_audit_resource ON audit_logs (resource_type, resource_id);
        
        -- Attachment indexes
        CREATE INDEX IF NOT EXISTS idx_attachments_email_id ON email_attachments (email_id);
        CREATE INDEX IF NOT EXISTS idx_attachments_size ON email_attachments (size_bytes);
        
        -- Data retention indexes
        CREATE INDEX IF NOT EXISTS idx_retention_org_type ON data_retention_policies (org_id, data_type);
    """)
    return indexes_sql

def create_triggers():
    """Create database triggers for automation"""
    triggers_sql = DDL("""
        -- Drop existing functions and triggers
        DROP TRIGGER IF EXISTS update_emails_updated_at ON emails;
        DROP TRIGGER IF EXISTS email_quota_trigger ON emails;
        DROP TRIGGER IF EXISTS audit_emails_trigger ON emails;
        DROP TRIGGER IF EXISTS audit_summaries_trigger ON summaries;
        DROP FUNCTION IF EXISTS update_updated_at_column();
        DROP FUNCTION IF EXISTS update_user_quota();
        DROP FUNCTION IF EXISTS log_data_access();
        
        -- Function to update updated_at timestamp
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ language 'plpgsql';
        
        -- Apply to relevant tables
        CREATE TRIGGER update_emails_updated_at 
            BEFORE UPDATE ON emails
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        
        -- Function to update user quota
        CREATE OR REPLACE FUNCTION update_user_quota()
        RETURNS TRIGGER AS $$
        BEGIN
            IF TG_OP = 'INSERT' THEN
                UPDATE users 
                SET quota_used_bytes = quota_used_bytes + NEW.email_size_bytes
                WHERE user_id = NEW.user_id;
                RETURN NEW;
            ELSIF TG_OP = 'DELETE' THEN
                UPDATE users 
                SET quota_used_bytes = quota_used_bytes - OLD.email_size_bytes
                WHERE user_id = OLD.user_id;
                RETURN OLD;
            END IF;
            RETURN NULL;
        END;
        $$ language 'plpgsql';
        
        -- Apply quota trigger
        CREATE TRIGGER email_quota_trigger
            AFTER INSERT OR DELETE ON emails
            FOR EACH ROW EXECUTE FUNCTION update_user_quota();
        
        -- Function for audit logging
        CREATE OR REPLACE FUNCTION log_data_access()
        RETURNS TRIGGER AS $$
        BEGIN
            INSERT INTO audit_logs (
                org_id, user_id, action, resource_type, resource_id, 
                success, additional_data
            ) VALUES (
                current_setting('app.current_org_id', true)::UUID,
                current_setting('app.current_user_id', true)::UUID,
                TG_OP,
                TG_TABLE_NAME,
                COALESCE(NEW.email_id, OLD.email_id),
                TRUE,
                jsonb_build_object('table', TG_TABLE_NAME, 'operation', TG_OP)
            );
            
            IF TG_OP = 'DELETE' THEN
                RETURN OLD;
            ELSE
                RETURN NEW;
            END IF;
        EXCEPTION
            WHEN OTHERS THEN
                -- Silently continue if audit logging fails
                IF TG_OP = 'DELETE' THEN
                    RETURN OLD;
                ELSE
                    RETURN NEW;
                END IF;
        END;
        $$ language 'plpgsql';
        
        -- Apply audit triggers to sensitive tables
        CREATE TRIGGER audit_emails_trigger
            AFTER INSERT OR UPDATE OR DELETE ON emails
            FOR EACH ROW EXECUTE FUNCTION log_data_access();
        
        CREATE TRIGGER audit_summaries_trigger
            AFTER INSERT OR UPDATE OR DELETE ON summaries
            FOR EACH ROW EXECUTE FUNCTION log_data_access();
    """)
    return triggers_sql

def create_database_schema(drop_existing=False):
    """Main function to create the complete database schema"""
    with engine.begin() as connection:
        if drop_existing:
            print("Dropping existing tables...")
            connection.execute(drop_existing_tables())
        
        print("Creating PostgreSQL extensions...")
        connection.execute(create_extensions())
        
        print("Creating ENUM types...")
        oauth_provider_enum.create(connection, checkfirst=True)
        processing_status_enum.create(connection, checkfirst=True)
        
        print("Creating non-partitioned tables...")
        metadata.create_all(connection)
        
        print("Creating partitioned tables...")
        connection.execute(create_partitioned_tables())
        
        print("Adding foreign key constraints...")
        connection.execute(add_foreign_key_constraints())
        
        print("Creating security policies...")
        connection.execute(create_security_policies())
        
        print("Creating indexes...")
        connection.execute(create_indexes())
        
        print("Creating triggers...")
        connection.execute(create_triggers())
        
        print("Database schema creation completed successfully!")

def setup_monitoring():
    """Set up database monitoring queries"""
    monitoring_sql = DDL("""
        -- Create monitoring views
        CREATE OR REPLACE VIEW v_user_statistics AS
        SELECT 
            u.org_id,
            u.user_id,
            u.email,
            COUNT(e.email_id) as total_emails,
            SUM(e.email_size_bytes) as total_size_bytes,
            MAX(e.received_at) as last_email_received,
            COUNT(s.summary_id) as total_summaries
        FROM users u
        LEFT JOIN emails e ON u.user_id = e.user_id
        LEFT JOIN summaries s ON e.email_id = s.email_id
        GROUP BY u.org_id, u.user_id, u.email;
        
        CREATE OR REPLACE VIEW v_processing_queue_status AS
        SELECT 
            status,
            COUNT(*) as task_count,
            AVG(EXTRACT(EPOCH FROM (NOW() - created_at))) as avg_wait_time_seconds
        FROM processing_queue
        GROUP BY status;
        
        CREATE OR REPLACE VIEW v_organization_usage AS
        SELECT 
            o.org_id,
            o.name,
            COUNT(DISTINCT u.user_id) as total_users,
            COUNT(e.email_id) as total_emails,
            SUM(e.email_size_bytes) as total_storage_bytes,
            COUNT(s.summary_id) as total_summaries
        FROM organizations o
        LEFT JOIN users u ON o.org_id = u.org_id
        LEFT JOIN emails e ON u.user_id = e.user_id
        LEFT JOIN summaries s ON e.email_id = s.email_id
        GROUP BY o.org_id, o.name;
    """)
    return monitoring_sql

def test_connection():
    """Test database connection and print info"""
    try:
        with engine.connect() as conn:
            db_version = conn.execute(text("SELECT version();")).scalar()
            print(f"✅ Successfully connected to PostgreSQL")
            print(f"Database version: {db_version}")
            
            # Check if we're connecting to the right database
            db_name = conn.execute(text("SELECT current_database();")).scalar()
            print(f"Connected to database: {db_name}")
            
            # Check the current user
            user = conn.execute(text("SELECT current_user;")).scalar()
            print(f"Connected as user: {user}")
            
        return True
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        print(f"Make sure you've created the email_db database with: createdb email_db")
        return False

def complete_database_reset():
    """Completely reset the database - drop everything for a fresh start"""
    reset_sql = DDL("""
        -- Drop all views first
        DROP VIEW IF EXISTS v_user_statistics CASCADE;
        DROP VIEW IF EXISTS v_processing_queue_status CASCADE;
        DROP VIEW IF EXISTS v_organization_usage CASCADE;
        
        -- Drop all triggers
        DROP TRIGGER IF EXISTS update_emails_updated_at ON emails;
        DROP TRIGGER IF EXISTS email_quota_trigger ON emails;
        DROP TRIGGER IF EXISTS audit_emails_trigger ON emails;
        DROP TRIGGER IF EXISTS audit_summaries_trigger ON summaries;
        
        -- Drop all functions
        DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE;
        DROP FUNCTION IF EXISTS update_user_quota() CASCADE;
        DROP FUNCTION IF EXISTS log_data_access() CASCADE;
        
        -- Drop all tables in reverse dependency order
        DROP TABLE IF EXISTS key_rotation_log CASCADE;
        DROP TABLE IF EXISTS data_retention_policies CASCADE;
        DROP TABLE IF EXISTS processing_queue CASCADE;
        DROP TABLE IF EXISTS summaries CASCADE;
        DROP TABLE IF EXISTS email_attachments CASCADE;
        DROP TABLE IF EXISTS emails CASCADE;
        DROP TABLE IF EXISTS audit_logs CASCADE;
        DROP TABLE IF EXISTS users CASCADE;
        DROP TABLE IF EXISTS organizations CASCADE;
        
        -- Drop all partition tables explicitly
        DROP TABLE IF EXISTS emails_part_0 CASCADE;
        DROP TABLE IF EXISTS emails_part_1 CASCADE;
        DROP TABLE IF EXISTS emails_part_2 CASCADE;
        DROP TABLE IF EXISTS emails_part_3 CASCADE;
        DROP TABLE IF EXISTS emails_part_4 CASCADE;
        DROP TABLE IF EXISTS emails_part_5 CASCADE;
        DROP TABLE IF EXISTS emails_part_6 CASCADE;
        DROP TABLE IF EXISTS emails_part_7 CASCADE;
        
        DROP TABLE IF EXISTS audit_logs_y2024m12 CASCADE;
        DROP TABLE IF EXISTS audit_logs_y2025m01 CASCADE;
        DROP TABLE IF EXISTS audit_logs_y2025m02 CASCADE;
        DROP TABLE IF EXISTS audit_logs_y2025m03 CASCADE;
        DROP TABLE IF EXISTS audit_logs_y2025m04 CASCADE;
        DROP TABLE IF EXISTS audit_logs_y2025m05 CASCADE;
        DROP TABLE IF EXISTS audit_logs_y2025m06 CASCADE;
        
        -- Drop custom types
        DROP TYPE IF EXISTS processing_status_type CASCADE;
        DROP TYPE IF EXISTS oauth_provider_type CASCADE;
        
        -- Drop roles (only if they exist and are not system roles)
        DO $$
        BEGIN
            IF EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'app_read') THEN
                DROP ROLE app_read;
            END IF;
            IF EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'app_write') THEN
                DROP ROLE app_write;
            END IF;
            IF EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'app_admin') THEN
                DROP ROLE app_admin;
            END IF;
        EXCEPTION
            WHEN OTHERS THEN
                -- Ignore errors if roles are in use
                NULL;
        END
        $$;
        
        -- Drop any remaining sequences
        DROP SEQUENCE IF EXISTS organizations_org_id_seq CASCADE;
        DROP SEQUENCE IF EXISTS users_user_id_seq CASCADE;
        
        -- Reset any session variables
        RESET ALL;
    """)
    return reset_sql

def fresh_start_setup():
    """Perform a complete database reset and setup"""
    print("🧹 Starting complete database reset...")
    
    try:
        with engine.begin() as connection:
            print("Dropping all existing objects...")
            connection.execute(complete_database_reset())
            
        print("✅ Database reset completed successfully!")
        print("🔨 Creating fresh database schema...")
        
        # Now create everything fresh
        create_database_schema(drop_existing=False)
        
        # Set up monitoring views
        with engine.begin() as connection:
            connection.execute(setup_monitoring())
        
        print("\n✅ Fresh database setup completed successfully!")
        
    except Exception as e:
        print(f"❌ Fresh start setup failed: {str(e)}")
        raise

if __name__ == "__main__":
    # Test connection first
    if not test_connection():
        print("Fix the connection issues before proceeding.")
        exit(1)
    
    # Ask user what they want to do
    print("\nChoose setup option:")
    print("1. Regular setup (drop and recreate tables)")
    print("2. Fresh start (complete database reset)")
    
    choice = input("Enter your choice (1 or 2): ").strip()
    
    try:
        if choice == "2":
            fresh_start_setup()
        else:
            # Default to regular setup
            create_database_schema(drop_existing=True)
            
            # Set up monitoring views
            with engine.begin() as connection:
                connection.execute(setup_monitoring())
            
            print("\n✅ Enterprise email database setup completed successfully!")
        
        print("\n📊 Next steps:")
        print("1. Configure your KMS/HSM for encryption key management")
        print("2. Set up database backups and replication")
        print("3. Configure monitoring and alerting")
        print("4. Implement your application-layer encryption")
        print("5. Set up automated partition management")
        
    except Exception as e:
        print(f"❌ Database setup failed: {str(e)}")
        raise

