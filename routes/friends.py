# Routes relating to friends

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from extensions import sdb

friends_bp = Blueprint('friends', __name__)

@friends_bp.route('/friends', methods=['GET'])
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

@friends_bp.route('/following', methods=['GET'])
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