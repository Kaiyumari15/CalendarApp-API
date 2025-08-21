# Routes relating to friends

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from extensions import sdb

social_bp = Blueprint('social', __name__)

@social_bp.route('/friends', methods=['GET'])
@jwt_required()
def get_friends():
    db = sdb.get_db()

    user = get_jwt_identity()
    user_id = f"user:{user}"

    result = db.query(
        """
        LET $friends = SELECT * FROM relationship_with WHERE in = $user_id AND type = 'friends';
        RETURN $friends;
        """,
        {"user_id": user_id}
    )

    return {
        "friends": result
    }, 200

@social_bp.route('/following', methods=['GET'])
@jwt_required()
def get_following():
    db = sdb.get_db()

    user = get_jwt_identity()
    user_id = f"user:{user}"

    result = db.query(
        """
        LET $following = SELECT * FROM relationship_with WHERE in = $user_id AND (type = 'following' OR type = 'friends');
        RETURN $following;
        """,
        {"user_id": user_id}
    )

    return {
        "following": result
    }, 200

@social_bp.route('/following', methods=['POST'])
@jwt_required()
def follow_user():
    db = sdb.get_db()

    user = get_jwt_identity()
    requester_id = f"user:{user}"

    data = request.get_json()
    target_user_id = data.get("target_user_id")

    if not target_user_id:
        return {"error": "Target user ID is required"}, 400
    target_user_id = f"user:{target_user_id}"

    # Create a following relationship
    result = db.query(
        """
        IF NOT (record::exists($target_user_id)) THEN {
            RETURN {"error": "Target user does not exist"};
        };
        LET $reverse_relation = SELECT * FROM relationship_with WHERE in = $target_user_id AND out = $requester_id;
        IF $reverse_relation != [] AND $reverse_relation[0].type == 'blocked' THEN {
            RETURN {"error": "Requester blocked by target"};
        };
        RELATE ONLY $requester_id->relationship_with->($target_user_id) SET type = 'following', labels = [];
        """,
        {"requester_id": requester_id, "target_user_id": target_user_id}
    )

    if result["error"]:
        match result["error"]:
            case "Target user does not exist":
                return {"error": "Target user does not exist"}, 404
            case "Requester blocked by target":
                return {"error": "You have been blocked by target"}, 403

    return {
        "message": "Successfully followed user",
        "relationship": result}, 201

@social_bp.route('/following/<user_id>', methods=['DELETE'])
@jwt_required()
def unfollow_user(user_id):
    db = sdb.get_db()

    user = get_jwt_identity()
    requester_id = f"user:{user}"
    target_user_id = f"user:{user_id}"

    result = db.query(
        """
        LET $relationship = SELECT * FROM relationship_with WHERE in = $requester_id AND out = $target_user_id;
        IF $relationship == [] THEN {
            RETURN {"error": "Requester not following target"};
        };
        RETURN DELETE $relationship RETURN AFTER;
        """,
        {"requester_id": requester_id, "target_user_id": target_user_id}
    )

    if result["error"]:
        match result["error"]:
            case "Requester not following target":
                return {"error": "You are not following this user"}, 404

    return {
        "message": "Successfully unfollowed user",
        "relationship": result}, 200

@social_bp.route('/followers', methods=['GET'])
@jwt_required()
def get_followers():
    db = sdb.get_db()

    user = get_jwt_identity()
    user_id = f"user:{user}"

    result = db.query(
        """
        LET $followers = SELECT * FROM relationship_with WHERE in = $user_id AND (type = 'follower' OR type = 'friends');
        RETURN $followers;
        """,
        {"user_id": user_id}
    )

    return {
        "followers": result
    }, 200

@social_bp.route('/followers/<user_id>', methods=['DELETE'])
@jwt_required()
def remove_follower(user_id):
    db = sdb.get_db()

    user = get_jwt_identity()
    requester_id = f"user:{user}"
    target_user_id = f"user:{user_id}"

    result = db.query(
        """
        IF NOT (record::exists($target_user_id)) THEN {
            RETURN {"error": "Target user does not exist"};
        };
        LET $relationship = SELECT * FROM relationship_with WHERE in = $target_user_id AND out = $requester_id;
        IF $relationship == [] OR $relationship[0].type = 'blocked' THEN {
            RETURN {"error": "Target is not following requester"};
        };
        LET $reverse_relationship = SELECT * FROM relationship_with WHERE in = $requester_id AND out = $target_user_id;
        IF $reverse_relationship != [] AND $reverse_relationship[0].type = 'friends' THEN {
            UPDATE ONLY $reverse_relationship SET type = 'follows';
        };
        RETURN DELETE $relationship RETURN AFTER;
        """,
        {"requester_id": requester_id, "target_user_id": target_user_id}
    )

    if result["error"]:
        match result["error"]:
            case "Target user does not exist":
                return {"error": "Target user does not exist"}, 404
            case "Target is not following user":
                return {"error": "Target is not following user"}, 404

    return {
        "message": "Successfully unfollowed user",
        "relationship": result
    }, 200

@social_bp.route('/friends/<user_id>', methods=['DELETE'])
@jwt_required()
def remove_friend(user_id):
    db = sdb.get_db()

    user = get_jwt_identity()
    requester_id = f"user:{user}"
    target_user_id = f"user:{user_id}"

    result = db.query(
        """
        IF NOT (record::exists($target_user_id)) THEN {
            RETURN {"error": "Target user does not exist"};
        };
        LET $relationship = SELECT * FROM relationship_with WHERE in = $requester_id AND out = $target_user_id;
        IF $relationship == [] OR $relationship[0].type != 'friends' THEN {
            RETURN {"error": "Target is not friends with requester"};
        };
        LET $reverse_relationship = SELECT * FROM relationship_with WHERE in = $target_user_id AND out = $requester_id;
        UPDATE ONLY $reverse_relationship.id SET type = 'follows';
        UPDATE ONLY $relationship.id SET type = 'follows';
        """,
        {"requester_id": requester_id, "target_user_id": target_user_id}
    )

    if result["error"]:
        match result["error"]:
            case "Target user does not exist":
                return {"error": "Target user does not exist"}, 404
            case "Target is not friends with user":
                return {"error": "Target is not friends with user"}, 404

    return {
        "message": "Successfully unfollowed user",
        "relationship": result
    }, 200

@social_bp.route('/block', methods=['POST'])
@jwt_required()
def block_user():
    db = sdb.get_db()

    user = get_jwt_identity()
    requester_id = f"user:{user}"

    data = request.get_json()
    target_user_id = data.get("target_user_id")

    if not target_user_id:
        return {"error": "Target user ID is required"}, 400
    target_user_id = f"user:{target_user_id}"

    # Create a block relationship
    result = db.query(
        """
        IF NOT (record::exists($target_user_id)) THEN {
            RETURN {"error": "Target user does not exist"};
        };
        LET $reverse_relation = SELECT * FROM relationship_with WHERE in = $target_user_id AND out = $requester_id AND type != 'blocked';
        DELETE ONLY $reverse_relation;
        RELATE ONLY $requester_id->relationship_with->($target_user_id) SET type = 'blocked', labels = [];
        """,
        {"requester_id": requester_id, "target_user_id": target_user_id}
    )

    if result["error"]:
        match result["error"]:
            case "Target user does not exist":
                return {"error": "Target user does not exist"}, 404

    return {
        "message": "Successfully blocked user",
        "relationship": result
    }, 201
