# Relationship labels related routes

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from extensions import sdb

relationship_labels_bp = Blueprint('relationship-labels', __name__)

@relationship_labels_bp.route('/', methods=['GET'])
@jwt_required()
def get_relationship_labels():
    db = sdb.get_db()
    current_user = get_jwt_identity()
    user_id = f"user:{current_user}"

    result = sdb.query("SELECT * FROM relationship_labels WHERE owner = $user_id", {"user_id": user_id})
    return jsonify(result), 200