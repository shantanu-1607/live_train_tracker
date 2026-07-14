"""Idempotent seed for the tracked_trains table.

Run:  venv/bin/python -m scripts.seed_tracked_trains
Safe to run repeatedly -- trains that already exist are skipped.
"""
from sqlalchemy import select

from app.db.sync_database import sync_engine, SyncSessionLocal
from app.db.models import Base, TrackedTrain

# a few real Indian trains to start tracking.
SEED_TRAINS = ["12301", "12951", "12259"]


def seed():
    # make sure tables exist so a fresh DB works out of the box.
    Base.metadata.create_all(sync_engine)

    inserted, skipped = [], []
    with SyncSessionLocal() as session:
        existing = set(session.scalars(select(TrackedTrain.train_number)).all())

        for train_no in SEED_TRAINS:
            if train_no in existing:
                skipped.append(train_no)
                continue
            session.add(TrackedTrain(train_number=train_no, is_active=True))
            inserted.append(train_no)

        session.commit()

    print(f"inserted: {inserted or 'none'}")
    print(f"skipped (already present): {skipped or 'none'}")


if __name__ == "__main__":
    seed()
