#!/usr/bin/env python3
"""
Create Phase 2 database tables for device states, state changes, events, and subscriptions.
"""

import psycopg2
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def create_phase2_tables():
    """Create Phase 2 database tables."""
    
    # Get database connection details
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("Error: DATABASE_URL not found in environment variables")
        return False
        
    # Parse connection details
    # Expected format: postgresql+psycopg2://username:password@host:port/database?sslmode=require
    try:
        # Remove postgresql+psycopg2:// prefix
        connection_string = database_url.replace('postgresql+psycopg2://', '')
        
        # Split into parts
        auth_part, rest = connection_string.split('@', 1)
        username, password = auth_part.split(':', 1)
        host_port, database_with_params = rest.split('/', 1)
        host, port = host_port.split(':', 1)
        
        # Remove query parameters from database name
        database = database_with_params.split('?')[0]
        
        print(f"Connecting to database: {host}:{port}/{database}")
        print(f"Username: {username}")
        
    except Exception as e:
        print(f"Error parsing DATABASE_URL: {e}")
        return False
    
    try:
        # Connect to database with SSL
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=username,
            password=password,
            sslmode='require'  # Required for CockroachDB
        )
        
        cursor = conn.cursor()
        
        # Create device_states table
        print("Creating device_states table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS device_states (
                id SERIAL PRIMARY KEY,
                device_id VARCHAR(255) NOT NULL UNIQUE,
                current_state VARCHAR(64) NOT NULL,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                configuration JSONB,
                device_metadata JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Create index on device_id
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_device_states_device_id 
            ON device_states(device_id);
        """)
        
        # Create state_changes table
        print("Creating state_changes table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS state_changes (
                id SERIAL PRIMARY KEY,
                device_id VARCHAR(255) NOT NULL,
                from_state VARCHAR(64),
                to_state VARCHAR(64) NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reason VARCHAR(255),
                change_metadata JSONB
            );
        """)
        
        # Create indexes on state_changes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_state_changes_device_id 
            ON state_changes(device_id);
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_state_changes_timestamp 
            ON state_changes(timestamp);
        """)
        
        # Create events table
        print("Creating events table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id SERIAL PRIMARY KEY,
                event_id VARCHAR(255) NOT NULL UNIQUE,
                event_type VARCHAR(64) NOT NULL,
                source VARCHAR(255) NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data JSONB,
                event_metadata JSONB,
                priority VARCHAR(32) NOT NULL,
                ttl INTEGER,
                delivered BOOLEAN DEFAULT FALSE
            );
        """)
        
        # Create indexes on events
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_event_id 
            ON events(event_id);
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_event_type 
            ON events(event_type);
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_source 
            ON events(source);
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_timestamp 
            ON events(timestamp);
        """)
        
        # Create event_subscriptions table
        print("Creating event_subscriptions table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS event_subscriptions (
                id SERIAL PRIMARY KEY,
                subscription_id VARCHAR(255) NOT NULL UNIQUE,
                subscriber_id VARCHAR(255) NOT NULL,
                event_types JSONB,
                sources JSONB,
                priority_filter VARCHAR(32),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                active BOOLEAN DEFAULT TRUE
            );
        """)
        
        # Create indexes on event_subscriptions
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_event_subscriptions_subscription_id 
            ON event_subscriptions(subscription_id);
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_event_subscriptions_subscriber_id 
            ON event_subscriptions(subscriber_id);
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_event_subscriptions_active 
            ON event_subscriptions(active);
        """)
        
        # Commit changes
        conn.commit()
        
        print("Phase 2 tables created successfully!")
        
        # Show table information
        cursor.execute("""
            SELECT table_name, column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name IN ('device_states', 'state_changes', 'events', 'event_subscriptions')
            ORDER BY table_name, ordinal_position;
        """)
        
        tables = cursor.fetchall()
        print("\nCreated tables and columns:")
        current_table = None
        for table_name, column_name, data_type in tables:
            if table_name != current_table:
                current_table = table_name
                print(f"\n{table_name}:")
            print(f"  - {column_name}: {data_type}")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"Error creating Phase 2 tables: {e}")
        return False

if __name__ == "__main__":
    success = create_phase2_tables()
    if success:
        print("\nPhase 2 database setup completed successfully!")
    else:
        print("\nPhase 2 database setup failed!")
        exit(1)
