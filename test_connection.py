#!/usr/bin/env python3
"""
Script to test CockroachDB connection and create tables directly.
"""

import psycopg2
from shared.database.models import Base
from sqlalchemy import create_engine, text

def test_connection():
    # Test direct psycopg2 connection
    conn_string = "postgresql://john:***REMOVED***@playground-15066.j77.aws-us-east-2.cockroachlabs.cloud:26257/tetheritall?sslmode=verify-full"
    
    try:
        print("Testing direct psycopg2 connection...")
        conn = psycopg2.connect(conn_string)
        cursor = conn.cursor()
        
        # Test a simple query
        cursor.execute("SELECT version()")
        version = cursor.fetchone()
        print(f"Connected successfully! Version: {version[0]}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"Direct connection failed: {e}")
        return False

def create_tables_sqlalchemy():
    # Test SQLAlchemy connection
    conn_string = "postgresql+psycopg2://john:***REMOVED***@playground-15066.j77.aws-us-east-2.cockroachlabs.cloud:26257/tetheritall?sslmode=verify-full"
    
    try:
        print("Testing SQLAlchemy connection...")
        engine = create_engine(conn_string)
        
        # Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.scalar()
            print(f"SQLAlchemy connected! Version: {version}")
        
        # Create tables
        print("Creating tables...")
        Base.metadata.create_all(engine)
        print("Tables created successfully!")
        
        return True
        
    except Exception as e:
        print(f"SQLAlchemy connection failed: {e}")
        return False

if __name__ == "__main__":
    print("Testing CockroachDB connections...")
    
    # Test direct connection
    if test_connection():
        print("✓ Direct connection works")
    else:
        print("✗ Direct connection failed")
    
    # Test SQLAlchemy connection
    if create_tables_sqlalchemy():
        print("✓ SQLAlchemy connection and table creation works")
    else:
        print("✗ SQLAlchemy connection failed")
