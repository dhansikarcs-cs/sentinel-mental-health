from sqlalchemy import Column, Integer, String

from app.core.database import Base


class InviteCode(Base):
    """Admin-issued invite code for psychologist (doctor) sign-up.

    A production clinic provisions doctors by generating invite codes in the
    admin console. Each code is bound to a clinic, can be limited in uses and
    expiry, and is deactivated (not deleted) on revoke for audit purposes.
    """

    __tablename__ = "invite_codes"

    code = Column(String, primary_key=True)  # stored uppercase
    clinic_code = Column(String, nullable=False, default="")
    created_by = Column(String, default="")
    created_at = Column(String, nullable=False)
    expires_at = Column(String, default="")  # ISO datetime, "" = never
    max_uses = Column(Integer, default=1)
    use_count = Column(Integer, default=0)
    active = Column(Integer, default=1)  # 0 = revoked
    used_by = Column(String, default="")  # last username that redeemed it
