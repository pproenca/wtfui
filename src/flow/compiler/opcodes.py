"""FlowByte Instruction Set Architecture.

Defines the opcodes for the Flow Virtual Machine. This is the contract
between the Python Compiler and the JavaScript VM.

Format: [OPCODE: u8] [ARGS...]
All multi-byte arguments are Big-Endian (!).

Opcode Ranges:
- 0x00-0x1F: Signals & State
- 0x20-0x3F: Arithmetic (Stack-Based)
- 0x40-0x5F: Control Flow
- 0x60-0x8F: DOM Manipulation
- 0x90-0xBF: Network (RPC)
- 0xA0-0xBF: Stack Operations
- 0xC0-0xDF: Intrinsic Calls
- 0xFF: HALT

Note: This opcode set includes both register-based (legacy) and stack-based opcodes.
Stack-based opcodes are preferred for new code and will eventually replace register-based ones.
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

    # Set Inline Style (Static) - compile-time extracted styles.
    # Args: [NODE_ID: u16] [PROP_STR_ID: u16] [VALUE_STR_ID: u16]
    # Example: DOM_STYLE_STATIC(node, "background", "blue")
    DOM_STYLE_STATIC = 0x66

    # Set Inline Style (Dynamic) - runtime evaluated styles.
    # Pops value from stack, applies as style property.
    # Args: [NODE_ID: u16] [PROP_STR_ID: u16]
    # Stack: [value] -> []
    # Fallback when static extraction fails (e.g., f-string styles).
    DOM_STYLE_DYN = 0x67

    # Set Generic Attribute.
    # Args: [NODE_ID: u16] [ATTR_STR_ID: u16] [VALUE_STR_ID: u16]
    DOM_ATTR = 0x68

    # Bind Attribute to Signal (Reactive).
    # Args: [NODE_ID: u16] [ATTR_STR_ID: u16] [SIG_ID: u16]
    DOM_BIND_ATTR = 0x69

    # --- NETWORK (0x90 - 0x9F) ---

    # Call Server RPC.
    # Args: [FUNC_STR_ID: u16] [RESULT_SIG_ID: u16]
    RPC_CALL = 0x90

    # --- STACK OPERATIONS (0xA0 - 0xBF) ---

    # Push numeric constant to stack.
    # Args: [VALUE: f64]
    PUSH_NUM = 0xA0

    # Push string constant to stack.
    # Args: [STR_ID: u16]
    PUSH_STR = 0xA1

    # Load signal VALUE to stack (dereference).
    # Args: [SIG_ID: u16]
    LOAD_SIG = 0xA2

    # Pop stack, store to signal.
    # Args: [SIG_ID: u16]
    STORE_SIG = 0xA3

    # Pop N values from stack (discard).
    # Args: [COUNT: u8]
    POP = 0xA4

    # Duplicate top of stack.
    # Args: None
    DUP = 0xA5

    # --- STACK-BASED ARITHMETIC (0x20 - 0x2F) ---
    # Note: These redefine existing opcodes to use stack semantics.
    # Legacy register-based arithmetic uses 0x20-0x24 range.
    # Stack-based: Pop 2 operands, push result.

    # ADD (stack-based): Pop b, pop a, push (a + b)
    # Args: None (operands from stack)
    ADD_STACK = 0x26

    # SUB (stack-based): Pop b, pop a, push (a - b)
    # Args: None
    SUB_STACK = 0x27

    # MUL (stack-based): Pop b, pop a, push (a * b)
    # Args: None
    MUL = 0x22

    # DIV (stack-based): Pop b, pop a, push (a / b)
    # Args: None
    DIV = 0x23

    # MOD (stack-based): Pop b, pop a, push (a % b)
    # Args: None
    MOD = 0x24

    # --- STACK-BASED COMPARISON (0x30 - 0x3F) ---

    # EQ (stack-based): Pop b, pop a, push (a == b)
    # Args: None
    EQ = 0x30

    # NE (stack-based): Pop b, pop a, push (a != b)
    # Args: None
    NE = 0x31

    # LT (stack-based): Pop b, pop a, push (a < b)
    # Args: None
    LT = 0x32

    # LE (stack-based): Pop b, pop a, push (a <= b)
    # Args: None
    LE = 0x33

    # GT (stack-based): Pop b, pop a, push (a > b)
    # Args: None
    GT = 0x34

    # GE (stack-based): Pop b, pop a, push (a >= b)
    # Args: None
    GE = 0x35

    # --- INTRINSIC CALLS (0xC0 - 0xDF) ---

    # Call builtin function (print, len, str, etc.).
    # Pops ARGC arguments from stack, pushes result (if any).
    # Args: [INTRINSIC_ID: u8] [ARGC: u8]
    CALL_INTRINSIC = 0xC0

    # --- CONTROL ---

    # End of Bytecode
    HALT = 0xFF
