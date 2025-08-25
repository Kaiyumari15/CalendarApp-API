from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from extensions import sdb

default_share_bp = Blueprint('default-share', __name__)

@default_share_bp.route('/<relationship_label_id>', methods=['GET'])
@jwt_required()
def get_default_share_with_by_relationship_label(relationship_label_id):
    db = sdb.get_db()
    requester = get_jwt_identity()
    requester_id = f"user:{requester}"

    result = db.query("""
        IF NOT record::exists($relationship_label_id) THEN {
            RETURN { "error": "Label not found" };
        };
        IF NOT $relationship_label_id.owner = $requester_id THEN {
            RETURN { "error": "Insufficient permissions" };
        };
        LET $shares = (SELECT * FROM default_share WHERE in = $relationship_label_id);
        RETURN { "shares": $shares };
    """, {"relationship_label_id": relationship_label_id, "requester_id": requester_id})

    if result["error"]:
        match result["error"]:
            case 'Label not found':
                return {"error": "Label not found"}, 404

    return jsonify({
        "shares": result["shares"]
    })

@default_share_bp.route('/<relationship_label_id>/event/<event_id>', methods=['POST'])
@jwt_required()
def create_default_share_with_event(relationship_label_id, event_id):
    db = sdb.get_db()
    requester = get_jwt_identity()

    data = request.json
    permission = data.get("permission", str)

    requester_id = f"user:{requester}"
    event_id = f"event:{event_id}"
    label_id = f"relationship_label:{label_id}"

    result = db.query("""
        IF !record::exists($event_id) THEN {
            RETURN { "error": "Event not found" };
        };
        IF !record::exists($label_id) THEN {
            RETURN { "error": "Label not found" };
        };
        LET $event_permission = (SELECT * FROM has_access_to WHERE in = $requester_id AND out = $event_id);
        IF $event_permission = [] OR NOT (['owner', 'admin'] CONTAINS $event_permission[0].permission) THEN {
            RETURN { "error": "Insufficient event permissions" };
        };
        IF $label_id.owner != $requester THEN {
            RETURN { "error": "Insufficient label permissions" };
        };
        LET $relation = RELATE $label_id->default_share->$event_id SET default_permission = $permission;
        LET $links = [];
        LET $users = SELECT out.id FROM relationship_with WHERE in = $requester_id AND out = $event_id AND labels CONTAINS $label_id;
        FOR $user IN $users {
            LET $existing_relationship = SELECT * FROM has_access_to WHERE in = $user AND out = $event_id;
            IF $existing_relationship = [] THEN {
                LET $link = RELATE $user->has_access_to->$event_id SET permission = $permission, because_of = $label_id;
                $links += $link;
            } ELSE {
                LET $link = UPDATE $existing_relationship[0].id SET because_of += $label_id;
                $links += $link;
            };
        };
        RETURN { links: $links, relation: $relation };
    """, {"event_id": event_id, "label_id": label_id, "requester_id": requester_id, "permission": permission})

    if result["error"]:
        match result["error"]:
            case 'Event not found':
                return {"error": "Event not found"}, 404
            case 'Label not found':
                return {"error": "Label not found"}, 404
            case 'Insufficient event permissions':
                return {"error": "User does not have permission to share this event"}, 403
            case 'Insufficient label permissions':
                return {"error": "User does not own this label"}, 403

    return jsonify({
        "message": "Shared with label",
        "relation": result["relation"],
        "links": result["links"]
    })

@default_share_bp.route('/<relationship_label_id>/event/<event_id>', methods=['PUT'])
@jwt_required()
def update_default_share_with_event(relationship_label_id, event_id):
    db = sdb.get_db()
    requester = get_jwt_identity()

    data = request.json
    permission = data.get("permission", str)

    requester_id = f"user:{requester}"
    event_id = f"event:{event_id}"
    label_id = f"relationship_label:{label_id}"

    result = db.query(
        """
        IF !record::exists($event_id) THEN {
            RETURN { "error": "Event not found" };
        };
        IF !record::exists($label_id) THEN {
            RETURN { "error": "Label not found" };
        };
        LET $event_permission = (SELECT * FROM has_access_to WHERE in = $requester_id AND out = $event_id);
        IF $event_permission = [] OR NOT (['owner', 'admin'] CONTAINS $event_permission[0].permission) THEN {
            RETURN { "error": "Insufficient event permissions" };
        };
        IF $label_id.owner != $requester_id THEN {
            RETURN { "error": "Insufficient label permissions" };
        };
        LET $relation = (SELECT * FROM default_share WHERE in = $label_id AND out = $event_id);
        IF $relation = [] THEN {
            RETURN { "error": "No existing share found" };
        };
        LET $links = [];
        LET $shares = (SELECT * FROM has_access_to WHERE out = $event_id AND because_of CONTAINS $relation[0].id);
        FOR $share IN $shares {
            UPDATE $share.id SET permission = $permission;
            $links += $share.id;
        };
        RETURN { links: $links, relation: $relation };
        """, {"event_id": event_id, "requester_id": requester_id, "permission": permission})

    if result["error"]:
        match result["error"]:
            case 'Event not found':
                return {"error": "Event not found"}, 404
            case 'Insufficient event permissions':
                return {"error": "User does not have permission to update this share"}, 403
            case 'No existing share found':
                return {"error": "No existing share found for this event"}, 404

    return jsonify({
        "message": "Share updated successfully",
        "links": result["links"],
        "relation": result["relation"]
    })

@default_share_bp.route('/<relationship_label_id>/event/<event_id>', methods=['DELETE'])
@jwt_required()
def delete_default_share_with_event(event_id, relationship_label_id):
    db = sdb.get_db()

    identity = get_jwt_identity()
    requester_id = f"user:{identity}"
    event_id = f"event:{event_id}"
    label_id = f"relationship_label:{label_id}"

    result = db.query("""
            IF NOT record::exists($event_id) THEN {
                RETURN { "error": "Event not found" };
            };
            IF NOT record::exists($label_id) THEN {
                RETURN { "error": "Label not found" };
            };
            LET $event_permission = (SELECT * FROM has_access_to WHERE in = $requester_id AND out = $event_id);
            IF $event_permission = [] OR NOT (['owner', 'admin'] CONTAINS $event_permission[0].permission) THEN {
                RETURN { "error": "Insufficient event permissions" };
            };
            IF $label_id.owner != $requester_id THEN {
                RETURN { "error": "Insufficient label permissions" };
            };
            LET $relation = (SELECT * FROM default_share WHERE in = $label_id AND out = $event_id);
            IF $relation = [] THEN {
                RETURN { "error": "No existing share found" };
            };
            LET $links = [];
            LET $shares = (SELECT * FROM has_access_to WHERE out = $event_id AND because_of CONTAINS $relation[0].id);
            FOR $share IN $shares {
                UPDATE $share.id SET because_of -= $relation[0].id;
                IF $share.because_of = [] THEN {
                    LET $link = DELETE $share.id RETURN AFTER;
                    $links += $link;
                };

            }
            RETURN { "links": $links, "relation": $relation };
        """)
    
    if result["error"]:
        match result["error"]:
            case 'Event not found':
                return {"error": "Event not found"}, 404
            case 'Label not found':
                return {"error": "Label not found"}, 404
            case 'Insufficient event permissions':
                return {"error": "User does not have permission to unshare this event"}, 403
            case 'Insufficient label permissions':
                return {"error": "User does not own this label"}, 403
            case 'No existing share found':
                return {"error": "No existing share found for this label and event"}, 404

    return jsonify({
        "message": "Share removed successfully",
        "links": result["links"],
        "relation": result["relation"]
    })