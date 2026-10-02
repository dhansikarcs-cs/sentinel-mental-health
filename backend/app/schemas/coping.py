from pydantic import BaseModel, Field


class CopingToolCreate(BaseModel):
    title: str = Field(min_length=1, max_length=80)
    description: str = Field(default="", max_length=500)
    category: str = Field(default="calming", max_length=20)


class CopingToolUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=500)
    category: str | None = Field(default=None, max_length=20)
    sort_order: int | None = None


class CopingToolResponse(BaseModel):
    id: int
    patient_username: str
    title: str
    description: str
    category: str
    sort_order: int
    recommended_by: str = ""
    created_at: str

    class Config:
        from_attributes = True


class CopingToolRecommend(BaseModel):
    """Clinician recommending a coping tool for an assigned patient."""

    patient_username: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=80)
    description: str = Field(default="", max_length=500)
    category: str = Field(default="calming", max_length=20)
