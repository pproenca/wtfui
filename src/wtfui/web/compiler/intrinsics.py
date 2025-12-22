from enum import IntEnum


class IntrinsicID(IntEnum):
    PRINT = 0x01
    LEN = 0x02
    STR = 0x03
    INT = 0x04
    RANGE = 0x05


INTRINSIC_MAP: dict[str, IntrinsicID] = {
    "print": IntrinsicID.PRINT,
    "len": IntrinsicID.LEN,
    "str": IntrinsicID.STR,
    "int": IntrinsicID.INT,
    "range": IntrinsicID.RANGE,
}


def get_intrinsic_id(name: str) -> IntrinsicID | None:
    return INTRINSIC_MAP.get(name)


def is_intrinsic(name: str) -> bool:
    return name in INTRINSIC_MAP
