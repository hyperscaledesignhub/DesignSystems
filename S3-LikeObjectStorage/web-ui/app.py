#!/usr/bin/env python3
"""
S3 Storage System - Web UI
Modern, responsive web interface for customers
"""

import os
import json
import time
import hashlib
import mimetypes
from datetime import datetime
from typing import Optional
import requests
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash, send_file
from werkzeug.utils import secure_filename
import tempfile

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Configuration
S3_API_URL = os.getenv("S3_API_URL", "http://localhost:7841")
UPLOAD_FOLDER = tempfile.gettempdir()
MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB

app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

class S3Client:
    """Client for interacting with S3 Storage System API"""
    
    def __init__(self, api_url: str, api_key: str):
        self.api_url = api_url
        self.headers = {"Authorization": f"Bearer {api_key}"}
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    def list_buckets(self):
        """List all buckets"""
        try:
            resp = self.session.get(f"{self.api_url}/buckets", timeout=10)
            return resp.json() if resp.status_code == 200 else []
        except:
            return []
    
    def create_bucket(self, bucket_name: str):
        """Create a new bucket"""
        try:
            resp = self.session.post(
                f"{self.api_url}/buckets",
                json={"bucket_name": bucket_name},
                timeout=10
            )
            return resp.status_code in [200, 201], resp.text
        except Exception as e:
            return False, str(e)
    
    def delete_bucket(self, bucket_name: str):
        """Delete a bucket"""
        try:
            resp = self.session.delete(f"{self.api_url}/buckets/{bucket_name}", timeout=10)
            return resp.status_code in [200, 204], resp.text
        except Exception as e:
            return False, str(e)
    
    def list_objects(self, bucket_name: str, prefix: str = ""):
        """List objects in bucket"""
        try:
            params = {"prefix": prefix} if prefix else {}
            resp = self.session.get(
                f"{self.api_url}/buckets/{bucket_name}/objects",
                params=params,
                timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("objects", [])
            return []
        except:
            return []
    
    def upload_object(self, bucket_name: str, object_key: str, file_data: bytes, content_type: str = None):
        """Upload an object"""
        try:
            headers = {}
            if content_type:
                headers["Content-Type"] = content_type
            
            resp = self.session.put(
                f"{self.api_url}/buckets/{bucket_name}/objects/{object_key}",
                data=file_data,
                headers=headers,
                timeout=60
            )
            return resp.status_code in [200, 201], resp.text
        except Exception as e:
            return False, str(e)
    
    def download_object(self, bucket_name: str, object_key: str):
        """Download an object"""
        try:
            resp = self.session.get(
                f"{self.api_url}/buckets/{bucket_name}/objects/{object_key}",
                timeout=60
            )
            if resp.status_code == 200:
                return True, resp.content, resp.headers.get("Content-Type", "application/octet-stream")
            return False, resp.text, None
        except Exception as e:
            return False, str(e), None
    
    def delete_object(self, bucket_name: str, object_key: str):
        """Delete an object"""
        try:
            resp = self.session.delete(
                f"{self.api_url}/buckets/{bucket_name}/objects/{object_key}",
                timeout=10
            )
            return resp.status_code in [200, 204], resp.text
        except Exception as e:
            return False, str(e)

def get_s3_client():
    """Get S3 client for current session"""
    api_key = session.get("api_key")
    if not api_key:
        return None
    return S3Client(S3_API_URL, api_key)

def format_file_size(size_bytes):
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0 B"
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024.0 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    return f"{size_bytes:.1f} {size_names[i]}"

def format_datetime(dt_str):
    """Format datetime string"""
    try:
        dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return dt_str

@app.route("/")
def index():
    """Home page"""
    if "api_key" not in session:
        return redirect(url_for("login"))
    
    client = get_s3_client()
    buckets = client.list_buckets() if client else []
    
    # Get total stats
    total_buckets = len(buckets)
    total_objects = 0
    total_size = 0
    
    for bucket in buckets:
        objects = client.list_objects(bucket["bucket_name"])
        total_objects += len(objects)
        total_size += sum(obj.get("size_bytes", 0) for obj in objects)
    
    stats = {
        "total_buckets": total_buckets,
        "total_objects": total_objects,
        "total_size": format_file_size(total_size)
    }
    
    return render_template("index.html", buckets=buckets, stats=stats)

@app.route("/login", methods=["GET", "POST"])
def login():
    """Login page"""
    if request.method == "POST":
        api_key = request.form.get("api_key", "").strip()
        
        if not api_key:
            flash("Please enter an API key", "error")
            return render_template("login.html")
        
        # Test API key by making a request
        try:
            client = S3Client(S3_API_URL, api_key)
            buckets = client.list_buckets()
            # If we get here without exception, API key is valid
            session["api_key"] = api_key
            flash("Successfully logged in!", "success")
            return redirect(url_for("index"))
        except:
            flash("Invalid API key or service unavailable", "error")
    
    return render_template("login.html")

@app.route("/logout")
def logout():
    """Logout"""
    session.clear()
    flash("Successfully logged out", "success")
    return redirect(url_for("login"))

@app.route("/buckets")
def buckets():
    """Buckets page"""
    if "api_key" not in session:
        return redirect(url_for("login"))
    
    client = get_s3_client()
    buckets = client.list_buckets() if client else []
    return render_template("buckets.html", buckets=buckets)

@app.route("/buckets/create", methods=["POST"])
def create_bucket():
    """Create a new bucket"""
    if "api_key" not in session:
        return jsonify({"success": False, "message": "Not authenticated"})
    
    bucket_name = request.json.get("bucket_name", "").strip()
    
    if not bucket_name:
        return jsonify({"success": False, "message": "Bucket name is required"})
    
    client = get_s3_client()
    success, message = client.create_bucket(bucket_name)
    
    if success:
        return jsonify({"success": True, "message": f"Bucket '{bucket_name}' created successfully"})
    else:
        return jsonify({"success": False, "message": f"Failed to create bucket: {message}"})

@app.route("/buckets/<bucket_name>/delete", methods=["POST"])
def delete_bucket(bucket_name):
    """Delete a bucket"""
    if "api_key" not in session:
        return jsonify({"success": False, "message": "Not authenticated"})
    
    client = get_s3_client()
    success, message = client.delete_bucket(bucket_name)
    
    if success:
        return jsonify({"success": True, "message": f"Bucket '{bucket_name}' deleted successfully"})
    else:
        return jsonify({"success": False, "message": f"Failed to delete bucket: {message}"})

@app.route("/buckets/<bucket_name>")
def bucket_detail(bucket_name):
    """Bucket detail page"""
    if "api_key" not in session:
        return redirect(url_for("login"))
    
    client = get_s3_client()
    objects = client.list_objects(bucket_name) if client else []
    
    # Process objects for display
    for obj in objects:
        obj["formatted_size"] = format_file_size(obj.get("size_bytes", 0))
        obj["formatted_date"] = format_datetime(obj.get("created_at", ""))
        obj["file_extension"] = os.path.splitext(obj.get("object_name", ""))[1]
    
    # Get folder structure
    folders = set()
    for obj in objects:
        parts = obj["object_name"].split("/")
        for i in range(len(parts) - 1):
            folder_path = "/".join(parts[:i+1])
            folders.add(folder_path)
    
    return render_template(
        "bucket_detail.html", 
        bucket_name=bucket_name, 
        objects=objects,
        folders=sorted(folders)
    )

@app.route("/buckets/<bucket_name>/upload", methods=["POST"])
def upload_object(bucket_name):
    """Upload an object"""
    if "api_key" not in session:
        return jsonify({"success": False, "message": "Not authenticated"})
    
    if "file" not in request.files:
        return jsonify({"success": False, "message": "No file provided"})
    
    file = request.files["file"]
    folder_path = request.form.get("folder_path", "").strip()
    
    if file.filename == "":
        return jsonify({"success": False, "message": "No file selected"})
    
    filename = secure_filename(file.filename)
    object_key = f"{folder_path}/{filename}" if folder_path else filename
    
    # Remove leading slashes
    object_key = object_key.lstrip("/")
    
    # Get content type
    content_type, _ = mimetypes.guess_type(filename)
    if not content_type:
        content_type = "application/octet-stream"
    
    try:
        file_data = file.read()
        client = get_s3_client()
        success, message = client.upload_object(bucket_name, object_key, file_data, content_type)
        
        if success:
            return jsonify({
                "success": True, 
                "message": f"File '{filename}' uploaded successfully",
                "object_key": object_key,
                "size": len(file_data)
            })
        else:
            return jsonify({"success": False, "message": f"Upload failed: {message}"})
    
    except Exception as e:
        return jsonify({"success": False, "message": f"Upload error: {str(e)}"})

@app.route("/buckets/<bucket_name>/objects/<path:object_key>/download")
def download_object(bucket_name, object_key):
    """Download an object"""
    if "api_key" not in session:
        return redirect(url_for("login"))
    
    client = get_s3_client()
    success, data, content_type = client.download_object(bucket_name, object_key)
    
    if success:
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        temp_file.write(data)
        temp_file.close()
        
        filename = os.path.basename(object_key)
        return send_file(
            temp_file.name,
            as_attachment=True,
            download_name=filename,
            mimetype=content_type
        )
    else:
        flash(f"Failed to download file: {data}", "error")
        return redirect(url_for("bucket_detail", bucket_name=bucket_name))

@app.route("/buckets/<bucket_name>/objects/<path:object_key>/delete", methods=["POST"])
def delete_object(bucket_name, object_key):
    """Delete an object"""
    if "api_key" not in session:
        return jsonify({"success": False, "message": "Not authenticated"})
    
    client = get_s3_client()
    success, message = client.delete_object(bucket_name, object_key)
    
    if success:
        return jsonify({"success": True, "message": f"File '{object_key}' deleted successfully"})
    else:
        return jsonify({"success": False, "message": f"Failed to delete file: {message}"})

@app.route("/api/health")
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "service": "web-ui"})

# Template filters
@app.template_filter('datetime')
def datetime_filter(s):
    return format_datetime(s)

@app.template_filter('filesize')
def filesize_filter(s):
    return format_file_size(s)

if __name__ == "__main__":
    print("Starting S3 Storage Web UI...")
    print(f"S3 API URL: {S3_API_URL}")
    print("Access the UI at: http://localhost:9347")
    app.run(host="0.0.0.0", port=9347, debug=True)