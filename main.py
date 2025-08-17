# Where the Flask app is and initialization happens

import flask
import os
import asyncio
from dotenv import load_dotenv
import flask_jwt_extended
from surrealdb import Surreal

from auth import auth_bp

load_dotenv()

DB_URL = os.getenv("DB_URL")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")

# Initialize the SurrealDB connection
def connect_db(url: str):
    print("Connecting to SurrealDB...:")
    db = Surreal(url=url)
    return db


db = connect_db(DB_URL)
db.use("Test", "Test")
db.signin({
    "username": DB_USER,
    "password": DB_PASS
})
print("Connected and authenticated with SurrealDB")


if __name__ == "__main__":
    app = flask.Flask(__name__)
    app.config["JWT_SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY")
    # Initialize the database connection
    if not DB_URL:
        raise ValueError("DB_URL environment variable is not set.")

    jwt = flask_jwt_extended.JWTManager()
    jwt.init_app(app)

    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/auth')

    # Run the Flask app
    app.run()
    