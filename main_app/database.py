import os
import urllib
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

host = os.getenv("DB_SERVER")
database = os.getenv("DB_NAME")
driver = os.getenv("DB_DRIVER")
user = os.getenv("DB_USER")
password = os.getenv("DB_PASSWORD")

# Construct the connection string
params = urllib.parse.quote_plus(
    f"DRIVER={{{driver}}};"
    f"SERVER={host};"
    f"DATABASE={database};"
    f"UID={user};"
    f"PWD={password};"
    f"TrustServerCertificate=yes;"
)


SQLALCHEMY_DATABASE_URL = f"mssql+pyodbc:///?odbc_connect={params}"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def test_connection():
    try:
        # Create a connection from the engine
        with engine.connect() as connection:
            # Run a simple SQL query to check the version
            result = connection.execute(text("SELECT @@VERSION"))
            print("Successfully connected to the database!")
            print(f"SQL Server Version: {result.fetchone()[0]}")
    except Exception as e:
        print("Connection failed!")
        print(f"Error details: {e}")

if __name__ == "__main__":
    test_connection()