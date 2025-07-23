from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from psycopg2.extras import RealDictCursor
from database.postgres import get_connection
from database.user_queries import get_user_id_by_email
from util.activity_logger import log_activity

notifications_bp = Blueprint("notifications", __name__)

# Subscribe/Unsubscribe can be implemented if you have user preferences in another table

# ----- Get User Notifications (Paginated Inbox) -----
@notifications_bp.route("/", methods=["GET"])
@jwt_required()
def get_user_notifications():
    user_id = get_user_id_by_email(get_jwt_identity())
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 20))
    offset = (page - 1) * page_size

    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT * FROM notifications
                WHERE user_id=%s
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            """, (user_id, page_size, offset))
            notifications = cur.fetchall()
    return jsonify(notifications), 200

# ----- Mark Notification as Read -----
@notifications_bp.route("/<int:notification_id>/read", methods=["PATCH"])
@jwt_required()
def mark_notification_read(notification_id):
    user_id = get_user_id_by_email(get_jwt_identity())
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE notifications SET status='read'
                WHERE id=%s AND user_id=%s
            """, (notification_id, user_id))
            conn.commit()
    return jsonify({"message": "Notification marked as read"}), 200

# ----- Utility: Notification Trigger -----
def send_notification(user_id, job_id, message, status="unread"):
    """
    Call this from other modules when you need to notify a user.
    - user_id: int, receiver
    - job_id: int or None
    - message: text, notification content
    - status: 'unread', 'read', etc.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO notifications (user_id, job_id, message, status, created_at)
                VALUES (%s, %s, %s, %s, NOW())
            """, (user_id, job_id, message, status))
            conn.commit()
    log_activity("Notification sent", "notification", user_id=user_id,
                 details={"job_id": job_id, "message": message})

# ----- (Optional) Delete Notification -----
@notifications_bp.route("/<int:notification_id>", methods=["DELETE"])
@jwt_required()
def delete_notification(notification_id):
    user_id = get_user_id_by_email(get_jwt_identity())
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                DELETE FROM notifications WHERE id=%s AND user_id=%s
            """, (notification_id, user_id))
            conn.commit()
    return jsonify({"message": "Notification deleted"}), 200
