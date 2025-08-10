# Where the Flask app is and initialization happens

import flask
import os
from dotenv import load_dotenv

from database import DB_URL, db  # Ensure the database is initialized before running the app
from database import init_db; 

load_dotenv()
DB_URL = os.getenv("DB_URL")


app = flask.Flask(__name__)

if __name__ == "__main__":
    # Initialize the database connection
    if not DB_URL:
        raise ValueError("DB_URL environment variable is not set.")
    init_db()
    # Run the Flask app
    app.run()
    