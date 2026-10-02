from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.core.structured_errors import ErrorCode, err
from app.events import get_event_bus
from app.models.booking import Booking, PsychAvailability
from app.models.user import User
from app.repositories import BookingRepository
from app.repositories.booking_repository import AvailabilityRepository
from app.schemas.booking import AvailabilityCreate, BookingCreate, BookingReschedule, BookingResponse, BookingUpdate
from app.services.audit import log_audit

router = APIRouter(prefix="/bookings", tags=["bookings"])


ACTIVE_BOOKING_STATUSES = ("Pending", "Approved", "Proposed")


def _find_conflict(
    db: Session, psych_username: str, date: str, time: str, exclude_id: int | None = None
) -> Booking | None:
    """An existing active booking for the same clinician at the same date+time."""
    q = db.query(Booking).filter(
        Booking.psychologist_username == psych_username,
        Booking.date == date,
        Booking.time == time,
        Booking.status.in_(ACTIVE_BOOKING_STATUSES),
    )
    if exclude_id:
        q = q.filter(Booking.id != exclude_id)
    return q.first()


def _availability_allows(db: Session, psych_username: str, date: str, time: str) -> bool:
    """True when the clinician has that date open and the time falls in the window.
    If no availability row exists for the date, we can't validate — allow it."""
    row = (
        db.query(PsychAvailability)
        .filter(
            PsychAvailability.psychologist_username == psych_username,
            PsychAvailability.date == date,
        )
        .first()
    )
    if not row:
        return True
    start = row.start_time or "09:00"
    end = row.end_time or "17:00"
    return start <= time <= end


@router.post("", response_model=BookingResponse)
def create_booking(entry: BookingCreate, user: User = Depends(require_role("patient")), db: Session = Depends(get_db)):
    repo = BookingRepository(db)

    conflict = _find_conflict(db, entry.psychologist_username, entry.date, entry.time)
    if conflict:
        raise err(
            409,
            ErrorCode.BOOKING_SLOT_CONFLICT,
            "That slot was just taken — please pick another time",
            details={"date": entry.date, "time": entry.time},
        )
    if not _availability_allows(db, entry.psychologist_username, entry.date, entry.time):
        raise err(
            400,
            ErrorCode.BOOKING_OUTSIDE_AVAILABILITY,
            "That time is outside the clinician's open hours for that date",
            details={"date": entry.date, "time": entry.time},
        )

    booking = Booking(
        patient_username=user.username,
        psychologist_username=entry.psychologist_username,
        date=entry.date,
        time=entry.time,
        session_type=entry.session_type,
        members=entry.members,
        contact=entry.contact,
        explanation=entry.explanation,
        status="Pending",
        created_at=datetime.now(UTC).isoformat(),
    )
    repo.add(booking)
    _notify_counterpart(
        db,
        booking,
        user,
        "📅 New session request",
        f"{user.username} requested a session on {booking.date} at {booking.time} — review it in your queue",
    )
    get_event_bus().emit(
        "booking:created",
        booking_id=booking.id,
        patient_username=user.username,
        psych=entry.psychologist_username,
        date=entry.date,
    )
    return booking


@router.get("", response_model=list[BookingResponse])
def get_bookings(
    status: str = Query("", description="Comma-separated statuses, e.g. Pending,Approved"),
    date_from: str = Query("", description="YYYY-MM-DD inclusive"),
    date_to: str = Query("", description="YYYY-MM-DD inclusive"),
    upcoming: bool = Query(False, description="Only sessions today or later"),
    past: bool = Query(False, description="Only sessions before today"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Bookings with optional status/date filters (both roles)."""
    repo = BookingRepository(db)
    if user.role == "psychologist":
        bookings = repo.get_for_psychologist(user.username)
    else:
        bookings = repo.get_for_patient(user.username)

    if status:
        wanted = {s.strip().lower() for s in status.split(",") if s.strip()}
        bookings = [b for b in bookings if (b.status or "").lower() in wanted]

    today = datetime.now(UTC).date().isoformat()
    if upcoming:
        bookings = [b for b in bookings if b.date >= today]
    if past:
        bookings = [b for b in bookings if b.date < today]
    if date_from:
        bookings = [b for b in bookings if b.date >= date_from]
    if date_to:
        bookings = [b for b in bookings if b.date <= date_to]

    return bookings


@router.put("/{booking_id}/reschedule")
def reschedule_booking(
    booking_id: int,
    update: BookingReschedule,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Move a booking to another date/time.

    The booking's owner (patient) or the assigned psychologist may reschedule.
    The clinician may move any of their bookings; a patient only their own,
    and only while the booking is still Pending or Proposed.
    """
    repo = BookingRepository(db)
    booking = repo.get_by_id(booking_id)
    if not booking:
        raise err(404, ErrorCode.BOOKING_NOT_FOUND, "Booking not found")

    is_owner = booking.patient_username == user.username
    is_psych = user.role == "psychologist" and booking.psychologist_username == user.username
    if not (is_owner or is_psych or user.role == "admin"):
        raise err(403, ErrorCode.OWNER_ONLY, "Not authorized to change this booking")
    if is_owner and not is_psych and booking.status not in ("Pending", "Proposed"):
        raise err(
            403,
            ErrorCode.BOOKING_INVALID_TRANSITION,
            "Only pending requests can be rescheduled from your side — contact your clinician",
            details={"status": booking.status},
        )
    if not update.date or not update.time:
        raise err(400, ErrorCode.VALIDATION_ERROR, "Both date and time are required")

    conflict = _find_conflict(db, booking.psychologist_username, update.date, update.time, exclude_id=booking.id)
    if conflict:
        raise err(
            409,
            ErrorCode.BOOKING_SLOT_CONFLICT,
            "You already have a session at that time — pick another slot",
            details={"date": update.date, "time": update.time},
        )

    old = f"{booking.date} {booking.time}"
    booking.date = update.date
    booking.time = update.time
    if booking.status == "Approved" and is_psych:
        booking.status = "Pending"  # a moved appointment needs re-confirmation
    db.commit()
    _notify_counterpart(
        db, booking, user, "📅 Session moved", f"The session was moved from {old} to {update.date} {update.time}"
    )
    get_event_bus().emit(
        "booking:rescheduled",
        booking_id=booking_id,
        patient_username=booking.patient_username,
        psych=user.username,
        old=old,
        new=f"{update.date} {update.time}",
    )
    return {"message": f"Moved from {old} to {update.date} {update.time}"}


def _notify_counterpart(
    db: Session, booking: Booking, actor: User, title: str, message: str, ntype: str = "info"
) -> None:
    """In-app notification for the booking's other party (patient ↔ psych)."""
    try:
        from app.services.notify import create_notification

        recipient = (
            booking.psychologist_username if actor.username == booking.patient_username else booking.patient_username
        )
        if not recipient:
            return
        create_notification(
            db,
            patient_username=booking.patient_username,
            title=title,
            message=message,
            notification_type=ntype,
            recipient_username=recipient if recipient != booking.patient_username else None,
        )
    except Exception:
        pass


@router.put("/{booking_id}/status")
def update_booking_status(
    booking_id: int,
    update: BookingUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Change a booking's status.

    Clinicians: any transition on their bookings. Patients: may accept or
    decline a session Proposed to them, and may cancel their own upcoming
    requests/appointments — nothing else.
    """
    repo = BookingRepository(db)
    booking = repo.get_by_id(booking_id)
    if not booking:
        raise err(404, ErrorCode.BOOKING_NOT_FOUND, "Booking not found")

    is_psych = user.role == "psychologist" and booking.psychologist_username == user.username
    is_owner = booking.patient_username == user.username
    if not (is_psych or is_owner or user.role == "admin"):
        raise err(403, ErrorCode.FORBIDDEN, "Not authorized to change this booking")

    if is_owner and not is_psych:
        allowed = {
            ("Proposed", "Approved"),  # accept the suggested slot
            ("Proposed", "Rejected"),  # decline it
            ("Pending", "Cancelled"),  # withdraw own request
            ("Approved", "Cancelled"),  # cancel own confirmed appointment
        }
        if (booking.status, update.status) not in allowed:
            raise err(
                403,
                ErrorCode.BOOKING_INVALID_TRANSITION,
                "You can accept/decline suggested sessions and cancel your own — other changes go through your clinician",
                details={"from": booking.status, "to": update.status},
            )

    booking.status = update.status
    db.commit()

    messages = {
        "Approved": f"Your session on {booking.date} at {booking.time} was confirmed ✅"
        if is_psych
        else f"{booking.patient_username} accepted the proposed session on {booking.date} at {booking.time}",
        "Rejected": f"The request for {booking.date} at {booking.time} was declined"
        if is_psych
        else f"{booking.patient_username} declined the proposed session on {booking.date}",
        "Cancelled": f"The session on {booking.date} at {booking.time} was cancelled",
        "Completed": f"Session on {booking.date} completed — well done",
    }
    _notify_counterpart(
        db,
        booking,
        user,
        f"📅 Booking {update.status}",
        messages.get(update.status, f"Booking status changed to {update.status}"),
    )

    get_event_bus().emit(
        "booking:status_updated",
        booking_id=booking_id,
        patient_username=booking.patient_username,
        psych=user.username,
        status=update.status,
    )
    return {"message": "Updated"}


@router.post("/availability")
def set_availability(
    entry: AvailabilityCreate, user: User = Depends(require_role("psychologist")), db: Session = Depends(get_db)
):
    avail_repo = AvailabilityRepository(db)
    existing = avail_repo.get_by_psych_and_date(user.username, entry.date)
    if existing:
        existing.start_time = entry.start_time
        existing.end_time = entry.end_time
    else:
        avail = PsychAvailability(
            psychologist_username=user.username,
            date=entry.date,
            start_time=entry.start_time,
            end_time=entry.end_time,
            created_at=datetime.now(UTC).isoformat(),
        )
        db.add(avail)
    db.commit()
    return {"message": "Availability set"}


@router.get("/{booking_id}/ics")
def download_ics(
    booking_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Download the session as an .ics calendar file.

    Owner or clinician only. Times are floating local times (no TZID), which
    every calendar app renders as local — correct for in-person sessions.
    """
    repo = BookingRepository(db)
    booking = repo.get_by_id(booking_id)
    if not booking:
        raise err(404, ErrorCode.BOOKING_NOT_FOUND, "Booking not found")
    if (
        booking.patient_username != user.username
        and booking.psychologist_username != user.username
        and user.role != "admin"
    ):
        raise err(403, ErrorCode.OWNER_ONLY, "Not authorized")

    def _fold(line: str) -> str:
        # RFC 5545: lines <= 75 octets, continuation lines start with a space
        out, line = [], line
        while len(line.encode("utf-8")) > 75:
            cut = 74
            while len(line[:cut].encode("utf-8")) > 74:
                cut -= 1
            out.append(line[:cut])
            line = " " + line[cut:]
        out.append(line)
        return "\r\n".join(out)

    def _esc(s: str) -> str:
        return s.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")

    date_compact = booking.date.replace("-", "")
    time_compact = booking.time.replace(":", "") + "00"
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    who = (
        booking.patient_username
        if user.username == booking.psychologist_username
        else (booking.psychologist_username or "your clinician")
    )

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Sentinel//Booking//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "BEGIN:VEVENT",
        f"UID:sentinel-booking-{booking.id}@sentinel",
        f"DTSTAMP:{stamp}",
        f"DTSTART:{date_compact}T{time_compact}",
        f"DTEND:{date_compact}T{(datetime.strptime(booking.time, '%H:%M') + timedelta(hours=1)).strftime('%H%M')}00",
        _fold(f"SUMMARY:{_esc('Session with ' + who)}"),
        _fold(f"DESCRIPTION:{_esc((booking.explanation or 'Sentinel session')[:300])}"),
        "END:VEVENT",
        "END:VCALENDAR",
    ]
    ics = "\r\n".join(lines) + "\r\n"
    log_audit(
        "booking_ics_downloaded",
        user=user.username,
        role=user.role,
        severity="INFO",
        status="success",
        resource=str(booking_id),
        db=db,
    )
    from fastapi.responses import Response

    return Response(
        content=ics,
        media_type="text/calendar; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="sentinel-session-{booking.id}.ics"'},
    )


@router.get("/next-free/{psych_username}")
def next_free_slots(
    psych_username: str,
    count: int = Query(3, ge=1, le=10),
    db: Session = Depends(get_db),
):
    """The clinician's next genuinely free slots (date open + time not taken).

    Walks their availability windows forward from today, steps the window in
    30-minute increments, and skips anything with an active booking. Public to
    any authenticated user so the booking form can react to conflicts.
    """
    windows = (
        db.query(PsychAvailability)
        .filter(
            PsychAvailability.psychologist_username == psych_username,
            PsychAvailability.date >= datetime.now(UTC).date().isoformat(),
        )
        .order_by(PsychAvailability.date)
        .limit(30)
        .all()
    )
    taken = {
        (b.date, b.time)
        for b in db.query(Booking)
        .filter(Booking.psychologist_username == psych_username, Booking.status.in_(ACTIVE_BOOKING_STATUSES))
        .all()
    }

    free: list[dict] = []
    for w in windows:
        start_h, start_m = (w.start_time or "09:00").split(":")
        end_h, end_m = (w.end_time or "17:00").split(":")
        t = int(start_h) * 60 + int(start_m)
        end = int(end_h) * 60 + int(end_m)
        while t + 60 <= end and len(free) < count:  # sessions are 1 hour
            hh, mm = divmod(t, 60)
            time = f"{hh:02d}:{mm:02d}"
            if (w.date, time) not in taken:
                free.append({"date": w.date, "time": time})
            t += 30
        if len(free) >= count:
            break
    return {"psychologist": psych_username, "free_slots": free}


@router.get("/calendar")
def booking_calendar(
    year: int = Query(...),
    month: int = Query(..., ge=1, le=12),
    user: User = Depends(require_role("psychologist", "admin")),
    db: Session = Depends(get_db),
):
    """Month view for the clinician's calendar: booked sessions grouped by date.

    Only active statuses are shown (Pending/Approved/Proposed) — cancelled and
    rejected requests are noise. Includes the availability window per date so
    the UI can render both open-hours and booked sessions in one pass.
    """
    prefix = f"{year:04d}-{month:02d}-"
    active = (
        db.query(Booking)
        .filter(
            Booking.psychologist_username == user.username,
            Booking.date.like(f"{prefix}%"),
            Booking.status.in_(ACTIVE_BOOKING_STATUSES),
        )
        .order_by(Booking.date, Booking.time)
        .all()
    )
    windows = {
        r.date: {"start_time": r.start_time or "09:00", "end_time": r.end_time or "17:00"}
        for r in db.query(PsychAvailability)
        .filter(PsychAvailability.psychologist_username == user.username, PsychAvailability.date.like(f"{prefix}%"))
        .all()
    }

    by_date: dict[str, list[dict]] = {}
    for b in active:
        by_date.setdefault(b.date, []).append(
            {
                "id": b.id,
                "time": b.time,
                "patient": b.patient_username,
                "session_type": b.session_type or "",
                "status": b.status,
            }
        )

    return {
        "year": year,
        "month": month,
        "sessions": [{"date": d, **(windows.get(d) or {}), "bookings": items} for d, items in sorted(by_date.items())],
        "open_dates": sorted(windows.keys()),
    }


@router.get("/availability/me")
def get_my_availability(
    detailed: bool = Query(False, description="Return full slot objects with start/end times"),
    user: User = Depends(require_role("psychologist")),
    db: Session = Depends(get_db),
):
    avail_repo = AvailabilityRepository(db)
    slots = avail_repo.get_for_psychologist(user.username)
    if detailed:
        return [
            {"id": s.id, "date": s.date, "start_time": s.start_time or "09:00", "end_time": s.end_time or "17:00"}
            for s in slots
        ]
    return [s.date for s in slots]


@router.get("/availability/{psych_username}")
def get_availability(psych_username: str, db: Session = Depends(get_db)):
    """Public (patient-facing) view of a clinician's open dates with time windows."""
    avail_repo = AvailabilityRepository(db)
    slots = avail_repo.get_for_psychologist(psych_username)
    today = datetime.now(UTC).date().isoformat()
    return [
        {"id": s.id, "date": s.date, "start": s.start_time or "09:00", "end": s.end_time or "17:00"}
        for s in slots
        if s.date >= today  # past dates are noise for booking
    ]


@router.delete("/availability/id/{slot_id}")
def delete_availability(
    slot_id: int, user: User = Depends(require_role("psychologist")), db: Session = Depends(get_db)
):
    avail_repo = AvailabilityRepository(db)
    slot = avail_repo.get_by_slot_id(slot_id, user.username)
    if not slot:
        raise err(404, ErrorCode.AVAILABILITY_NOT_FOUND, "Availability slot not found")
    avail_repo.delete(slot)
    return {"message": "Deleted"}


@router.delete("/availability/date/{date}")
def delete_availability_date(
    date: str, user: User = Depends(require_role("psychologist")), db: Session = Depends(get_db)
):
    avail_repo = AvailabilityRepository(db)
    slot = avail_repo.get_by_date(date, user.username)
    if not slot:
        raise err(404, ErrorCode.AVAILABILITY_NOT_FOUND, "No availability set for that date")
    avail_repo.delete(slot)
    return {"message": "Deleted"}
