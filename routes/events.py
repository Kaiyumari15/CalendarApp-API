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
    link_result = db.query("RELATE $user->has_access_to->$calendar_event", {"user": user_id, "calendar_event": full_event_id})

    # Return user and link objects
    return {
        "message": "Event created successfully",
        "event": event_result,
        "link": link_result
    }, 201