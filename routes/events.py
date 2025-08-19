# Routes relating to events

from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from main import db

events_bp = Blueprint('events', __name__)

@events_bp.route('/events', methods=['POST'])
@jwt_required()
def create_event():
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

@events_bp.route('/events/<int:event_id>', methods=['GET'])
@jwt_required()
def get_event_by_id(event_id):
    user = get_jwt_identity()
    user_id = f"user:{id}"

    # Fetch event
    event_result = db.query("SELECT * FROM calendar_event WHERE id = $event_id", {"event_id": event_id})
    if event_result == []:
        return {"error": "Event not found"}, 404

    # Check if user has access
    access_check = db.query("RETURN (SELECT * FROM has_access_to WHERE in = $user_id AND user = $event_id).permissions CONTAINSANY ['owner', 'admin', 'edit', 'view']", {"user_id": user_id, "event_id": event_id})
    if not access_check:
        return {"error": "User does not have access to this event"}, 403

    return {
        "event": event_result
    }, 200