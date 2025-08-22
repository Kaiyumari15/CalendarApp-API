# Event labels related routes

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from extensions import sdb

event_labels_bp = Blueprint('event-labels', __name__)

@event_labels_bp.route('/event-labels', methods=['GET'])
@jwt_required()
def get_event_labels():
    db = sdb.get_db()
    # Logic to retrieve event labels
    current_user = get_jwt_identity()
    user_id = f"user:{current_user}"

    event_labels = db.query("SELECT * FROM event_labels WHERE owner = $user_id", {"user_id": user_id})
    return jsonify(event_labels)