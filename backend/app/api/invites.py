import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.api_response import ok
from app.core.database import get_db
from app.core.dependencies import require_role
from app.core.structured_errors import ErrorCode, err
from app.models.invite_code import InviteCode
from app.models.user import User
from app.schemas.auth import InviteCreateRequest
from app.services.audit import log_audit

router = APIRouter(prefix="/admin/invites", tags=["invites"])


@router.get("")
def list_invites(user: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    """All invite codes with redemption state. Admin only."""
    rows = db.query(InviteCode).order_by(InviteCode.created_at.desc()).limit(200).all()
    now = datetime.now(UTC)
    items = []
    for r in rows:
        expired = False
        if r.expires_at:
            try:
                expired = datetime.fromisoformat(r.expires_at) < now
            except ValueError:
                expired = False
        items.append(
            {
                "code": r.code,
                "clinic_code": r.clinic_code,
                "created_by": r.created_by,
                "created_at": r.created_at,
                "expires_at": r.expires_at,
                "max_uses": r.max_uses,
                "use_count": r.use_count or 0,
                "used_by": r.used_by or "",
                "active": bool(r.active),
                "expired": expired,
                "exhausted": bool(r.max_uses and (r.use_count or 0) >= r.max_uses),
                "revoked": not bool(r.active),
            }
        )
    return ok(data={"invites": items})


@router.post("")
def create_invite(
    req: InviteCreateRequest,
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """Generate a new doctor invite code bound to a clinic."""
    code = f"INV-{secrets.token_urlsafe(9).upper().replace('-', 'A').replace('_', 'B')}"
    while db.get(InviteCode, code):
        code = f"INV-{secrets.token_urlsafe(9).upper().replace('-', 'A').replace('_', 'B')}"
    expires = (datetime.now(UTC) + timedelta(days=req.expires_in_days)).isoformat()
    invite = InviteCode(
        code=code,
        clinic_code=req.clinic_code.strip().upper(),
        created_by=user.username,
        created_at=datetime.now(UTC).isoformat(),
        expires_at=expires,
        max_uses=req.max_uses,
        use_count=0,
        active=1,
    )
    db.add(invite)
    db.commit()
    log_audit(
        "invite_created",
        user=user.username,
        role=user.role,
        resource="invite_code",
        resource_id=code,
        details=f"clinic={invite.clinic_code} max_uses={req.max_uses}",
        db=db,
    )
    return ok(
        data={
            "code": code,
            "clinic_code": invite.clinic_code,
            "expires_at": expires,
            "max_uses": req.max_uses,
        },
        message="Invite created",
    )


@router.delete("/{code}")
def revoke_invite(code: str, user: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    """Revoke (deactivate) an invite code. Kept for audit; not deleted."""
    invite = db.get(InviteCode, code.strip().upper())
    if not invite:
        raise err(404, ErrorCode.NOT_FOUND, "Invite code not found")
    invite.active = 0
    db.commit()
    log_audit(
        "invite_revoked",
        user=user.username,
        role=user.role,
        resource="invite_code",
        resource_id=invite.code,
        db=db,
    )
    return ok(message="Invite revoked")
