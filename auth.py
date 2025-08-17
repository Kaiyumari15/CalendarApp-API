# User authentication and authorization logic

from flask import Flask, Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, create_refresh_token, get_jwt, get_jwt_identity, jwt_required
from werkzeug.security import generate_password_hash, check_password_hash

auth_bp = Blueprint('auth', __name__)

from main import db

@auth_bp.post('/register')
def register():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    email = data.get("email")

    if not username or not password or not email:
        return { "error": "Username, password, and email are required" }, 400

    # Lazily check that it COULD be a valid email address
    # This should be updated with a proper regex and then a confirmation email 
    if email.count('@') != 1 or email.count('.') < 1:
        return { "error": "Invalid email address" }, 400

    users = db.query("SELECT * FROM user WHERE username = $username OR email = $email", { "username": username, "email": email })
    print(users)
    if users != []:
        return { "error": "username or email taken" }, 409

    password = data.get("password")
    hash = generate_password_hash(password)
    print(hash)

    db.query("CREATE user SET username = $username, email = $email, password = $password" , { "username": username, "email": email, "password": hash })
    return { "message": "User registered successfully" }

@auth_bp.post('/login')
def login():
    data = request.get_json()
    password = data.get("password")
    email = data.get("email")

    print(password)

    if (not email) or not password:
        return { "error": "Email and password are required" }, 400

    user = db.query("SELECT * FROM user WHERE email = $email", { "email": email })
    print(user)
    if user == []:
        return { "error": "Invalid email or password" }, 401

    if not check_password_hash(user[0]['password'], password):
        return { "error": "Invalid email or password" }, 401

    # Generate JWT tokens
    access_token = create_access_token(user[0]['id'].id)
    refresh_token = create_refresh_token(user[0]['id'].id)
    return jsonify(
        {
            "message": "Login successful",
            "tokens": {
                "access_token": access_token,
                "refresh_token": refresh_token
            }
        }
    )

@auth_bp.get('/refresh')
@jwt_required(refresh=True)
def refresh_access():
    identity = get_jwt_identity()
    access_token = create_access_token(identity)
    return jsonify(
        {
            "message": "Access token refreshed",
            "tokens": {
                "access_token": access_token
            }
        }
    )

@auth_bp.post('/logout')
@jwt_required(verify_type=False)
def logout():
    jwt = get_jwt()
    jti = jwt["jti"]
    exp = jwt["exp"]
    token_type = jwt["type"]

    db.query("CREATE blocked_token SET jti = $jti, reason='logout', expiry=$expiry", { "jti": jti, "expiry": exp })

    return jsonify(
        {
            "message": F"{token_type} token revoked successfully"
        }, 200
    )