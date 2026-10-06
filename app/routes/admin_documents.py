from datetime import datetime
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from flask import Blueprint, current_app, flash, redirect, render_template, send_file, url_for, request, abort
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models.compliance import DocumentArchive
from app.rbac.decorators import permission_required
from app.audit.service import AuditService

admin_documents_bp = Blueprint("admin_documents", __name__, url_prefix="/admin/documents")
ALLOWED = {"pdf", "doc", "docx", "xls", "xlsx", "csv", "txt", "md", "png", "jpg", "jpeg", "webp"}


def _extension(name):
    return name.rsplit(".", 1)[-1].lower() if "." in name else ""


@admin_documents_bp.route("/", methods=["GET", "POST"])
@login_required
@permission_required("documents.manage")
def index():
    if request.method == "POST":
        uploaded = request.files.get("document")
        title = (request.form.get("title") or "").strip()
        document_type = (request.form.get("document_type") or "operational").strip()[:80]
        description = (request.form.get("description") or "").strip()
        version = (request.form.get("version") or "").strip()[:60]
        if not uploaded or not uploaded.filename or not title:
            flash("A title and document are required.", "danger")
            return redirect(url_for("admin_documents.index"))
        ext = _extension(uploaded.filename)
        if ext not in ALLOWED:
            flash("That file type is not allowed.", "danger")
            return redirect(url_for("admin_documents.index"))
        data = uploaded.read()
        if len(data) > current_app.config["AUTH_DOCUMENT_MAX_BYTES"]:
            flash("The document exceeds the configured size limit.", "danger")
            return redirect(url_for("admin_documents.index"))
        digest = sha256(data).hexdigest()
        stored = f"{uuid4().hex}.{ext}"
        root = Path(current_app.config["DOCUMENT_ARCHIVE_DIR"]).resolve()
        root.mkdir(parents=True, exist_ok=True)
        target = root / stored
        target.write_bytes(data)
        doc = DocumentArchive(
            title=title,
            document_type=document_type,
            description=description,
            version=version or None,
            effective_date=datetime.utcnow().date(),
            original_filename=secure_filename(uploaded.filename)[:255],
            stored_filename=stored,
            storage_path=str(target),
            mime_type=uploaded.mimetype,
            file_size=len(data),
            sha256=digest,
            uploaded_by_id=current_user.id,
        )
        db.session.add(doc)
        db.session.commit()
        AuditService.log(action="documents.upload", category="admin", resource="DocumentArchive", resource_id=doc.public_id, description=f"Archived {doc.title}")
        flash("Document archived successfully.", "success")
        return redirect(url_for("admin_documents.index"))
    documents = DocumentArchive.query.order_by(DocumentArchive.created_at.desc()).all()
    return render_template("admin/documents.html", documents=documents)


@admin_documents_bp.get("/<public_id>/download")
@login_required
@permission_required("documents.view")
def download(public_id):
    doc = DocumentArchive.query.filter_by(public_id=public_id, is_active=True).first_or_404()
    path = Path(doc.storage_path).resolve()
    root = Path(current_app.config["DOCUMENT_ARCHIVE_DIR"]).resolve()
    if root not in path.parents or not path.is_file():
        abort(404)
    AuditService.log(action="documents.download", category="admin", resource="DocumentArchive", resource_id=doc.public_id, description=f"Downloaded {doc.title}")
    return send_file(path, as_attachment=True, download_name=doc.original_filename, mimetype=doc.mime_type)


@admin_documents_bp.post("/<public_id>/delete")
@login_required
@permission_required("documents.manage")
def delete(public_id):
    doc = DocumentArchive.query.filter_by(public_id=public_id).first_or_404()
    path = Path(doc.storage_path)
    if path.exists():
        path.unlink()
    db.session.delete(doc)
    db.session.commit()
    AuditService.log(action="documents.delete", category="admin", resource="DocumentArchive", resource_id=public_id, description=f"Deleted archived document {doc.title}")
    flash("Document removed from the archive.", "success")
    return redirect(url_for("admin_documents.index"))
