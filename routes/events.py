# Routes relating to events

from flask import Blueprint, request
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

@events_bp.route('/<int:event_id>', methods=['GET'])
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

@events_bp.route('/<int:event_id>', methods=['DELETE'])
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