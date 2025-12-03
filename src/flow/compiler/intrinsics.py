"""Python Intrinsic Functions Registry.

Maps Python built-in functions to FlowByte intrinsic opcodes.
This allows standard Python functions like print(), len(), str() to work
in the browser without RPC calls.

The VM implements these intrinsics natively for optimal performance.
"""

from enum import IntEnum


class IntrinsicID(IntEnum):
    """Intrinsic function identifiers.

    These map to native implementations in the FlowByte VM.
    """

    PRINT = 0x01  # print(*args) -> None (console.log in JS)
    LEN = 0x02  # len(obj) -> int (obj.length in JS)
    STR = 0x03  # str(obj) -> str (String(obj) in JS)
    INT = 0x04  # int(obj) -> int (Math.floor(Number(obj)) in JS)
    RANGE = 0x05  # range(n) -> List[int] (Array.from({length: n}, (_, i) => i))


# Map Python builtin names to intrinsic IDs
INTRINSIC_MAP: dict[str, IntrinsicID] = {
    "print": IntrinsicID.PRINT,
    "len": IntrinsicID.LEN,
    "str": IntrinsicID.STR,
    "int": IntrinsicID.INT,
    "range": IntrinsicID.RANGE,
}


def get_intrinsic_id(name: str) -> IntrinsicID | None:
    """Get intrinsic ID for a Python builtin name.

    Args:
        name: Python builtin function name (e.g., "print", "len")

    Returns:
        IntrinsicID if the name is a supported intrinsic, None otherwise

    Example:
        >>> get_intrinsic_id("print")
        <IntrinsicID.PRINT: 1>
        >>> get_intrinsic_id("custom_func")
        None
    """
    return INTRINSIC_MAP.get(name)


def is_intrinsic(name: str) -> bool:
    """Check if a name is a supported intrinsic function.

    Args:
        name: Function name to check

    Returns:
        True if the name is a supported intrinsic

    Example:
        >>> is_intrinsic("print")
        True
        >>> is_intrinsic("my_function")
        False
    """
    return name in INTRINSIC_MAP
