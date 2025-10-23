# db_connection.py
from sqlalchemy import create_engine
import mysql.connector
import streamlit as st
from urllib.parse import quote_plus
from decouple import config
# ---------------------------------------------------------
# Database configuration
# ---------------------------------------------------------
# Create a SQLAlchemy engine
def create_connection():
    try:
        # Safely encode credentials to handle special characters like @, :, /, #
        username = quote_plus(config("user"))
        password = quote_plus(config("password"))
        host = config("host")
        port = config("port", cast=int)
        database = config("database") 
 
        # Build a properly encoded SQLAlchemy connection string
        connection_string = f"mysql+pymysql://{username}:{password}@{host}:{port}/{database}"
 
        # Create engine
        engine = create_engine(connection_string)
        print("Database connection established.")
        return engine
 
    except Exception as e:
        st.error(f"Database connection error: {e}")
        return None