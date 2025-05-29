import sqlite3
import os
from datetime import datetime

def create_database():
    """Create SQLite database and tables for multi-user Gmail API"""
    
    # Create database directory if it doesn't exist
    os.makedirs('data', exist_ok=True)
    
    # Connect to SQLite database
    conn = sqlite3.connect('data/gmail_app.db')
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            is_active BOOLEAN DEFAULT 1
        )
    ''')
    
    # Create user_credentials table to store OAuth tokens
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_credentials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            access_token TEXT NOT NULL,
            refresh_token TEXT,
            token_uri TEXT NOT NULL,
            client_id TEXT NOT NULL,
            client_secret TEXT NOT NULL,
            scopes TEXT NOT NULL,
            expires_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')
    
    # Create sessions table for user sessions
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            session_token TEXT UNIQUE NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')
    
    # Create email_cache table (optional - for caching frequently accessed emails)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS email_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            email_id TEXT NOT NULL,
            subject TEXT,
            sender TEXT,
            recipient TEXT,
            date_received TIMESTAMP,
            snippet TEXT,
            body TEXT,
            cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
            UNIQUE(user_id, email_id)
        )
    ''')
    
    # Create indexes for better performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_credentials_user_id ON user_credentials(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_sessions_token ON user_sessions(session_token)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_email_cache_user_id ON email_cache(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_email_cache_email_id ON email_cache(user_id, email_id)')
    
    # Commit changes and close connection
    conn.commit()
    conn.close()
    
    print("Database created successfully!")
    print("Tables created:")
    print("- users: Store user information")
    print("- user_credentials: Store OAuth tokens per user")
    print("- user_sessions: Manage user sessions")
    print("- email_cache: Cache email data for performance")

def reset_database():
    """Reset database by dropping all tables and recreating them"""
    if os.path.exists('data/gmail_app.db'):
        os.remove('data/gmail_app.db')
        print("Existing database removed.")
    
    create_database()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--reset':
        reset_database()
    else:
        create_database()