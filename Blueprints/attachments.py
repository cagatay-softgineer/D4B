import os
import tempfile
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from google.cloud import storage
from werkzeug.utils import secure_filename
from PIL import Image
from database.postgres import get_connection
from util.activity_logger import log_activity

ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
ALLOWED_VIDEO_EXTENSIONS = {"mp4", "mov", "avi"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

attachments_bp = Blueprint("attachments", __name__)

# --- Utility: Check allowed file types ---
def allowed_file(filename):
    ext = filename.rsplit(".", 1)[-1].lower()
    return ext in ALLOWED_IMAGE_EXTENSIONS or ext in ALLOWED_VIDEO_EXTENSIONS

def is_image(filename):
    ext = filename.rsplit(".", 1)[-1].lower()
    return ext in ALLOWED_IMAGE_EXTENSIONS

def to_webp(src_path, dest_path):
    with Image.open(src_path) as img:
        img.save(dest_path, "WEBP", quality=85)  # Adjust quality as needed

# --- Utility: Google Cloud Storage client ---
def get_gcs_bucket():
    client = storage.Client()
    return client.bucket(os.environ["GCS_BUCKET"])

# --- File Upload Endpoint ---
@attachments_bp.route("/upload", methods=["POST"])
@jwt_required()
def upload_file():
    if "file" not in request.files or "job_id" not in request.form:
        return jsonify({"error": "File and job_id required"}), 400
    file = request.files["file"]
    job_id = request.form["job_id"]
    user_id = get_jwt_identity()

    if not allowed_file(file.filename):
        return jsonify({"error": "Invalid file type"}), 415

    filename = secure_filename(file.filename)
    ext = filename.rsplit(".", 1)[-1].lower()

    # Save temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
        file.save(tmp.name)
        file_path = tmp.name

    # Check file size
    if os.path.getsize(file_path) > MAX_FILE_SIZE:
        os.remove(file_path)
        return jsonify({"error": "File exceeds size limit"}), 413

    # Convert images to webp
    if is_image(filename):
        webp_path = file_path.rsplit(".", 1)[0] + ".webp"
        to_webp(file_path, webp_path)
        os.remove(file_path)
        file_path = webp_path
        ext = "webp"
        filename = filename.rsplit(".", 1)[0] + ".webp"

    # Upload to GCS
    bucket = get_gcs_bucket()
    blob = bucket.blob(f"jobs/{job_id}/{filename}")
    blob.upload_from_filename(file_path)
    file_url = blob.public_url

    # Save to job_files table
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO job_files (job_id, uploaded_by, file_url, file_type, file_name, file_size)
                VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
            """, (job_id, user_id, file_url, ext, filename, os.path.getsize(file_path)))
            file_id = cur.fetchone()[0]
            conn.commit()
    os.remove(file_path)
    log_activity("File uploaded", "file", user_id=user_id, details={"job_id": job_id, "filename": filename})
    return jsonify({"id": file_id, "url": file_url, "type": ext}), 201

# --- Download Endpoint ---
@attachments_bp.route("/download/<int:file_id>", methods=["GET"])
@jwt_required()
def download_file(file_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT file_url, file_name FROM job_files WHERE id=%s", (file_id,))
            row = cur.fetchone()
    if not row:
        return jsonify({"error": "File not found"}), 404
    file_url, file_name = row
    # Redirect or stream (for direct download use GCS signed URLs if private)
    return jsonify({"url": file_url, "file_name": file_name})

# --- List Files by Job ---
@attachments_bp.route("/job/<int:job_id>", methods=["GET"])
@jwt_required()
def list_files(job_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM job_files WHERE job_id=%s", (job_id,))
            files = cur.fetchall()
    return jsonify(files), 200
