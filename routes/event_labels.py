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

    event_labels = db.query("SELECT * FROM event_label WHERE owner = $user_id;", {"user_id": user_id})
    return jsonify(event_labels)

@event_labels_bp.route('/event-labels', methods=['POST'])
@jwt_required()
def create_event_label():
    db = sdb.get_db()
    current_user = get_jwt_identity()
    user_id = f"user:{current_user}"

    data = request.get_json()
    label_name = data.get("name")

    if not label_name:
        return jsonify({"error": "Label name is required"}), 400

    db.query("CREATE event_label SET name = $name, owner = $user_id;", {"name": label_name, "user_id": user_id})
    return jsonify({"message": "Event label created successfully"}), 201