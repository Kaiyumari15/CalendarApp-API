# Database connection related stuff

import surrealdb
import dotenv
import os


class SurrealInstance:
    def __init__(self):
        self.app = None,
        self.driver = None

    def init_app(self, app):
        self.app = app
        self.connect()

    def connect(self):
        print("Connecting to SurrealDB...")
        dotenv.load_dotenv()
        DB_URL = os.getenv("DB_URL")
        DB_USER = os.getenv("DB_USER")
        DB_PASS = os.getenv("DB_PASS")

        if not DB_URL or not DB_USER or not DB_PASS:
            raise ValueError("DB_URL, DB_USER, and DB_PASS environment variables must be set.")
    
        self.driver = surrealdb.Surreal(DB_URL)
        self.driver.use("Test", "Test")
        self.driver.signin({
            "username": DB_USER,
            "password": DB_PASS
        })
        print("Connected to SurrealDB!")
        return self.driver

    def get_db(self):
        if not self.driver:
            self.driver = self.connect
        return self.driver