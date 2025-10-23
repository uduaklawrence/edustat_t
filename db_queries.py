# db_queries.py
import pandas as pd
from db_connection import create_connection
import streamlit as st

# ---------------------------------------------------------
# Generic function to execute a query and return DataFrame
# ---------------------------------------------------------
def fetch_data(query):
    engine = create_connection()  # Get the SQLAlchemy engine (not the connection object)
    if engine:
        try:
            # Use pandas to execute the query and return a DataFrame, using the engine
            df = pd.read_sql(query, engine)  # Pass the engine directly to pandas
            return df
        except Exception as e:
            st.error(f"Query execution error: {e}")
            return pd.DataFrame()
    else:
        return pd.DataFrame()
    

# Assuming you have a function to get a database connection
# from your_db_connection_module import get_db_connection
 
def update_payment_status(email: str):
    """Updates the user's payment status to True (or 1) in the database."""
    # IMPORTANT: Use parameterized queries to prevent SQL injection
    # The exact syntax depends on your DB connector (e.g., %s for psycopg2, ? for sqlite3)
    query = "UPDATE users SET payment = 1 WHERE email_address = %s" 
    # This is a placeholder for your actual database execution logic
    try:
        # conn = get_db_connection()
        # cursor = conn.cursor()
        # cursor.execute(query, (email,))
        # conn.commit()
        # cursor.close()
        # conn.close()
        print(f"DATABASE: Updated payment status for {email}")
        return True
    except Exception as e:
        print(f"DATABASE ERROR: Failed to update payment status for {email}. Error: {e}")
        return False
    