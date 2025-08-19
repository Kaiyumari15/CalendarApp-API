# Where the Flask app is and initialization happens

import flask
import os
from dotenv import load_dotenv
import flask_jwt_extended
from surrealdb import Surreal

from extensions import sdb

from routes.auth import auth_bp
from routes.events import events_bp

load_dotenv()

if __name__ == "__main__":
    app = flask.Flask(__name__)
    app.config["JWT_SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY")
    
    # Initialize the database connection
    sdb.init_app(app)
    db = sdb.get_db()

    jwt = flask_jwt_extended.JWTManager()
    jwt.init_app(app)

    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(events_bp, url_prefix='/events')

    # Flask callbacks
    @jwt.additional_claims_loader
    def add_claims_to_access_token(identity):
        pass

    @jwt.token_in_blocklist_loader
    def token_in_blocklist(jwt_header, jwt_payload):
        jti = jwt_payload["jti"]
        token = db.query("SELECT * FROM blocked_token WHERE jti = $jti", {"jti": jti})
        if token != []:
            return True
        return False

    
    # Run the Flask app
    app.run()
    