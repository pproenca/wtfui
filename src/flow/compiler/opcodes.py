"""FlowByte Instruction Set Architecture.

Defines the opcodes for the Flow Virtual Machine. This is the contract
between the Python Compiler and the JavaScript VM.

Format: [OPCODE: u8] [ARGS...]
All multi-byte arguments are Big-Endian (!).

Opcode Ranges:
- 0x00-0x1F: Signals & State
- 0x20-0x3F: Arithmetic
- 0x40-0x5F: Control Flow
- 0x60-0x8F: DOM Manipulation
- 0x90-0xFE: Network (RPC)
- 0xFF: HALT
"""

from enum import IntEnum


class OpCode(IntEnum):
    """FlowByte Instruction Set."""

    # --- SIGNALS & STATE (0x00 - 0x1F) ---

    # Create a new signal with numeric value.
    # Args: [ID: u16] [INITIAL_VAL: f64]
    INIT_SIG_NUM = 0x01

    # Create a new signal with string value.
    # Args: [ID: u16] [STR_ID: u16]
    INIT_SIG_STR = 0x02

    # Update a signal value (numeric).
    # Args: [ID: u16] [NEW_VAL: f64]
    SET_SIG_NUM = 0x03

    # --- ARITHMETIC (0x20 - 0x3F) ---

    # Add two signals: target.value = source_a.value + source_b.value
    # Args: [TARGET: u16] [SRC_A: u16] [SRC_B: u16]
    ADD = 0x20

    # Subtract: target = a - b
    # Args: [TARGET: u16] [SRC_A: u16] [SRC_B: u16]
    SUB = 0x21

    # Increment signal by constant.
    # Args: [TARGET: u16] [AMOUNT: f64]
    INC_CONST = 0x25

    # --- CONTROL FLOW (0x40 - 0x5F) ---

    # Jump if Signal is Truthy.
    # Args: [SIG_ID: u16] [ADDR: u32]
    JMP_TRUE = 0x40

    # Jump if Signal is Falsy.
    # Args: [SIG_ID: u16] [ADDR: u32]
    JMP_FALSE = 0x41

    # Unconditional Jump.
    # Args: [ADDR: u32]
    JMP = 0x42

    # --- DOM MANIPULATION (0x60 - 0x8F) ---

    # Create DOM Element.
    # Args: [NODE_ID: u16] [TAG_STR_ID: u16]
    DOM_CREATE = 0x60

    # Append Child.
    # Args: [PARENT_ID: u16] [CHILD_ID: u16]
    DOM_APPEND = 0x61

    # Set Text Content (Static).
    # Args: [NODE_ID: u16] [STR_ID: u16]
    DOM_TEXT = 0x62

    # Bind Text Content to Signal (Reactive).
    # Args: [NODE_ID: u16] [SIG_ID: u16] [TEMPLATE_STR_ID: u16]
    # Template example: "Count: {}"
    DOM_BIND_TEXT = 0x63

    # Add Event Listener (Click).
    # Args: [NODE_ID: u16] [JMP_ADDR: u32]
    DOM_ON_CLICK = 0x64

    # Set Attribute (Class).
    # Args: [NODE_ID: u16] [STR_ID: u16]
    DOM_ATTR_CLASS = 0x65

    # --- NETWORK (0x90 - 0xFF) ---

    # Call Server RPC.
    # Args: [FUNC_STR_ID: u16] [RESULT_SIG_ID: u16]
    RPC_CALL = 0x90

    # End of Bytecode
    HALT = 0xFF
