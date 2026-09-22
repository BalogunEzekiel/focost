from pathlib import Path
from uuid import uuid4

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_from_directory
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from PIL import Image

from app.extensions import db

profile_bp = Blueprint("profile", __name__, url_prefix="/profile")
ALLOWED = {"png", "jpg", "jpeg", "webp"}


@profile_bp.route("/", methods=["GET", "POST"])
@login_required
def index():
    if request.method == "POST":
        current_user.first_name = request.form.get("first_name", current_user.first_name).strip()[:80]
        current_user.last_name = request.form.get("last_name", current_user.last_name).strip()[:80]
        current_user.phone = request.form.get("phone", current_user.phone or "").strip()[:20] or None
        current_user.country = request.form.get("country", current_user.country or "").strip()[:80] or None
        current_user.currency = request.form.get("currency", current_user.currency or "NGN").strip()[:10] or "NGN"
        current_user.occupation = request.form.get("occupation", current_user.occupation or "").strip()[:120] or None
        upload = request.files.get("avatar")
        if upload and upload.filename:
            ext = Path(secure_filename(upload.filename)).suffix.lower().lstrip(".")
            if ext not in ALLOWED:
                flash("Please upload a PNG, JPG, JPEG or WEBP image.", "danger")
                return render_template("profile/index.html")
            upload_dir = Path(current_app.instance_path) / "uploads" / "avatars"
            upload_dir.mkdir(parents=True, exist_ok=True)
            filename = f"{current_user.public_id}_{uuid4().hex}.{ext}"
            try:
                upload.stream.seek(0)
                image = Image.open(upload.stream)
                image.verify()
                upload.stream.seek(0)
            except Exception:
                flash("The selected file is not a valid image.", "danger")
                return render_template("profile/index.html")
            destination = upload_dir / filename
            upload.save(destination)

            # Remove previous uploaded avatar after the new file is safely saved.
            previous = current_user.avatar
            current_user.avatar = f"uploads/avatars/{filename}"
            if previous and previous.startswith("uploads/avatars/"):
                old_path = Path(current_app.instance_path) / previous
                if old_path.exists() and old_path.resolve() != destination.resolve():
                    try:
                        old_path.unlink()
                    except OSError:
                        current_app.logger.warning("Unable to remove previous avatar: %s", old_path)
        db.session.commit()
        flash("Profile updated successfully.", "success")
        return redirect(url_for("profile.index"))
    return render_template("profile/index.html")


@profile_bp.get("/avatar/<path:filename>")
@login_required
def avatar(filename):
    # Avatar files are private user assets. Only serve the authenticated user's
    # own uploaded avatar; never allow arbitrary file access.
    safe_name = Path(filename).name
    if not safe_name.startswith(f"{current_user.public_id}_"):
        return ("", 404)
    directory = Path(current_app.instance_path) / "uploads" / "avatars"
    return send_from_directory(directory, safe_name)
