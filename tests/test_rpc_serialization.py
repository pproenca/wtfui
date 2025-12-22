# tests/test_rpc_serialization.py
"""Tests for WtfUIJSONEncoder - robust RPC serialization."""

import json
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID, uuid4

from wtfui.web.rpc.encoder import WtfUIJSONEncoder


class Status(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


@dataclass
class User:
    id: UUID
    name: str
    created_at: datetime


def test_encoder_handles_datetime():
    """Encoder serializes datetime to ISO format."""
    dt = datetime(2025, 12, 2, 14, 30, 0)
    result = json.dumps({"timestamp": dt}, cls=WtfUIJSONEncoder)
    assert "2025-12-02T14:30:00" in result


def test_encoder_handles_date():
    """Encoder serializes date to ISO format."""
    d = date(2025, 12, 2)
    result = json.dumps({"date": d}, cls=WtfUIJSONEncoder)
    assert "2025-12-02" in result


def test_encoder_handles_uuid():
    """Encoder serializes UUID to string."""
    uid = UUID("12345678-1234-5678-1234-567812345678")
    result = json.dumps({"id": uid}, cls=WtfUIJSONEncoder)
    assert "12345678-1234-5678-1234-567812345678" in result


def test_encoder_handles_dataclass():
    """Encoder serializes dataclasses to dicts."""
    user = User(
        id=UUID("12345678-1234-5678-1234-567812345678"),
        name="Alice",
        created_at=datetime(2025, 12, 2, 14, 30, 0),
    )
    result = json.dumps(user, cls=WtfUIJSONEncoder)
    parsed = json.loads(result)

    assert parsed["name"] == "Alice"
    assert "12345678-1234-5678-1234-567812345678" in parsed["id"]
    assert "2025-12-02" in parsed["created_at"]


def test_encoder_handles_enum():
    """Encoder serializes Enum to its value."""
    result = json.dumps({"status": Status.ACTIVE}, cls=WtfUIJSONEncoder)
    assert "active" in result


def test_encoder_handles_decimal():
    """Encoder serializes Decimal to string (preserves precision)."""
    result = json.dumps({"price": Decimal("19.99")}, cls=WtfUIJSONEncoder)
    assert "19.99" in result


def test_encoder_handles_nested_dataclass():
    """Encoder handles dataclasses with nested complex types."""

    @dataclass
    class Order:
        id: UUID
        user: User
        total: Decimal

    order = Order(
        id=uuid4(),
        user=User(id=uuid4(), name="Bob", created_at=datetime.now()),
        total=Decimal("99.99"),
    )

    result = json.dumps(order, cls=WtfUIJSONEncoder)
    parsed = json.loads(result)

    assert parsed["user"]["name"] == "Bob"
    assert "99.99" in parsed["total"]
