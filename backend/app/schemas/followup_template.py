from pydantic import BaseModel, Field


class FollowupTemplateCreate(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=2000)
    category: str = Field(default="general", max_length=20)
    default_due_days: int = Field(default=7, ge=0, le=365)


class FollowupTemplateUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    category: str | None = Field(default=None, max_length=20)
    default_due_days: int | None = Field(default=None, ge=0, le=365)


class FollowupTemplateResponse(BaseModel):
    id: int
    psychologist_username: str
    title: str
    description: str
    category: str
    default_due_days: int
    times_used: int
    created_at: str

    class Config:
        from_attributes = True


class AssignFromTemplateRequest(BaseModel):
    patient_username: str
    due_date: str = ""
