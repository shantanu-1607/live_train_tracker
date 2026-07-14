"""Hermetic unit tests for the Celery polling tasks.

No network, no real Redis, no real DB -- everything the tasks touch at the
edges (the async rail client, the sync redis connection, the DB session) is
mocked out.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from celery.exceptions import Retry, MaxRetriesExceededError

from app import tasks
from app.db.models import TrainTelemetry
from app.schemas.train import TrainResponse


def fake_train():
    return TrainResponse(
        number="12301",
        name="Howrah Rajdhani",
        type="Rajdhani",
        source="Howrah",
        destination="New Delhi",
        current_station="CNB",
        delay=15,
    )


def test_poll_single_train_writes_when_fresh():
    """Fresh idempotency key -> a telemetry row is added and committed, with the
    fields mapped correctly and a 90s TTL on the guard key."""
    mock_redis = MagicMock()
    mock_redis.set.return_value = True  # key did not exist -> fresh

    mock_session_local = MagicMock()
    session = mock_session_local.return_value.__enter__.return_value

    with patch.object(tasks.client, "get_live_status", new=AsyncMock(return_value=fake_train())), \
         patch.object(tasks, "redis_client", mock_redis), \
         patch.object(tasks, "SyncSessionLocal", mock_session_local):
        result = tasks.poll_single_train("12301")

    # guard was claimed with NX and a TTL
    mock_redis.set.assert_called_once()
    _, kwargs = mock_redis.set.call_args
    assert kwargs.get("nx") is True
    assert kwargs.get("ex") == 90

    # a telemetry row with the right fields was committed
    assert session.add.called
    assert session.commit.called
    added = session.add.call_args[0][0]
    assert isinstance(added, TrainTelemetry)
    assert added.train_number == "12301"
    assert added.station_code == "CNB"
    assert added.delay_minutes == 15

    assert result["status"] == "recorded"


def test_poll_single_train_skips_when_duplicate():
    """Existing idempotency key -> no DB write happens."""
    mock_redis = MagicMock()
    mock_redis.set.return_value = False  # key already existed -> duplicate

    mock_session_local = MagicMock()
    session = mock_session_local.return_value.__enter__.return_value

    with patch.object(tasks.client, "get_live_status", new=AsyncMock(return_value=fake_train())), \
         patch.object(tasks, "redis_client", mock_redis), \
         patch.object(tasks, "SyncSessionLocal", mock_session_local):
        result = tasks.poll_single_train("12301")

    assert not session.add.called
    assert not session.commit.called
    assert result["status"] == "duplicate"


def test_poll_single_train_retries_when_status_unavailable():
    """result is None -> the task raises Retry (schedules a backed-off retry)."""
    with patch.object(tasks.client, "get_live_status", new=AsyncMock(return_value=None)):
        with pytest.raises(Retry):
            tasks.poll_single_train("00000")


def test_poll_single_train_gives_up_after_max_retries():
    """When retries are exhausted, the None path returns 'gave_up' instead of
    crashing the worker."""
    with patch.object(tasks.client, "get_live_status", new=AsyncMock(return_value=None)), \
         patch.object(tasks.poll_single_train, "retry", side_effect=MaxRetriesExceededError()):
        result = tasks.poll_single_train("00000")

    assert result["status"] == "gave_up"


def test_poll_single_train_releases_guard_when_write_fails():
    """If the DB commit blows up, the idempotency key is released so a later
    attempt can still record the point, and the task retries.

    Note: invoked directly (not via .delay), Celery's self.retry(exc=...)
    re-raises the original exception rather than Retry; a real worker would
    raise Retry. Either way the guard key must be released first.
    """
    mock_redis = MagicMock()
    mock_redis.set.return_value = True  # fresh claim

    mock_session_local = MagicMock()
    session = mock_session_local.return_value.__enter__.return_value
    session.commit.side_effect = RuntimeError("db down")

    with patch.object(tasks.client, "get_live_status", new=AsyncMock(return_value=fake_train())), \
         patch.object(tasks, "redis_client", mock_redis), \
         patch.object(tasks, "SyncSessionLocal", mock_session_local):
        with pytest.raises(RuntimeError):
            tasks.poll_single_train("12301")

    mock_redis.delete.assert_called_once()  # claim was released before failing


def test_poll_all_trains_fans_out_once_per_active_train():
    """poll_all_trains dispatches one child task per active train."""
    mock_session_local = MagicMock()
    session = mock_session_local.return_value.__enter__.return_value
    session.scalars.return_value.all.return_value = ["12301", "12951"]

    with patch.object(tasks, "SyncSessionLocal", mock_session_local), \
         patch.object(tasks.poll_single_train, "delay") as mock_delay:
        result = tasks.poll_all_trains()

    assert mock_delay.call_count == 2
    mock_delay.assert_any_call("12301")
    mock_delay.assert_any_call("12951")
    assert result == {"dispatched": 2}
