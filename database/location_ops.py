from datetime import datetime, timezone
from database.firebase import get_connection

def insert_location(job_id, latitude, longitude, user_id=None, timestamp=None):
    """
    Inserts a location record into Firestore (locations collection).

    Args:
        job_id (int): Required job ID.
        latitude (float): Required latitude.
        longitude (float): Required longitude.
        user_id (int or None): Optional user ID.
        timestamp (datetime or None): Optional timestamp (UTC). If None, set to now.
    Returns:
        dict: Inserted document fields.
    """
    if job_id is None or latitude is None or longitude is None:
        raise ValueError("job_id, latitude, and longitude are required.")

    if timestamp is None:
        timestamp = datetime.now(timezone.utc)

    doc = {
        "job_id": job_id,
        "user_id": user_id,
        "latitude": latitude,
        "longitude": longitude,
        "timestamp": timestamp.isoformat()
    }

    with get_connection() as db:
        db.collection("locations").add(doc)
    return doc
