import uuid
import pandas as pd
from datetime import datetime, timedelta
from db_connection import create_connection
from sqlalchemy import text
 
def create_session(user_id: int):
    """Generate a session token, save it to DB, and return the token."""
    engine = create_connection()
    session_token = str(uuid.uuid4())
    insert_query = "INSERT INTO sessions (user_id, session_token, created_at) VALUES (%s, %s, %s)"
    with engine.begin() as conn:
        conn.execute(
            text("INSERT INTO sessions (user_id, session_token, created_at) VALUES (:user_id, :token, :created_at)"),
            {"user_id": user_id, "token": session_token, "created_at": datetime.utcnow()}
        )
    return session_token
 
def validate_session(token: str):
    """Check if a session token exists and is still valid."""
    engine = create_connection()
    query = "SELECT * FROM sessions WHERE session_token = %s"
    session_df = pd.read_sql(query, engine, params=(token,))
    if session_df.empty:
        return None
    return int(session_df['user_id'].values[0])
 
def delete_session(token: str):
    """Remove session on logout."""
    engine = create_connection()
    delete_query = "DELETE FROM sessions WHERE session_token = %s"
    with engine.begin() as conn:
        conn.execute(delete_query, (token,))