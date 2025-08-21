# Routes relating to friends

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from extensions import sdb

social_bp = Blueprint('social', __name__)

@social_bp.route('/friends', methods=['GET'])
@jwt_required()
def get_friends():
    db = sdb.get_db()

    user = get_jwt_identity()
    user_id = f"user:{user}"

    result = db.query(
        """
        LET $friends = SELECT * FROM relationship_with WHERE in = $user_id AND type = 'friend';
        RETURN $friends;
        """,
        {"user_id": user_id}
    )

    return {
        "friends": result
    }, 200

@social_bp.route('/following', methods=['GET'])
@jwt_required()
def get_following():
    db = sdb.get_db()

    user = get_jwt_identity()
    user_id = f"user:{user}"

    result = db.query(
        """
        LET $following = SELECT * FROM relationship_with WHERE in = $user_id AND (type = 'following' OR type = 'friend');
        RETURN $following;
        """,
        {"user_id": user_id}
    )

    return {
        "following": result
    }, 200

@social_bp.route('/followers', methods=['GET'])
@jwt_required()
def get_followers():
    db = sdb.get_db()

    user = get_jwt_identity()
    user_id = f"user:{user}"

    result = db.query(
        """
        LET $followers = SELECT * FROM relationship_with WHERE in = $user_id AND type = 'follower';
        RETURN $followers;
        """,
        {"user_id": user_id}
    )

    return {
        "followers": result
    }, 200