# src/flow/rpc/encoder.py
"""FlowJSONEncoder - Robust JSON encoder for RPC responses.

Automatically handles:
- datetime, date, time → ISO 8601 strings
- UUID → string representation
- dataclasses → dict (recursive)
- Enum → value
- Decimal → string (preserves precision)
- bytes → base64 string
- sets → lists
"""

from __future__ import annotations

import base64
import dataclasses
import json
from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID


class FlowJSONEncoder(json.JSONEncoder):
    """
    Enterprise-grade JSON encoder for Flow RPC.

    Developers don't need to manually convert objects to dicts.
    All common Python types are handled automatically.
    """

    def default(self, obj: Any) -> Any:
        # datetime types → ISO 8601
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, date):
            return obj.isoformat()
        if isinstance(obj, time):
            return obj.isoformat()

        # UUID → string
        if isinstance(obj, UUID):
            return str(obj)

        # Decimal → string (preserves precision)
        if isinstance(obj, Decimal):
            return str(obj)

        # Enum → value
        if isinstance(obj, Enum):
            return obj.value

        # dataclass → dict (recursive via asdict)
        if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
            return self._encode_dataclass(obj)

        # bytes → base64
        if isinstance(obj, bytes):
            return base64.b64encode(obj).decode("ascii")

        # set/frozenset → list
        if isinstance(obj, set | frozenset):
            return list(obj)

        # Fallback to default behavior
        return super().default(obj)

    def _encode_dataclass(self, obj: Any) -> dict[str, Any]:
        """Recursively encode a dataclass, handling nested complex types."""
        result: dict[str, Any] = {}
        for field in dataclasses.fields(obj):
            value = getattr(obj, field.name)
            # Recursively encode values (the encoder will handle nested types)
            if dataclasses.is_dataclass(value) and not isinstance(value, type):
                result[field.name] = self._encode_dataclass(value)
            elif isinstance(value, datetime | date | time | UUID | Decimal | Enum):
                result[field.name] = self.default(value)
            elif isinstance(value, list | tuple):
                result[field.name] = [
                    self._encode_dataclass(v)
                    if dataclasses.is_dataclass(v) and not isinstance(v, type)
                    else v
                    for v in value
                ]
            elif isinstance(value, dict):
                result[field.name] = {
                    k: self._encode_dataclass(v)
                    if dataclasses.is_dataclass(v) and not isinstance(v, type)
                    else v
                    for k, v in value.items()
                }
            else:
                result[field.name] = value
        return result


def flow_json_dumps(obj: Any, **kwargs: Any) -> str:
    """Convenience function for JSON serialization with FlowJSONEncoder."""
    return json.dumps(obj, cls=FlowJSONEncoder, **kwargs)
