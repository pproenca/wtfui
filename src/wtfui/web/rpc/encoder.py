import base64
import dataclasses
import json
from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID


class WtfUIJSONEncoder(json.JSONEncoder):
    def default(self, o: Any) -> Any:
        match o:
            case datetime() | date() | time():
                return o.isoformat()
            case UUID():
                return str(o)
            case Decimal():
                return str(o)
            case Enum():
                return o.value
            case bytes():
                return base64.b64encode(o).decode("ascii")
            case set() | frozenset():
                return list(o)
            case _ if dataclasses.is_dataclass(o) and not isinstance(o, type):
                return self._encode_dataclass(o)
            case _:
                return super().default(o)

    def _encode_dataclass(self, obj: Any) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for field in dataclasses.fields(obj):
            value = getattr(obj, field.name)

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


def wtfui_json_dumps(obj: Any, **kwargs: Any) -> str:
    return json.dumps(obj, cls=WtfUIJSONEncoder, **kwargs)
