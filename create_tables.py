#!/usr/bin/env python3
"""
Script to create database tables directly using psycopg2.
"""

import psycopg2

def create_tables():
    conn_string = os.getenv('DATABASE_URL', 'postgresql://username:password@host:port/tetheritall?sslmode=verify-full')
    
    try:
        print("Connecting to CockroachDB...")
        conn = psycopg2.connect(conn_string)
        cursor = conn.cursor()
        
        # Create tables based on our models
        print("Creating tables...")
        
        # Device table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS devices (
                id SERIAL PRIMARY KEY,
                model VARCHAR(255),
                manufacturer VARCHAR(255),
                firmware_version VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # API Endpoints table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_endpoints (
                id SERIAL PRIMARY KEY,
                device_id INTEGER REFERENCES devices(id),
                endpoint_url VARCHAR(500),
                method VARCHAR(10),
                authentication_type VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Scan Results table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scan_results (
                id SERIAL PRIMARY KEY,
                device_id INTEGER REFERENCES devices(id),
                agent_type VARCHAR(100),
                raw_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Commit the changes
        conn.commit()
        print("Tables created successfully!")
        
        # List the tables
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        tables = cursor.fetchall()
        print("Created tables:")
        for table in tables:
            print(f"  - {table[0]}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"Error creating tables: {e}")
        return False

if __name__ == "__main__":
    create_tables()
