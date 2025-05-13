import pytest
import os
import sqlite3
from datetime import datetime, timedelta
from mayer_monitor import (
    init_db, store_mayer_value, get_recent_mayer_values, analyze_mayer_multiple,
    check_sell_condition, get_notification_chats, get_db_connection
)

TEST_DB_PATH = 'test_mayer_monitor.db'

@pytest.fixture(autouse=True)
def setup_and_teardown_db(monkeypatch):
    # Patch DB_PATH to use a test database
    monkeypatch.setenv('DB_PATH', TEST_DB_PATH)
    # Remove test DB if exists
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
    init_db()
    yield
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)

def test_store_and_get_recent_mayer_values():s
    now = datetime.now()
    # Insert 7 days of values
    for i in range(7):
        store_mayer_value(now - timedelta(days=i), 2.5, 10000 + i, 9000 + i)
    values = get_recent_mayer_values(7)
    assert len(values) == 7
    assert all(v[0] == 2.5 for v in values)

def test_analyze_mayer_multiple_buy():
    msg, signal = analyze_mayer_multiple(0.9)
    assert 'BUY' in msg
    assert signal == 'BUY'

def test_analyze_mayer_multiple_sell(monkeypatch):
    # Insert 7 days of >2.4 values
    now = datetime.now()
    for i in range(7):
        store_mayer_value(now - timedelta(days=i), 2.5, 10000 + i, 9000 + i)
    msg, signal = analyze_mayer_multiple(2.5)
    assert 'SELL' in msg
    assert signal == 'SELL'

def test_analyze_mayer_multiple_hold():
    msg, signal = analyze_mayer_multiple(1.5)
    assert 'HOLD' in msg or '⏳' in msg
    assert signal == 'HOLD'

def test_check_sell_condition_true():
    now = datetime.now()
    for i in range(7):
        store_mayer_value(now - timedelta(days=i), 2.5, 10000 + i, 9000 + i)
    assert check_sell_condition() is True

def test_check_sell_condition_false():
    now = datetime.now()
    for i in range(6):
        store_mayer_value(now - timedelta(days=i), 2.5, 10000 + i, 9000 + i)
    store_mayer_value(now - timedelta(days=6), 2.0, 10000, 9000)
    assert check_sell_condition() is False

def test_get_notification_chats():
    with get_db_connection() as conn:
        db = conn.cursor()
        db.execute('INSERT INTO notifications (chat_id, enabled, last_notified) VALUES (?, ?, ?)', (123, 1, datetime.now()))
        db.execute('INSERT INTO notifications (chat_id, enabled, last_notified) VALUES (?, ?, ?)', (456, 0, datetime.now()))
        conn.commit()
    chats = get_notification_chats()
    assert 123 in chats
    assert 456 not in chats 