from enum import IntEnum


class OpCode(IntEnum):
    INIT_SIG_NUM = 0x01

    INIT_SIG_STR = 0x02

    SET_SIG_NUM = 0x03

    ADD = 0x20

    SUB = 0x21

    INC_CONST = 0x25

    JMP_TRUE = 0x40

    JMP_FALSE = 0x41

    JMP = 0x42

    DOM_CREATE = 0x60

    DOM_APPEND = 0x61

    DOM_TEXT = 0x62

    DOM_BIND_TEXT = 0x63

    DOM_ON_CLICK = 0x64

    DOM_ATTR_CLASS = 0x65

    DOM_STYLE_STATIC = 0x66

    DOM_STYLE_DYN = 0x67

    DOM_ATTR = 0x68

    DOM_BIND_ATTR = 0x69

    DOM_IF = 0x70

    DOM_FOR = 0x71

    DOM_ROUTER = 0x88

    RPC_CALL = 0x90

    PUSH_NUM = 0xA0

    PUSH_STR = 0xA1

    LOAD_SIG = 0xA2

    STORE_SIG = 0xA3

    POP = 0xA4

    DUP = 0xA5

    ADD_STACK = 0x26

    SUB_STACK = 0x27

    MUL = 0x22

    DIV = 0x23

    MOD = 0x24

    EQ = 0x30

    NE = 0x31

    LT = 0x32

    LE = 0x33

    GT = 0x34

    GE = 0x35

    CALL_INTRINSIC = 0xC0

    CALL = 0xC1

    RET = 0xC2

    HALT = 0xFF
