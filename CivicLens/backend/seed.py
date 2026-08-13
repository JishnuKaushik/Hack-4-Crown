"""Seed ~15-20 demo reports across Gurugram for the P5/P6 demo (PROJECT_SPEC.md §9).

Every report's category/severity/embedding comes from a REAL run of the AI
pipeline (analyze_image()) against real sample photos in ai/samples/ —
never hardcoded, per CLAUDE.md §0.5 ("no mocked AI outputs presented as
real"). Only the submission metadata (location, timestamp, status,
report_count) is synthetic, and that's explicitly what PROJECT_SPEC.md §9
asks P5 to pre-seed.

Idempotent: skips seeding if any reports already exist, unless --force.

Run from backend/, with the venv active:
    python seed.py [--force]
"""

import random
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import app  # noqa: F401  — triggers the ai/ sys.path bootstrap

from sqlalchemy import select

from app.config import settings
from app.database import Base, SessionLocal, engine
from app.models import Report, ReportEmbedding, User
from app.scoring import STATUSES, compute_priority_score
from ai.pipeline import analyze_image

SAMPLES_DIR = Path(__file__).resolve().parent.parent / "ai" / "samples"
SAMPLE_IMAGES = ["pothole.jpg", "garbage.jpg", "waterlogging.jpg", "pothole_dup.jpg"]


def _copy_samples_into_uploads() -> dict[str, str]:
    """Copies ai/samples/*.jpg into settings.upload_dir/seed/ so they're
    actually servable via the /uploads static mount (ai/samples/ isn't).
    Returns {sample_filename: relative_path_under_upload_dir}.
    """
    dest_dir = settings.upload_dir / "seed"
    dest_dir.mkdir(parents=True, exist_ok=True)
    mapping = {}
    for name in SAMPLE_IMAGES:
        src = SAMPLES_DIR / name
        dest = dest_dir / name
        if not dest.exists():
            shutil.copy(src, dest)
        mapping[name] = f"seed/{name}"
    return mapping

# Approximate real Gurugram-area coordinates, spread across sectors, per the
# example location already used in PROJECT_SPEC.md §6 (Sector 23A).
GURUGRAM_LOCATIONS = [
    (28.4595, 77.0266, "Sector 23A, Gurugram"),
    (28.4601, 77.0728, "Sector 29, Gurugram"),
    (28.4419, 77.0498, "Sector 14, Gurugram"),
    (28.4744, 77.0836, "DLF Phase 3, Gurugram"),
    (28.4089, 77.0546, "Sector 45, Gurugram"),
    (28.4954, 77.0876, "DLF Phase 1, Gurugram"),
    (28.4281, 77.0410, "Sector 12, Gurugram"),
    (28.3931, 76.9805, "Sohna Road, Gurugram"),
    (28.4636, 77.0296, "Old Gurugram, Sector 4"),
    (28.5127, 77.0932, "Sushant Lok, Gurugram"),
]


def get_seed_user(db) -> User:
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


def seed(force: bool = False) -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        existing = db.execute(select(Report.id).limit(1)).first()
        if existing and not force:
            print("Reports already exist — skipping seed. Pass --force to seed anyway.")
            return

        user = get_seed_user(db)
        random.seed(7)
        upload_relative_paths = _copy_samples_into_uploads()

        n = 18
        created = 0
        for i in range(n):
            image_name = SAMPLE_IMAGES[i % len(SAMPLE_IMAGES)]
            source_image_path = SAMPLES_DIR / image_name
            lat, lng, address = GURUGRAM_LOCATIONS[i % len(GURUGRAM_LOCATIONS)]
            # Small jitter so reports at the "same" location aren't pixel-identical
            lat += random.uniform(-0.002, 0.002)
            lng += random.uniform(-0.002, 0.002)

            analysis = analyze_image(str(source_image_path), lat, lng)

            age_days = random.uniform(0, 20)
            report_count = random.choice([1, 1, 1, 2, 3, 5])
            status = STATUSES[i % len(STATUSES)]
            created_at = datetime.now(timezone.utc) - timedelta(days=age_days)

            priority = compute_priority_score(
                severity=analysis.severity,
                category=analysis.category,
                report_count=report_count,
                age_days=age_days,
            )

            # Resolved reports get a plausible resolution time after creation
            # (not the same instant) so avg_resolution_hours isn't always 0.
            updated_at = created_at
            if status == "resolved":
                updated_at = created_at + timedelta(hours=random.uniform(2, 72))

            report = Report(
                user_id=user.id,
                image_path=upload_relative_paths[image_name],
                latitude=lat,
                longitude=lng,
                address=address,
                description=f"[SEED DATA] Demo report #{i + 1} for CivicLens presentation.",
                category=analysis.category,
                ai_confidence=analysis.confidence,
                severity=analysis.severity,
                status=status,
                priority_score=priority,
                report_count=report_count,
                created_at=created_at,
                updated_at=updated_at,
            )
            db.add(report)
            db.flush()

            db.add(
                ReportEmbedding(
                    report_id=report.id,
                    vector=analysis.embedding.tobytes(),
                    dim=analysis.embedding.shape[0],
                )
            )
            created += 1
            print(f"  [{created}/{n}] {analysis.category} (sev={analysis.severity}, "
                  f"priority={priority}, status={status}) @ {address}")

        db.commit()
        print(f"\nSeeded {created} demo reports.")
    finally:
        db.close()


if __name__ == "__main__":
    seed(force="--force" in sys.argv)
