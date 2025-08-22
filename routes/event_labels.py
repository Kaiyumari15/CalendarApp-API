# Event labels related routes

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from extensions import sdb

event_labels_bp = Blueprint('event-labels', __name__)

@event_labels_bp.route('/', methods=['GET'])
@jwt_required()
def get_event_labels():
    db = sdb.get_db()
    # Logic to retrieve event labels
    current_user = get_jwt_identity()
    user_id = f"user:{current_user}"

    event_labels = db.query("SELECT * FROM event_label WHERE owner = $user_id;", {"user_id": user_id})
    return jsonify(event_labels)

@event_labels_bp.route('/', methods=['POST'])
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

@event_labels_bp.route('/<label_id>', methods=['DELETE'])
@jwt_required()
def delete_event_label(label_id):
    db = sdb.get_db()
    current_user = get_jwt_identity()
    user_id = f"user:{current_user}"

    result = db.query("""
            IF NOT (record::exists($label_id)) THEN {
                RETURN { "error": "Event label not found" };
            };
            IF (SELECT owner FROM $label_id) != $user_id THEN {
                RETURN { "error": "Requester is not owner" };
            }
            UPDATE has_access_to WHERE because_of CONTAINS $label_id SET because_of -= $label_id;
            DELETE has_access_to WHERE because_of = [];
            RETURN DELETE FROM event_label WHERE id = $label_id AND owner = $user_id RETURN BEFORE;
            """)

    if result.get("error"):
        match result["error"]:
            case "Event label not found":
                return jsonify({"error": "Event label not found"}), 404
            case "Requester is not owner":
                return jsonify({"error": "You do not have permission to delete this label"}), 403

    return jsonify({"message": "Event label deleted successfully", "label": result}), 204