#!/usr/bin/env python3
"""
Script to create the tetheritall database in CockroachDB.
"""

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

def create_database():
    # Connection string for defaultdb (existing database)
    default_conn_string = "postgresql://john:***REMOVED***@playground-15066.j77.aws-us-east-2.cockroachlabs.cloud:26257/defaultdb?sslmode=verify-full"
    
    try:
        # Connect to defaultdb
        print("Connecting to CockroachDB...")
        conn = psycopg2.connect(default_conn_string)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        
        # Create cursor
        cursor = conn.cursor()
        
        # Check if database already exists
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = 'tetheritall'")
        exists = cursor.fetchone()
        
        if exists:
            print("Database 'tetheritall' already exists!")
        else:
            # Create the database
            print("Creating database 'tetheritall'...")
            cursor.execute("CREATE DATABASE tetheritall")
            print("Database 'tetheritall' created successfully!")
        
        # Close connections
        cursor.close()
        conn.close()
        
        print("Database setup complete!")
        return True
        
    except Exception as e:
        print(f"Error creating database: {e}")
        return False

if __name__ == "__main__":
    create_database()
