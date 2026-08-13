from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    image_url: str
    latitude: float
    longitude: float
    address: str | None
    description: str | None
    category: str
    ai_confidence: float
    severity: int
    status: str
    priority_score: float
    report_count: int
    is_duplicate_of: int | None
    created_at: datetime
    updated_at: datetime


class ReportCreateResponse(BaseModel):
    report: ReportOut
    duplicate_of: int | None = None


class StatusHistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    old_status: str | None
    new_status: str
    note: str | None
    created_at: datetime


class ReportDetailOut(ReportOut):
    duplicates: list[ReportOut] = Field(default_factory=list)
    status_history: list[StatusHistoryOut] = Field(default_factory=list)


class StatusUpdateRequest(BaseModel):
    status: str
    note: str | None = None
