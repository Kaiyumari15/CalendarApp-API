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

    result = sdb.query("SELECT * FROM relationship_label WHERE owner = $user_id", {"user_id": user_id})
    return jsonify(result), 200

@relationship_labels_bp.route('/', methods=['POST'])
@jwt_required()
def create_relationship_label():
    db = sdb.get_db()
    current_user = get_jwt_identity()
    user_id = f"user:{current_user}"

    data = request.get_json()
    name = data.get("name")

    if not name:
        return jsonify({"error": "Name is required"}), 400

    result = sdb.query("CREATE relationship_label SET owner = $user_id, name = $name RETURN AFTER", {"user_id": user_id, "name": name})
    return jsonify({"message": "Label created successfully", "label": result}), 201

@relationship_labels_bp.route('/<label_id>', methods=['PUT'])
@jwt_required()
def update_relationship_label(label_id):
    db = sdb.get_db()
    current_user = get_jwt_identity()
    user_id = f"user:{current_user}"

    data = request.get_json()
    merge_data = data.get("merge_data")
    if not merge_data:
        return jsonify({"error": "Merge data is required"}), 400

    name = merge_data["name"]

    result = sdb.execute("""
                IF NOT record::exists($label_id) THEN {
                    RETURN { "error": "Label not found" };
                }
                IF $label_id.owner != $user_id THEN {
                    RETURN { "error": "Requester is not the owner" };
                }
                UPDATE $label_id MERGE $merge_data;
                """, {"merge_data": merge_data, "label_id": label_id, "user_id": user_id})
    
    if result["error"]:
        match result["error"]:
            case "Label not found":
                return jsonify({"error": "Label not found"}), 404
            case "Requester is not the owner":
                return jsonify({"error": "Requester is not the owner"}), 403

    return jsonify({"message": "Label updated successfully", "label": result}), 200

@relationship_labels_bp.route('/<label_id>', methods=['DELETE'])
@jwt_required()
def delete_relationship_label(label_id):
    db = sdb.get_db()
    current_user = get_jwt_identity()
    user_id = f"user:{current_user}"

    result = sdb.execute("""
                IF NOT record::exists($label_id) THEN {
                    RETURN { "error": "Label not found" };
                }
                IF $label_id.owner != $user_id THEN {
                    RETURN { "error": "Requester is not the owner" };
                }
                DELETE ONLY $label_id RETURN AFTER;
                """, {"label_id": label_id, "user_id": user_id})

    if result["error"]:
        match result["error"]:
            case "Label not found":
                return jsonify({"error": "Label not found"}), 404

    return jsonify({"message": "Label deleted successfully"}), 200