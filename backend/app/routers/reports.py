import numpy as np
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Report, ReportEmbedding, User
from app.schemas import ReportCreateResponse, ReportOut
from app.scoring import CATEGORIES, compute_priority_score
from app.storage import save_report_image

router = APIRouter(prefix="/reports", tags=["reports"])

# STUB: AI pipeline is not wired yet (arrives in P2, see ai/pipeline.py).
# Every submission gets this fixed classification so the vertical slice
# (submit -> store -> list) can be verified end to end.
_STUB_CATEGORY = "pothole"
_STUB_CONFIDENCE = 0.5
_STUB_SEVERITY = 3
_STUB_EMBEDDING_DIM = 512


def _get_demo_user(db: Session) -> User:
    """P1 has no auth yet (arrives in P4 per PROJECT_SPEC milestones).

    All submissions are attributed to a single seeded demo citizen so the
    NOT NULL reports.user_id FK is satisfiable. Replaced by the real
    authenticated user once auth lands.
    """
    user = db.execute(select(User).where(User.email == "demo@civiclens.local")).scalar_one_or_none()
    if user is None:
        user = User(
            name="Demo Citizen",
            email="demo@civiclens.local",
            password_hash="unusable-stub-hash",
            role="citizen",
        )
        db.add(user)
        db.flush()
    return user


def _to_report_out(report: Report) -> ReportOut:
    return ReportOut(
        id=report.id,
        image_url=f"/uploads/{report.image_path}",
        latitude=report.latitude,
        longitude=report.longitude,
        address=report.address,
        description=report.description,
        category=report.category,
        ai_confidence=report.ai_confidence,
        severity=report.severity,
        status=report.status,
        priority_score=report.priority_score,
        report_count=report.report_count,
        is_duplicate_of=report.is_duplicate_of,
        created_at=report.created_at,
        updated_at=report.updated_at,
    )


@router.post("", response_model=ReportCreateResponse, status_code=201)
async def create_report(
    image: UploadFile = File(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    description: str | None = Form(None),
    address: str | None = Form(None),
    db: Session = Depends(get_db),
) -> ReportCreateResponse:
    if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
        raise HTTPException(status_code=422, detail="Invalid latitude/longitude")

    image_path = await save_report_image(image)
    user = _get_demo_user(db)

    priority = compute_priority_score(
        severity=_STUB_SEVERITY, category=_STUB_CATEGORY, report_count=1, age_days=0
    )

    report = Report(
        user_id=user.id,
        image_path=image_path,
        latitude=latitude,
        longitude=longitude,
        address=address,
        description=description,
        category=_STUB_CATEGORY,
        ai_confidence=_STUB_CONFIDENCE,
        severity=_STUB_SEVERITY,
        priority_score=priority,
        report_count=1,
    )
    db.add(report)
    db.flush()

    zero_vector = np.zeros(_STUB_EMBEDDING_DIM, dtype=np.float32)
    db.add(ReportEmbedding(report_id=report.id, vector=zero_vector.tobytes(), dim=_STUB_EMBEDDING_DIM))

    db.commit()
    db.refresh(report)

    return ReportCreateResponse(report=_to_report_out(report), duplicate_of=None)


@router.get("", response_model=list[ReportOut])
def list_reports(
    status: str | None = Query(None),
    category: str | None = Query(None),
    min_priority: float | None = Query(None),
    sort: str = Query("priority", pattern="^(priority|recent)$"),
    bbox: str | None = Query(None, description="minLat,minLng,maxLat,maxLng"),
    include_duplicates: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> list[ReportOut]:
    if category is not None and category not in CATEGORIES:
        raise HTTPException(status_code=422, detail=f"Unknown category: {category}")

    stmt = select(Report)

    if not include_duplicates:
        stmt = stmt.where(Report.is_duplicate_of.is_(None))
    if status is not None:
        stmt = stmt.where(Report.status == status)
    if category is not None:
        stmt = stmt.where(Report.category == category)
    if min_priority is not None:
        stmt = stmt.where(Report.priority_score >= min_priority)
    if bbox is not None:
        try:
            min_lat, min_lng, max_lat, max_lng = (float(x) for x in bbox.split(","))
        except ValueError:
            raise HTTPException(status_code=422, detail="bbox must be minLat,minLng,maxLat,maxLng") from None
        stmt = stmt.where(
            Report.latitude >= min_lat,
            Report.latitude <= max_lat,
            Report.longitude >= min_lng,
            Report.longitude <= max_lng,
        )

    if sort == "priority":
        stmt = stmt.order_by(Report.priority_score.desc())
    else:
        stmt = stmt.order_by(Report.created_at.desc())

    stmt = stmt.limit(limit).offset(offset)

    reports = db.execute(stmt).scalars().all()
    return [_to_report_out(r) for r in reports]
