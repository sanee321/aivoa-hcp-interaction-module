# test_db.py
import os
from psycopg2 import connect, OperationalError
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()  # reads .env in current directory

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise SystemExit("Please set DATABASE_URL in .env")

try:
    conn = connect(DATABASE_URL)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT current_database() AS db, version() AS pg_version;")
    result = cur.fetchone()
    print("Connection successful:", result)
    cur.close()
    conn.close()
except OperationalError as e:
    print("Connection failed:", e)
