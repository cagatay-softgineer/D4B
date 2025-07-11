# database/firebase.py
from contextlib import contextmanager
import os
import firebase_admin
from settings import FirebaseSettings
from firebase_admin import credentials, firestore

_fb = FirebaseSettings()

@contextmanager
def get_connection():
    if not _fb.project_id or not _fb.creds_path:
        raise RuntimeError("FIREBASE_PROJECT_ID and GOOGLE_APPLICATION_CREDENTIALS are required")
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = _fb.creds_path
    current_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    cert_path = os.path.join(current_dir, _fb.creds_path)
    cred = credentials.Certificate(cert=cert_path)
    firebase_admin.initialize_app(
        cred,
        {
            "apiKey": _fb.api_key,
            "authDomain": _fb.auth_domain,
            "projectId": _fb.project_id,
            "storageBucket": _fb.storage_bucket,
            "messagingSenderId": _fb.messaging_sender_id,
            "appId": _fb.app_id,
        },
    )
    db = firestore.client()
    try:
        yield db
    finally:
        pass
