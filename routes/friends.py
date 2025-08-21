# Routes relating to friends

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from extensions import sdb

events_bp = Blueprint('events', __name__)

@events_bp.route('/friends', methods=['GET'])
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
