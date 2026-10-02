"""Session reports: structured one-page reports per client session.

Full CRUD for clinicians (author or admin only), file attachments, and
export as a downloadable formatted report. Reports are per-client and
per-session; patients never see this router (their views are separate).
"""

import os
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session

from app.core.api_response import ok
from app.core.database import get_db
from app.core.dependencies import require_role
from app.core.input_validator import validate_file_upload
from app.core.structured_errors import ErrorCode, err
from app.models.session_report import SessionReport
from app.models.user import User

router = APIRouter(prefix="/session-reports", tags=["session-reports"])

UPLOAD_DIR = "data/session_report_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)

FIELDS = [
    "presenting_concerns",
    "mental_state",
    "interventions",
    "risk_assessment",
    "progress_note",
    "homework",
    "plan",
]


def _serialize(r: SessionReport) -> dict:
    return {
        "id": r.id,
        "psychologist": r.psychologist_username,
        "patient": r.patient_username,
        "session_date": r.session_date,
        "session_type": r.session_type,
        "duration_min": r.duration_min,
        "title": r.title,
        "presenting_concerns": r.presenting_concerns,
        "mental_state": r.mental_state,
        "interventions": r.interventions,
        "risk_assessment": r.risk_assessment,
        "progress_note": r.progress_note,
        "homework": r.homework,
        "plan": r.plan,
        "file_name": r.file_name or "",
        "has_file": bool(r.file_path),
        "approved_by": r.approved_by,
        "approved_at": r.approved_at,
        "created_at": r.created_at,
        "updated_at": r.updated_at,
    }


def _get_scoped(db: Session, user: User, report_id: int) -> SessionReport:
    report = db.query(SessionReport).filter(SessionReport.id == report_id).first()
    if not report:
        raise err(404, ErrorCode.REPORT_NOT_FOUND, "Report not found")
    if user.role != "admin" and report.psychologist_username != user.username:
        raise err(403, ErrorCode.REPORT_FORBIDDEN, "Only the author or an admin can access this report")
    return report


@router.get("")
def list_reports(
    patient: str = Query("", description="Filter by client username"),
    q: str = Query("", description="Free-text search across decrypted fields"),
    session_type: str = Query("", description="Filter by session type"),
    date_from: str = Query("", description="YYYY-MM-DD inclusive"),
    date_to: str = Query("", description="YYYY-MM-DD inclusive"),
    approved: str = Query("", description="'yes', 'no', or empty for all"),
    limit: int = Query(100, ge=1, le=300),
    user: User = Depends(require_role("psychologist", "admin")),
    db: Session = Depends(get_db),
):
    """List session reports, newest first. Psychologists see only their own."""
    query = db.query(SessionReport)
    if user.role != "admin":
        query = query.filter(SessionReport.psychologist_username == user.username)
    if patient:
        query = query.filter(SessionReport.patient_username == patient)
    if session_type:
        query = query.filter(SessionReport.session_type == session_type)
    if date_from:
        query = query.filter(SessionReport.session_date >= date_from)
    if date_to:
        query = query.filter(SessionReport.session_date <= date_to)
    if approved == "yes":
        query = query.filter(SessionReport.approved_by != "")
    elif approved == "no":
        query = query.filter(SessionReport.approved_by == "")
    rows = query.order_by(SessionReport.session_date.desc(), SessionReport.id.desc()).limit(limit).all()

    if q:
        needle = q.lower()
        rows = [
            r
            for r in rows
            if needle in (r.title or "").lower()
            or needle in (r.presenting_concerns or "").lower()
            or needle in (r.interventions or "").lower()
            or needle in (r.progress_note or "").lower()
            or needle in (r.plan or "").lower()
        ]
    return [_serialize(r) for r in rows]


@router.post("")
def create_report(
    payload: dict = None,
    user: User = Depends(require_role("psychologist", "admin")),
    db: Session = Depends(get_db),
):
    """File a new session report. `patient`, `session_date` required."""
    data = payload or {}
    patient = (data.get("patient") or "").strip()
    session_date = (data.get("session_date") or "").strip()
    if not patient or not session_date:
        raise err(400, ErrorCode.VALIDATION_ERROR, "patient and session_date are required")

    if user.role != "admin":
        target = db.query(User).filter(User.username == patient, User.role == "patient").first()
        if not target:
            raise err(404, ErrorCode.PATIENT_NOT_FOUND, "Patient not found")
        if target.assigned_psych != user.username:
            raise err(403, ErrorCode.NOT_ASSIGNED, "This client is not assigned to you")

    now = datetime.now(UTC).isoformat()
    report = SessionReport(
        psychologist_username=user.username,
        patient_username=patient,
        session_date=session_date,
        session_type=(data.get("session_type") or "Standard session").strip(),
        duration_min=int(data.get("duration_min") or 50),
        title=(data.get("title") or "").strip(),
        created_at=now,
        updated_at=now,
    )
    for f in FIELDS:
        setattr(report, f, (data.get(f) or "").strip())
    db.add(report)
    db.commit()
    db.refresh(report)
    return ok(data=_serialize(report), message="Report filed")


@router.get("/{report_id}")
def get_report(
    report_id: int,
    user: User = Depends(require_role("psychologist", "admin")),
    db: Session = Depends(get_db),
):
    report = _get_scoped(db, user, report_id)
    return _serialize(report)


@router.put("/{report_id}")
def update_report(
    report_id: int,
    payload: dict = None,
    user: User = Depends(require_role("psychologist", "admin")),
    db: Session = Depends(get_db),
):
    """Edit any field of a past report. Author or admin only."""
    report = _get_scoped(db, user, report_id)
    data = payload or {}

    if "patient" in data and data["patient"] and data["patient"] != report.patient_username:
        raise err(
            400, ErrorCode.VALIDATION_ERROR, "Reports cannot be moved between clients", details={"field": "patient"}
        )
    if "session_date" in data and data["session_date"]:
        report.session_date = data["session_date"].strip()
    for key in ("session_type", "title"):
        if key in data and data[key] is not None:
            setattr(report, key, str(data[key]).strip())
    if "duration_min" in data and data["duration_min"]:
        try:
            report.duration_min = int(data["duration_min"])
        except (TypeError, ValueError):
            raise err(
                400, ErrorCode.VALIDATION_ERROR, "duration_min must be a number", details={"field": "duration_min"}
            ) from None
    for f in FIELDS:
        if f in data and data[f] is not None:
            setattr(report, f, str(data[f]).strip())

    report.updated_at = datetime.now(UTC).isoformat()
    db.commit()
    db.refresh(report)
    return ok(data=_serialize(report), message="Report updated")


@router.delete("/{report_id}")
def delete_report(
    report_id: int,
    user: User = Depends(require_role("psychologist", "admin")),
    db: Session = Depends(get_db),
):
    report = _get_scoped(db, user, report_id)
    if report.file_path and os.path.exists(report.file_path):
        try:
            os.remove(report.file_path)
        except OSError:
            pass
    db.delete(report)
    db.commit()
    return ok(message="Report deleted")


@router.put("/{report_id}/approve")
def approve_report(
    report_id: int,
    user: User = Depends(require_role("psychologist", "admin")),
    db: Session = Depends(get_db),
):
    report = _get_scoped(db, user, report_id)
    report.approved_by = user.username
    report.approved_at = datetime.now(UTC).isoformat()
    report.updated_at = report.approved_at
    db.commit()
    return ok(message="Report approved")


@router.post("/{report_id}/upload")
async def upload_attachment(
    report_id: int,
    file: UploadFile = File(...),
    user: User = Depends(require_role("psychologist", "admin")),
    db: Session = Depends(get_db),
):
    """Attach a file (worksheet scan, signed PDF, letter) to a report."""
    report = _get_scoped(db, user, report_id)
    content = await validate_file_upload(file)
    ext = os.path.splitext(file.filename or "file")[1]
    fname = f"report_{report_id}{ext}"
    dest = os.path.join(UPLOAD_DIR, fname)
    with open(dest, "wb") as f:
        f.write(content)
    report.file_path = dest
    report.file_name = (file.filename or fname)[:200]
    report.updated_at = datetime.now(UTC).isoformat()
    db.commit()
    return ok(data={"file_name": report.file_name}, message="Attachment uploaded")


@router.get("/{report_id}/attachment")
def download_attachment(
    report_id: int,
    user: User = Depends(require_role("psychologist", "admin")),
    db: Session = Depends(get_db),
):
    report = _get_scoped(db, user, report_id)
    if not report.file_path or not os.path.exists(report.file_path):
        raise err(404, ErrorCode.ATTACHMENT_NOT_FOUND, "No attachment on this report")
    return FileResponse(report.file_path, filename=report.file_name or "attachment")


@router.get("/{report_id}/export")
def export_report(
    report_id: int,
    user: User = Depends(require_role("psychologist", "admin")),
    db: Session = Depends(get_db),
):
    """Download the report as a formatted one-page text document."""
    r = _get_scoped(db, user, report_id)
    client = db.query(User).filter(User.username == r.patient_username).first()
    client_name = (client.name if client else r.patient_username) or r.patient_username

    def section(label: str, body: str) -> str:
        body = (body or "").strip()
        if not body:
            return ""
        wrapped_lines = []
        for para in body.split("\n"):
            line = ""
            for word in para.split():
                if len(line) + len(word) + 1 > 92:
                    wrapped_lines.append(line)
                    line = word
                else:
                    line = f"{line} {word}".strip()
            wrapped_lines.append(line)
        return f"\n{label.upper()}\n{'-' * len(label)}\n" + "\n".join(wrapped_lines) + "\n"

    lines = [
        "=" * 94,
        "SESSION REPORT — SENTINEL CLINICAL RECORD".center(94),
        "=" * 94,
        f"Client: {client_name} (@{r.patient_username})".ljust(62) + f"Date: {r.session_date}",
        f"Clinician: {r.psychologist_username}".ljust(62) + f"Type: {r.session_type} ({r.duration_min} min)",
        (f"Title: {r.title}" if r.title else ""),
        ("Approved by " + r.approved_by + " at " + r.approved_at) if r.approved_by else "UNAPPROVED DRAFT",
        "-" * 94,
    ]
    for label, field in [
        ("Presenting concerns", r.presenting_concerns),
        ("Mental state examination", r.mental_state),
        ("Interventions this session", r.interventions),
        ("Risk assessment", r.risk_assessment),
        ("Progress since last session", r.progress_note),
        ("Homework assigned", r.homework),
        ("Plan / next steps", r.plan),
    ]:
        chunk = section(label, field)
        if chunk:
            lines.append(chunk)
    if r.file_name:
        lines.append(f"\nATTACHMENT: {r.file_name}")
    lines.append("\n" + "=" * 94)
    lines.append("Confidential clinical record — handle under your clinic's privacy policy.".center(94))
    lines.append("=" * 94)

    text = "\n".join(line for line in lines if line is not None)
    filename = f"session_report_{r.patient_username}_{r.session_date}.txt"
    return Response(
        content=text,
        media_type="text/plain",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
