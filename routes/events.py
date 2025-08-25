# Routes relating to events

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from extensions import sdb

events_bp = Blueprint('events', __name__)

@events_bp.route('/', methods=['POST'])
@jwt_required()
def create_event():
    db = sdb.get_db()
    
    event_data = request.json
    user = get_jwt_identity()
    user_id = f"user:{id}"

    # Check data is valid 
    if not event_data:
        return {"error": "Event data is required"}, 400
    
    if not event_data["start_time"] or not event_data["end_time"]:
        return {"error": "Start time and end time are required"}, 400

    if not event_data["start_time"] < event_data["end_time"]:
        return {"error": "Start time must be before end time"}, 400

    if not event_data["title"]:
        return {"error": "Title is required"}, 400
    
    # Create event
    event_result = db.query("CREATE calendar_event CONTENT $event_data", {"event_data": event_data})
    full_event_id = event_result[0].id

    # Link user to event
    link_result = db.query("RELATE $user->has_access_to->$calendar_event SET permission='owner', because_of=['owner'], labels=[]", {"user": user_id, "calendar_event": full_event_id})

    # Return user and link objects
    return {
        "message": "Event created successfully",
        "event": event_result,
        "link": link_result
    }, 201

@events_bp.route('/<event_id>', methods=['GET'])
@jwt_required()
def get_event_by_id(event_id):
    db = sdb.get_db()

    user = get_jwt_identity()
    user_id = f"user:{id}"
    
    # Get event and check permissions
    result = db.query(
        """
        LET $event = SELECT * FROM calendar_event WHERE id = $event_id;
        IF $event IS NULL THEN {
            RETURN {
                'error': 'Not found'
            };
        };
        LET $link = (SELECT * FROM has_access_to WHERE in = $user_id AND user = $event_id);
        IF $link.permission CONTAINSNONE ['owner', 'admin', 'edit', 'view'] THEN {
            RETURN {
                'error': 'Insufficient permissions'
            };
        };
        RETURN {
            'event': $event,
            'link': $link
        };
        """,
        {"event_id": event_id})
    # Handle errors
    if result["error"]:
        match result["error"]:
            case 'Not found':
                return {"error": "Event not found"}, 404
            case 'Insufficient permissions':
                return {"error": "User does not have access to this event"}, 403
    # Return event and link objects
    event, link = result["event"], result["link"]
    return {
        "event": event,
        "link": link
    }, 200

@events_bp.route('/<event_id>', methods=["PUT"])
@jwt_required()
def update_event(event_id):
    db = sdb.get_db()

    event_id = f"event:{event_id}"
    event_data = request.json
    requester = get_jwt_identity()
    requester = f"user:{requester}"

    event_data = event_data.get("content", {})

    # Check if event exists
    result = db.query("""
        LET $event = SELECT * FROM calendar_event WHERE id = $event_id;
        IF $event IS NULL THEN {
            RETURN { "error": "Event not found" };
        };
        LET $requester_permission = (SELECT * FROM has_access_to WHERE in = $requester AND event = $event_id);
        IF $requester_permission = [] OR NOT (['owner', 'admin'] CONTAINS $requester_permission[0].permission) THEN {
            RETURN { "error": "Insufficient permissions" };
        };
        BEGIN TRANSACTION;
        LET $updated_event = UPDATE $event MERGE $event_data RETURN AFTER;
        IF $updated_event.start_time > $updated_event.endtime THEN {
            RETURN { "error": "Start time must be before end time" };
        }
        COMMIT TRANSACTION;
        RETURN $updated_event;
    """, {"event_id": event_id, "requester": requester, "event_data": event_data})

    if result["error"]:
        match result["error"]:
            case 'Event not found':
                return {"error": "Event not found"}, 404
            case 'Insufficient permissions':
                return {"error": "User does not have permission to edit this event"}, 403

    return jsonify({
        "message": "Event updated successfully",
        "event": result
    }), 200

@events_bp.route('/<event_id>', methods=['DELETE'])
@jwt_required()
def delete_event(event_id):
    db = sdb.get_db()

    user = get_jwt_identity()
    user_id = f"user:{id}"

    result = db.query(
        """
        IF !record::exists($event) THEN {
            RETURN {
                'error': 'Not found'
            };
        };
        IF (SELECT * FROM has_access_to WHERE user = $user_id AND in = $event_id).permission CONTAINS 'owner' THEN {
            LET $event = DELETE FROM calendar_event WHERE id = $event_id RETURN BEFORE;
            RETURN $event;
        } ELSE {
            RETURN {
                'error': 'Insufficient permissions'
            };
        };
        """,
        {"event_id": event_id, "user_id": user_id}
    )

    if result["error"]:
        match result["error"]:
            case 'Not found':
                return {"error": "Event not found"}, 404
            case 'Insufficient permissions':
                return {"error": "User does not have permission to delete this event"}, 403
            
    return {
        "message": "Event deleted successfully",
        "event": result
    }

@events_bp.route('/owned-by/<user_id>', methods=['GET'])
@jwt_required()
def get_events_by_user(user_id):
    db = sdb.get_db()

    requester_id = get_jwt_identity()
    requester_id = f"user:{requester_id}"

    result = db.query(
        """
        IF !record::exists($user_id) THEN {
                    RETURN {
                'error': 'Not found'
            };
        };
        LET $events = SELECT ->has_access_to(WHERE permission = 'owner')->event<-has_access_to<-user(WHERE id = $requester_id) FROM $user_id;
        RETURN $events;
        """,
        {"user_id": user_id, "requester_id": requester_id}
    )

    if result["error"]:
        match result["error"]:
            case 'Not found':
                return {"error": "User not found"}, 404

    return {
        "events": result
    }, 200

@events_bp.route('/<event_id>/share', methods=['POST'])
@jwt_required()
def share_event(event_id):
    db = sdb.get_db()

    requester = get_jwt_identity()
    requester = f"user:{requester}"

    shares = []

    event_id = f"event:{event_id}"
    data = request.json
    for share in data.get("shares", []):
        user_id = share['user_id']
        permission = share['share']

        if not user_id or not permission or permission not in ['admin', 'edit', 'view']:
            return {"error": "User ID and valid permission are required"}, 400
        user_id = f"user:{user_id}"
        shares.append({"user_id": user_id, "permission": permission})

    result = db.query("""
        IF !record::exists($event_id) THEN {
            RETURN { "error": "Event not found" };
        };
        LET $requester_permission = (SELECT * FROM has_access_to WHERE in = $requester AND event = $event_id);
        IF $requester_permission = [] OR NOT (['owner', 'admin'] CONTAINS $requester_permission) THEN {
            RETURN { "error": "Insufficient permissions" };
        };
        LET $links = [];
        FOR $share IN $shares {
            IF !record::exists($share.user_id) THEN {
                LET $links = array::append($links, { "error": "User $share.user_id not found" });
                CONTINUE;
            };
            LET $existing = (SELECT * FROM has_access_to WHERE user = $share.user_id AND event = $event_id);
            IF $existing = [] THEN {
                LET $link = (RELATE ONLY $share.user_id->has_access_to->$event_id SET permission = $share.permission SET because_of = 'direct invite');
                LET $links = array::append($links, $link);
                CONTINUE;
            };
            IF $existing[0].permission = 'owner' THEN {
                RETURN { "error": "User has higher permission" };
            }
            LET $updated = (UPDATE ONLY $existing[0].id SET permission = $share.permission);
            LET $links = array::append($links, $updated);
        };
        RETURN $links;
    """, {"requester": requester, "event_id": event_id, "shares": shares})

    if result["error"]:
        match result["error"]:
            case 'Event not found':
                return {"error": "Event not found"}, 404
            case 'Insufficient permissions':
                return {"error": "User does not have permission to share this event"}, 403

    return jsonify({
        "links": result
    })

@events_bp.route('/<event_id>/share', methods=['DELETE'])
@jwt_required()
def unshare_event(event_id):
    db = sdb.get_db()

    requester = get_jwt_identity()
    requester = f"user:{requester}"

    event_id = f"event:{event_id}"
    data = request.json
    shares = []
    for share in data.get("shares", []):
        user_id = share['user_id']
        if not user_id:
            return {"error": "User ID is required"}, 400
        user_id = f"user:{user_id}"
        shares.append({"user_id": user_id})

    result = db.query("""
        IF !record::exists($event_id) THEN {
            RETURN { "error": "Event not found" };
        };
        LET $requester_permission = (SELECT * FROM has_access_to WHERE in = $requester AND event = $event_id);
        IF $requester_permission = [] OR NOT (['owner', 'admin'] CONTAINS $requester_permission[0].permission) THEN {
            RETURN { "error": "Insufficient permissions" };
        };
        LET $links = [];
        FOR $share IN $shares {
            IF !record::exists($share.user_id) THEN {
                LET $links = array::append($links, { "error": "User $share.user_id not found" });
                CONTINUE;
            };
            LET $existing = (SELECT * FROM has_access_to WHERE user = $share.user_id AND event = $event_id);
            IF $existing = [] THEN {
                RETURN { "error": "Share not found };
            };
            IF $existing[0].permission = 'owner' THEN {
                RETURN { "error": "User has higher permission" };
            }
            LET $deleted = (DELETE ONLY $existing[0].id);
            LET $links = array::append($links, $deleted);
        };
        RETURN $links;
    """, {"requester": requester, "event_id": event_id, "shares": shares})

    if result["error"]:
        match result["error"]:
            case 'Event not found':
                return {"error": "Event not found"}, 404
            case 'Insufficient permissions':
                return {"error": "User does not have edit permissions on this event"}, 403

    return jsonify({
        "links": result
    })

@events_bp.route('/<event_id>/share', methods=['GET'])
@jwt_required
def get_shares_by_event(event_id):
    db = sdb.get_db()
    event_id = f"event:{event_id}"

    result = db.query("""
        IF !record::exists($event_id) THEN {
            RETURN { "error": "Event not found" };
        };
        LET $requester_permission = (SELECT * FROM has_access_to WHERE user = $requester AND event = $event_id);
        IF $requester_permission = [] OR NOT (['owner', 'admin'] CONTAINS $requester_permission[0].permission.) THEN {
            RETURN { "error": "Insufficient permissions" };
        };
        RETURN (SELECT * FROM has_access_to WHERE event = $event_id);
    """, {"event_id": event_id})

    if result["error"]:
        match result["error"]:
            case 'Event not found':
                return {"error": "Event not found"}, 404
            case 'Insufficient permissions':
                return {"error": "User does not have permission to view shares for this event"}, 403

    return jsonify({
        "links": result
    })

@events_bp.route('/<event_id>/share/<user_id>', methods=['GET'])
@jwt_required()
def get_share_by_event_and_user(event_id, user_id):
    db = sdb.get_db()

    requesting_user = get_jwt_identity()
    event_id = f"event:{event_id}"
    user_id = f"user:{user_id}"

    result = db.query("""
        IF !record::exists($event_id) THEN {
            RETURN { "error": "Event not found" };
        };
        IF !record::exists($user_id) THEN {
            RETURN { "error": "User not found" };
        };
        IF $requesting_user = $user_id THEN {
            RETURN (SELECT * FROM has_access_to WHERE event = $event_id AND user = $user_id);
        };
        LET $requesting_user_permission = (SELECT * FROM has_access_to WHERE user = $requesting_user AND event = $event_id);
        IF $requesting_user != $user_id AND ($requesting_user_permission != [] OR NOT (['owner', 'admin'] CONTAINS $requesting_user_permission[0].permission)) THEN {
            RETURN { "error": "User does not have permission to view this share" };
        };
    """, {"event_id": event_id, "user_id": user_id})

    if result["error"]:
        match result["error"]:
            case 'Event not found':
                return {"error": "Event not found"}, 404
            case 'User not found':
                return {"error": "User not found"}, 404
            case 'Insufficient permissions':
                return {"error": "User does not have permission to view this share"}, 403

    return jsonify({
        "links": result
    })

@events_bp.route('/<event_id>/share/relationship-label/<label_id>', methods=['POST'])
@jwt_required()
def share_event_with_relationship_label(event_id, label_id):
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