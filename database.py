from surrealdb import Surreal
# Database connection initialization
import os
from dotenv import load_dotenv

# Initialize the SurrealDB connection
def connect_db(url):
    return Surreal(url)