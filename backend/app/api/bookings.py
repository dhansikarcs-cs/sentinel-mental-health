from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.events import get_event_bus
from app.models.booking import Booking, PsychAvailability
from app.models.user import User
from app.repositories import BookingRepository
from app.repositories.booking_repository import AvailabilityRepository
from app.schemas.booking import AvailabilityCreate, BookingCreate, BookingResponse, BookingUpdate

router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.post("", response_model=BookingResponse)
def create_booking(entry: BookingCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    repo = BookingRepository(db)
    if user.role == "patient":
        patient_username = user.username
        psychologist_username = entry.psychologist_username
        status = "Pending"
    elif user.role == "psychologist":
        patient_username = entry.patient_username
        psychologist_username = user.username
        status = "Proposed"
        if not patient_username:
            return {"error": "patient_username is required when proposing a slot"}
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    booking = Booking(
        patient_username=patient_username,
        psychologist_username=psychologist_username,
        date=entry.date,
        time=entry.time,
        session_type=entry.session_type,
        members=entry.members,
        contact=entry.contact,
        explanation=entry.explanation,
        status=status,
        created_at=datetime.now(UTC).isoformat(),
    )
    repo.add(booking)
    get_event_bus().emit(
        "booking:created",
        booking_id=booking.id,
        patient_username=patient_username,
        psych=psychologist_username,
        date=entry.date,
    )
    return booking


@router.get("", response_model=list[BookingResponse])
def get_bookings(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    repo = BookingRepository(db)
    if user.role == "psychologist":
        return repo.get_for_psychologist(user.username)
    return repo.get_for_patient(user.username)


@router.put("/{booking_id}/status")
def update_booking_status(
    booking_id: int,
    update: BookingUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = BookingRepository(db)
    booking = repo.get_by_id(booking_id)
    if not booking:
        return {"error": "Not found"}
    is_patient = user.role == "patient"
    is_psych = user.role == "psychologist"
    if not (is_patient or is_psych):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    if is_patient and booking.patient_username != user.username:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    if is_psych and booking.psychologist_username != user.username:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    if is_patient and booking.status != "Proposed":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    booking.status = update.status
    db.commit()
    get_event_bus().emit(
        "booking:status_updated",
        booking_id=booking_id,
        patient_username=booking.patient_username,
        psych=booking.psychologist_username,
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


@router.get("/availability/me")
def get_my_availability(user: User = Depends(require_role("psychologist")), db: Session = Depends(get_db)):
    avail_repo = AvailabilityRepository(db)
    slots = avail_repo.get_for_psychologist(user.username)
    return [s.date for s in slots]


@router.get("/availability/{psych_username}")
def get_availability(psych_username: str, db: Session = Depends(get_db)):
    avail_repo = AvailabilityRepository(db)
    slots = avail_repo.get_for_psychologist(psych_username)
    return [{"id": s.id, "date": s.date, "start": s.start_time, "end": s.end_time} for s in slots]


@router.delete("/availability/id/{slot_id}")
def delete_availability(
    slot_id: int, user: User = Depends(require_role("psychologist")), db: Session = Depends(get_db)
):
    avail_repo = AvailabilityRepository(db)
    slot = avail_repo.get_by_slot_id(slot_id, user.username)
    if not slot:
        return {"error": "Not found"}
    avail_repo.delete(slot)
    return {"message": "Deleted"}


@router.delete("/availability/date/{date}")
def delete_availability_date(
    date: str, user: User = Depends(require_role("psychologist")), db: Session = Depends(get_db)
):
    avail_repo = AvailabilityRepository(db)
    slot = avail_repo.get_by_date(date, user.username)
    if not slot:
        return {"error": "Not found"}
    avail_repo.delete(slot)
    return {"message": "Deleted"}
