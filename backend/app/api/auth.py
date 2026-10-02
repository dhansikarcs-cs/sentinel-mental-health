import logging
import secrets
import time as _time
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.core.api_response import ok
from app.core.config import settings
from app.core.database import get_db
from app.core.device_tracker import parse_user_agent
from app.core.location import user_timezone
from app.core.login_rate_limiter import LoginRateLimiter
from app.core.password_validator import PasswordPolicy
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    initialize_encryption,
    is_encryption_ready,
    password_needs_rehash,
    verify_password,
)
from app.core.structured_errors import ErrorCode, err
from app.core.token_blacklist import token_blacklist
from app.events import get_event_bus
from app.models.invite_code import InviteCode
from app.models.user import User
from app.repositories import PatientRepository
from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    ResendVerificationRequest,
    TokenResponse,
    UnlockRequest,
)
from app.services.audit import log_audit
from app.services.notification import send_email

logger = logging.getLogger("sentinel.auth")

router = APIRouter(prefix="/auth", tags=["auth"])

PROFESSIONAL_CODES = {
    "PSY-0001": "SENTINEL-01",
    "PSY-0002": "SENTINEL-02",
    "PSY-0003": "SENTINEL-03",
    "PSY-0004": "SENTINEL-04",
    "PSY-0005": "SENTINEL-05",
}

VERIFICATION_TOKEN_TTL_HOURS = 48


def _verification_link(token: str) -> str:
    base = (settings.cors_origins.split(",")[0].strip() if settings.cors_origins else "") or "http://localhost:5173"
    return f"{base}/verify-email?token={token}"


def issue_email_verification(user: User, db: Session) -> bool:
    """Store a fresh verification token on the user and attempt to email it.
    Email delivery is best-effort: if SMTP is not configured the account can
    still be used (verification is optional), and the admin can resend later.
    Returns True when the email was actually sent."""
    token = secrets.token_urlsafe(32)
    user.verification_token = token
    user.verification_expires = (datetime.now(UTC) + timedelta(hours=VERIFICATION_TOKEN_TTL_HOURS)).isoformat()
    db.commit()
    link = _verification_link(token)
    try:
        return send_email(
            user.email,
            "Verify your Sentinel email",
            "Welcome to Sentinel!\n\n"
            f"Confirm your email address by opening this link:\n{link}\n\n"
            f"The link expires in {VERIFICATION_TOKEN_TTL_HOURS // 24} days. "
            "If you didn't create this account, you can ignore this email.",
        )
    except Exception:  # never block registration on email failures
        logger.exception("verification email send failed for %s", user.username)
        return False


# Demo mode: login lockouts and attempt limiting are disabled entirely.
unlock_rate_limiter = LoginRateLimiter(max_attempts=8, window_seconds=60, lockout_seconds=60)


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    ua = request.headers.get("user-agent", "")
    device_info = parse_user_agent(ua)
    client_ip = request.client.host if request.client else "unknown"

    repo = PatientRepository(db)

    user = repo.get_by_username(req.username)
    if not user:
        log_audit(
            "login_failed",
            user=req.username,
            severity="WARNING",
            status="failure",
            details=f"User not found from {client_ip}",
            device=device_info.device,
            browser=device_info.browser,
            db=db,
        )
        raise err(status.HTTP_401_UNAUTHORIZED, ErrorCode.AUTH_INVALID_CREDENTIALS, "Invalid credentials")

    if not verify_password(req.password, user.password_hash or ""):
        log_audit(
            "login",
            user=req.username,
            severity="WARNING",
            status="failure",
            details=f"Invalid credentials from {client_ip}",
            device=device_info.device,
            browser=device_info.browser,
            db=db,
        )
        db.commit()
        raise err(status.HTTP_401_UNAUTHORIZED, ErrorCode.AUTH_INVALID_CREDENTIALS, "Invalid credentials")

    # Demo mode: heal any stale lock fields left over from earlier versions.
    user.failed_attempts = 0
    user.locked_until = ""
    if password_needs_rehash(user.password_hash or ""):
        user.password_hash = hash_password(req.password)
        logger.info("rehashed password for %s with Argon2id", req.username)
    db.commit()

    get_event_bus().emit("auth:login_success", username=user.username, role=user.role)
    access_token = create_access_token(
        {
            "sub": user.username,
            "role": user.role,
            "user_id": user.username,
            "name": user.name,
        }
    )
    refresh_token = create_refresh_token(user.username)

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        max_age=28800,
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        max_age=86400 * 30,
        path="/",
    )

    role_label = "Patient" if user.role == "patient" else "Psychologist"
    log_audit(
        "login_success",
        user=user.username,
        severity="INFO",
        status="success",
        details=f"Login from {device_info.device} / {device_info.browser}",
        device=device_info.device,
        browser=device_info.browser,
        db=db,
    )
    return TokenResponse(access_token=access_token, refresh_token=refresh_token, role=role_label, name=user.name)


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(req: RefreshRequest, response: Response, db: Session = Depends(get_db)):
    token = req.refresh_token
    payload = decode_refresh_token(token)
    if not payload:
        raise err(status.HTTP_401_UNAUTHORIZED, ErrorCode.SESSION_EXPIRED, "Invalid refresh token")

    jti = payload.get("jti", "")
    if token_blacklist.is_revoked(jti):
        raise err(status.HTTP_401_UNAUTHORIZED, ErrorCode.SESSION_EXPIRED, "Refresh token revoked")

    username = payload.get("sub")
    repo = PatientRepository(db)
    user = repo.get_by_username(username)
    if not user:
        raise err(status.HTTP_401_UNAUTHORIZED, ErrorCode.SESSION_EXPIRED, "User not found")

    # Rotate: revoke the presented refresh token and issue a fresh pair.
    token_blacklist.revoke(jti, float(payload.get("exp", _time.time())))

    new_access = create_access_token(
        {
            "sub": user.username,
            "role": user.role,
            "user_id": user.username,
            "name": user.name,
        }
    )
    new_refresh = create_refresh_token(user.username)

    role_label = "Patient" if user.role == "patient" else "Psychologist"
    response.set_cookie(
        key="access_token",
        value=new_access,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        max_age=28800,
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=new_refresh,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        max_age=86400 * 30,
        path="/",
    )
    return TokenResponse(access_token=new_access, refresh_token=new_refresh, role=role_label, name=user.name)


@router.post("/register")
def register(req: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    PasswordPolicy.validate_strict(req.password)
    ua = request.headers.get("user-agent", "")
    device_info = parse_user_agent(ua)

    repo = PatientRepository(db)
    existing = repo.get_by_username(req.username)
    if existing:
        log_audit(
            "registration_failed",
            user=req.username,
            severity="WARNING",
            status="failure",
            details="Username taken",
            device=device_info.device,
            browser=device_info.browser,
            db=db,
        )
        raise err(status.HTTP_400_BAD_REQUEST, ErrorCode.USERNAME_TAKEN, "Username taken")
    import os as _os

    # Email is optional but must be unique when given (production accounts).
    email = (req.email or "").strip().lower()
    if email:
        email_taken = db.query(User).filter(User.email == email, User.deleted_at.is_(None)).first()
        if email_taken:
            raise err(status.HTTP_400_BAD_REQUEST, ErrorCode.DUPLICATE_RESOURCE, "This email is already registered")

    invite: InviteCode | None = None
    if req.role == "psychologist":
        license_number = (req.license_number or "").strip()
        invite_code = (req.invite_code or "").strip().upper()
        legacy_code = PROFESSIONAL_CODES.get(req.professional_code.strip().upper())

        if license_number:
            dup_license = (
                db.query(User)
                .filter(User.role == "psychologist", User.license_number == license_number, User.deleted_at.is_(None))
                .first()
            )
            if dup_license:
                raise err(
                    status.HTTP_400_BAD_REQUEST,
                    ErrorCode.DUPLICATE_RESOURCE,
                    "This license number is already registered to another clinician",
                )

        if invite_code:
            # Production path: admin-issued invite code.
            invite = db.get(InviteCode, invite_code)
            if not invite or not invite.active:
                raise err(status.HTTP_400_BAD_REQUEST, ErrorCode.VALIDATION_ERROR, "Invalid invite code")
            if invite.expires_at:
                try:
                    if datetime.fromisoformat(invite.expires_at) < datetime.now(UTC):
                        raise err(
                            status.HTTP_400_BAD_REQUEST, ErrorCode.VALIDATION_ERROR, "This invite code has expired"
                        )
                except ValueError:
                    pass
            if invite.max_uses and invite.use_count >= invite.max_uses:
                raise err(status.HTTP_400_BAD_REQUEST, ErrorCode.VALIDATION_ERROR, "This invite code has no uses left")
            if not license_number:
                raise err(
                    status.HTTP_400_BAD_REQUEST,
                    ErrorCode.VALIDATION_ERROR,
                    "License number is required to register as a clinician",
                )
            clinic_code = invite.clinic_code
            occupation = (req.occupation or "").strip()
            professional_code = ""
            assigned_psych = ""
        elif legacy_code:
            # Legacy/demo path: pre-provisioned professional codes.
            existing = db.query(User).filter(User.professional_code == req.professional_code.strip().upper()).first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="This professional code is already registered to another psychologist.",
                )
            clinic_code = legacy_code
            occupation = (req.occupation or "").strip()
            professional_code = req.professional_code.strip().upper()
            assigned_psych = ""
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An invite code from your clinic administrator is required to register as a psychologist.",
            )
    else:
        occupation = req.occupation or ""
        professional_code = ""
        clinic_code = req.clinic_code
        assigned_psych = req.assigned_psych or ""
        if assigned_psych:
            target = repo.get_by_username(assigned_psych)
            if target is None or target.role != "psychologist":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid psychologist selection.",
                )
            if clinic_code and target.clinic_code != clinic_code:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="The selected psychologist does not belong to your chosen clinic.",
                )

    user = User(
        username=req.username,
        password_hash=hash_password(req.password),
        name=req.name,
        role=req.role,
        dob=req.dob,
        country=req.country.strip(),
        timezone=user_timezone(req.country, req.timezone),
        occupation=occupation,
        clinic_code=clinic_code,
        professional_code=professional_code,
        assigned_psych=assigned_psych,
        email=email,
        license_number=(req.license_number or "").strip() if req.role == "psychologist" else "",
        onboarding_step=0,
        encryption_salt=_os.urandom(16).hex(),
        created_at=datetime.now(UTC).isoformat(),
    )
    repo.add(user)
    db.flush()

    if invite is not None:
        invite.use_count = (invite.use_count or 0) + 1
        invite.used_by = req.username

    verification_sent = False
    if email:
        verification_sent = issue_email_verification(user, db)

    get_event_bus().emit("auth:registered", username=req.username, role=req.role, clinic=req.clinic_code)
    log_audit(
        "registration_success",
        user=req.username,
        severity="INFO",
        status="success",
        details="invite_code used" if invite is not None else "",
        device=device_info.device,
        browser=device_info.browser,
        db=db,
    )
    return ok(message="Registered", data={"verification_email_sent": verification_sent} if email else None)


@router.post("/unlock")
def unlock(req: UnlockRequest, request: Request):
    client_ip = request.client.host if request.client else "unknown"
    is_locked, remaining = unlock_rate_limiter.is_locked(client_ip)
    if is_locked:
        log_audit(
            "encryption_unlock_rate_limited",
            severity="WARNING",
            status="failure",
            details=f"Too many unlock attempts from {client_ip}",
            db=None,
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many unlock attempts. Try again in {remaining} seconds.",
            headers={"Retry-After": str(remaining)},
        )
    if is_encryption_ready():
        return ok(data={"ready": True})
    try:
        initialize_encryption(req.passphrase)
        get_event_bus().emit("encryption:unlocked")
        unlock_rate_limiter.record_attempt(client_ip, success=True)
        return ok(data={"ready": True})
    except Exception as e:
        unlock_rate_limiter.record_attempt(client_ip, success=False)
        log_audit("encryption_unlock_failed", severity="ERROR", status="failure", details=str(e))
        raise err(status.HTTP_400_BAD_REQUEST, ErrorCode.ACCOUNT_UNLOCK_FAILED, "Unlock failed") from None


@router.get("/verify-email")
def verify_email(token: str, db: Session = Depends(get_db)):
    """Confirm an email address via the token from the verification link."""
    user = db.query(User).filter(User.verification_token == token, User.deleted_at.is_(None)).first()
    if not user:
        raise err(status.HTTP_400_BAD_REQUEST, ErrorCode.VALIDATION_ERROR, "Invalid or already-used verification link")
    if user.verification_expires:
        try:
            if datetime.fromisoformat(user.verification_expires) < datetime.now(UTC):
                raise err(
                    status.HTTP_400_BAD_REQUEST,
                    ErrorCode.VALIDATION_ERROR,
                    "This verification link has expired — request a new one",
                )
        except ValueError:
            pass
    user.email_verified_at = datetime.now(UTC).isoformat()
    user.verification_token = ""
    user.verification_expires = ""
    db.commit()
    log_audit("email_verified", user=user.username, severity="INFO", status="success", db=db)
    return ok(data={"verified": True, "username": user.username})


@router.post("/resend-verification")
def resend_verification(req: ResendVerificationRequest, request: Request, db: Session = Depends(get_db)):
    """Re-send the verification email. Deliberately does not reveal whether
    the account exists or already has a verified email."""
    client_ip = request.client.host if request.client else "unknown"
    is_locked, remaining = unlock_rate_limiter.is_locked(client_ip)
    if is_locked:
        raise err(
            status.HTTP_429_TOO_MANY_REQUESTS,
            ErrorCode.RATE_LIMITED,
            f"Too many requests. Try again in {remaining} seconds.",
        )
    unlock_rate_limiter.record_attempt(client_ip, success=True)

    repo = PatientRepository(db)
    user = repo.get_by_username(req.username)
    if user and (user.email or "").strip() and not user.email_verified_at:
        issue_email_verification(user, db)
    return ok(message="If that account has an unverified email, a new link is on its way.")


@router.post("/logout")
def logout(request: Request, response: Response):
    token = request.cookies.get("access_token")
    if not token:
        auth_header = request.headers.get("authorization", "")
        if auth_header.lower().startswith("bearer "):
            token = auth_header[7:].strip()
    if not token:
        raise err(status.HTTP_401_UNAUTHORIZED, ErrorCode.UNAUTHORIZED, "Not authenticated")
    from app.core.security import decode_access_token as _decode
    from app.core.security import decode_refresh_token as _decode_refresh

    payload = _decode(token)
    if payload and payload.get("jti"):
        token_blacklist.revoke(payload["jti"], float(payload.get("exp", _time.time())))

    refresh_token = request.cookies.get("refresh_token")
    if refresh_token:
        r_payload = _decode_refresh(refresh_token)
        if r_payload and r_payload.get("jti"):
            token_blacklist.revoke(r_payload["jti"], float(r_payload.get("exp", _time.time())))

    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    return ok(message="Logged out")


@router.get("/encryption-status")
def encryption_status():
    return ok(data={"ready": is_encryption_ready()})
