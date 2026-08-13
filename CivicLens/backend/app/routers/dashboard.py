from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Report, as_utc

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

_HIGH_PRIORITY_THRESHOLD = 70


@router.get("/stats")
def get_stats(db: Session = Depends(get_db)) -> dict:
    canonical = select(Report).where(Report.is_duplicate_of.is_(None))

    total = db.scalar(select(func.count()).select_from(canonical.subquery())) or 0

    by_status: dict[str, int] = dict(
        db.execute(
            select(Report.status, func.count())
            .where(Report.is_duplicate_of.is_(None))
            .group_by(Report.status)
        ).all()
    )

    by_category: dict[str, int] = dict(
        db.execute(
            select(Report.category, func.count())
            .where(Report.is_duplicate_of.is_(None))
            .group_by(Report.category)
        ).all()
    )

    high_priority_count = db.scalar(
        select(func.count()).where(
            Report.is_duplicate_of.is_(None), Report.priority_score > _HIGH_PRIORITY_THRESHOLD
        )
    ) or 0

    resolved = db.execute(
        select(Report.created_at, Report.updated_at).where(
            Report.is_duplicate_of.is_(None), Report.status == "resolved"
        )
    ).all()
    if resolved:
        hours = [
            (as_utc(updated_at) - as_utc(created_at)).total_seconds() / 3600
            for created_at, updated_at in resolved
        ]
        avg_resolution_hours = round(sum(hours) / len(hours), 1)
    else:
        avg_resolution_hours = None

    return {
        "total": total,
        "by_status": by_status,
        "by_category": by_category,
        "avg_resolution_hours": avg_resolution_hours,
        "high_priority_count": high_priority_count,
    }
