// src/fuse/static/vm.ts
/**
 * MyFuseByte Virtual Machine - Browser runtime for .mfbc binaries.
 *
 * A lightweight (~3KB) VM that executes MyFuseByte bytecode directly
 * from an ArrayBuffer, achieving zero parse time.
 *
 * REVISED: Pure Stack Machine Architecture
 * - All arithmetic/comparison operations pop operands from stack, push result
 * - No register allocation needed
 * - Intrinsic functions use stack for arguments
 */

import { createSignal, createEffect, Signal } from './reactivity.js';

// OpCode Mapping (Must match Python opcodes.py)
const OPS = {
    // --- SIGNALS & STATE (0x00 - 0x1F) ---
    INIT_SIG_NUM: 0x01,
    INIT_SIG_STR: 0x02,
    SET_SIG_NUM:  0x03,

    // --- ARITHMETIC (0x20 - 0x2F) ---
    // Legacy register-based (kept for compatibility)
    ADD:          0x20,
    SUB:          0x21,
    MUL:          0x22,
    DIV:          0x23,
    MOD:          0x24,
    INC_CONST:    0x25,
    // Stack-based arithmetic
    ADD_STACK:    0x26,
    SUB_STACK:    0x27,

    // --- COMPARISON (0x30 - 0x3F) ---
    EQ:           0x30,
    NE:           0x31,
    LT:           0x32,
    LE:           0x33,
    GT:           0x34,
    GE:           0x35,

    // --- CONTROL FLOW (0x40 - 0x5F) ---
    JMP_TRUE:     0x40,
    JMP_FALSE:    0x41,
    JMP:          0x42,

    // --- DOM MANIPULATION (0x60 - 0x8F) ---
    DOM_CREATE:     0x60,
    DOM_APPEND:     0x61,
    DOM_TEXT:       0x62,
    DOM_BIND_TEXT:  0x63,
    DOM_ON_CLICK:   0x64,
    DOM_ATTR_CLASS: 0x65,
    DOM_STYLE_STATIC: 0x66,
    DOM_STYLE_DYN:  0x67,
    DOM_ATTR:       0x68,
    DOM_BIND_ATTR:  0x69,
    DOM_IF:         0x70,
    DOM_FOR:        0x71,
    DOM_ROUTER:     0x88,

    // --- NETWORK (0x90 - 0x9F) ---
    RPC_CALL:     0x90,

    // --- STACK OPERATIONS (0xA0 - 0xBF) ---
    PUSH_NUM:     0xA0,
    PUSH_STR:     0xA1,
    LOAD_SIG:     0xA2,
    STORE_SIG:    0xA3,
    POP:          0xA4,
    DUP:          0xA5,

    // --- INTRINSIC CALLS (0xC0 - 0xDF) ---
    CALL_INTRINSIC: 0xC0,
    // User function calls
    CALL: 0xC1,
    RET: 0xC2,

    // --- CONTROL ---
    HALT:         0xFF
} as const;

// Intrinsic function IDs (must match Python intrinsics.py)
const INTRINSICS: Record<number, (...args: any[]) => any> = {
    0x01: (...args) => console.log(...args),           // PRINT
    0x02: (arg) => arg?.length ?? 0,                   // LEN
    0x03: (arg) => String(arg),                        // STR
    0x04: (arg) => Math.floor(Number(arg)),            // INT
    0x05: (n) => Array.from({length: n}, (_, i) => i)  // RANGE
};

// Magic header "MYFU" + version
const MAGIC = [0x4D, 0x59, 0x46, 0x55]; // "MYFU"

/**
 * Convert kebab-case CSS property to camelCase for el.style access.
 */
function kebabToCamel(str: string): string {
    return str.replace(/-([a-z])/g, (_, c) => c.toUpperCase());
}

export class MyFuseVM {
    // Memory Banks
    signals = new Map<number, Signal<any>>();
    nodes = new Map<number, HTMLElement | Text>();
    strings: string[] = [];

    // === PURE STACK MACHINE ===
    stack: any[] = [];
    private callStack: number[] = [];

    // Program Code
    view: DataView | null = null;

    // Root element for mounting
    root: HTMLElement | null = null;

    /**
     * Load and execute a MyFuseByte binary from URL.
     */
    async load(url: string): Promise<void> {
        const response = await fetch(url);
        const buffer = await response.arrayBuffer();
        this.view = new DataView(buffer);

        // 1. Verify Magic Header
        for (let i = 0; i < 4; i++) {
            if (this.view.getUint8(i) !== MAGIC[i]) {
                throw new Error('Invalid MyFuseByte binary: bad magic header');
            }
        }

        // Skip header (6 bytes: MYFU + 2 version bytes)
        let offset = 6;

        // 2. Parse String Table
        offset = this.parseStringTable(offset);

        // 3. Get root element
        this.root = document.getElementById('root') || document.body;

        // 4. Execute Code Section
        this.execute(offset);
    }

    /**
     * Parse the string table section.
     * Format: [COUNT: u16] [LEN: u16, BYTES...]...
     */
    private parseStringTable(offset: number): number {
        const count = this.view!.getUint16(offset, false); // Big Endian
        offset += 2;

        const decoder = new TextDecoder();
        for (let i = 0; i < count; i++) {
            const len = this.view!.getUint16(offset, false);
            offset += 2;

            const bytes = new Uint8Array(this.view!.buffer, offset, len);
            this.strings.push(decoder.decode(bytes));
            offset += len;
        }

        return offset;
    }

    /**
     * The Main CPU Loop - Pure Stack Machine.
     * @param pc Program Counter (Byte Offset)
     */
    execute(pc: number): void {
        if (!this.view) return;
        const view = this.view;
        let running = true;

        while (running && pc < view.byteLength) {
            const op = view.getUint8(pc++);

            switch (op) {
                // === STACK OPERATIONS ===

                case OPS.PUSH_NUM: {
                    const val = view.getFloat64(pc, false); pc += 8;
                    this.stack.push(val);
                    break;
                }

                case OPS.PUSH_STR: {
                    const strId = view.getUint16(pc, false); pc += 2;
                    this.stack.push(this.strings[strId]);
                    break;
                }

                case OPS.LOAD_SIG: {
                    const sigId = view.getUint16(pc, false); pc += 2;
                    const signal = this.signals.get(sigId);
                    this.stack.push(signal ? signal.value : undefined);
                    break;
                }

                case OPS.STORE_SIG: {
                    const sigId = view.getUint16(pc, false); pc += 2;
                    const val = this.stack.pop();
                    const signal = this.signals.get(sigId);
                    if (signal) signal.value = val;
                    break;
                }

                case OPS.POP: {
                    const count = view.getUint8(pc++);
                    this.stack.splice(-count);
                    break;
                }

                case OPS.DUP: {
                    const top = this.stack[this.stack.length - 1];
                    this.stack.push(top);
                    break;
                }

                // === STACK-BASED ARITHMETIC ===

                case OPS.ADD_STACK: {
                    const b = this.stack.pop();
                    const a = this.stack.pop();
                    this.stack.push(a + b);
                    break;
                }

                case OPS.SUB_STACK: {
                    const b = this.stack.pop();
                    const a = this.stack.pop();
                    this.stack.push(a - b);
                    break;
                }

                case OPS.MUL: {
                    const b = this.stack.pop();
                    const a = this.stack.pop();
                    this.stack.push(a * b);
                    break;
                }

                case OPS.DIV: {
                    const b = this.stack.pop();
                    const a = this.stack.pop();
                    this.stack.push(a / b);
                    break;
                }

                case OPS.MOD: {
                    const b = this.stack.pop();
                    const a = this.stack.pop();
                    this.stack.push(a % b);
                    break;
                }

                // === COMPARISON OPERATIONS ===

                case OPS.EQ: {
                    const b = this.stack.pop();
                    const a = this.stack.pop();
                    this.stack.push(a === b);
                    break;
                }

                case OPS.NE: {
                    const b = this.stack.pop();
                    const a = this.stack.pop();
                    this.stack.push(a !== b);
                    break;
                }

                case OPS.LT: {
                    const b = this.stack.pop();
                    const a = this.stack.pop();
                    this.stack.push(a < b);
                    break;
                }

                case OPS.LE: {
                    const b = this.stack.pop();
                    const a = this.stack.pop();
                    this.stack.push(a <= b);
                    break;
                }

                case OPS.GT: {
                    const b = this.stack.pop();
                    const a = this.stack.pop();
                    this.stack.push(a > b);
                    break;
                }

                case OPS.GE: {
                    const b = this.stack.pop();
                    const a = this.stack.pop();
                    this.stack.push(a >= b);
                    break;
                }

                // === INTRINSIC CALLS ===

                case OPS.CALL_INTRINSIC: {
                    const intrinsicId = view.getUint8(pc++);
                    const argc = view.getUint8(pc++);
                    const args = this.stack.splice(-argc);

                    const fn = INTRINSICS[intrinsicId];
                    if (fn) {
                        const result = fn(...args);
                        // Push result if not undefined (print returns undefined)
                        if (result !== undefined) {
                            this.stack.push(result);
                        }
                    }
                    break;
                }

                case OPS.CALL: {
                    // CALL: Push return address, jump to function
                    const funcAddr = view.getUint32(pc, false); pc += 4;
                    if (this.callStack.length >= 256) {
                        throw new Error("Stack overflow: max call depth (256) exceeded");
                    }
                    this.callStack.push(pc);  // Push return address
                    pc = funcAddr;
                    break;
                }

                case OPS.RET: {
                    // RET: Pop return address, jump back (or halt if stack empty)
                    if (this.callStack.length === 0) {
                        return; // Graceful termination for event handlers
                    }
                    pc = this.callStack.pop()!;
                    break;
                }

                // === SIGNAL STATE (Legacy + Stack-compatible) ===

                case OPS.INIT_SIG_NUM: {
                    const id = view.getUint16(pc, false); pc += 2;
                    const val = view.getFloat64(pc, false); pc += 8;
                    this.signals.set(id, createSignal(val));
                    break;
                }

                case OPS.INIT_SIG_STR: {
                    const id = view.getUint16(pc, false); pc += 2;
                    const strId = view.getUint16(pc, false); pc += 2;
                    this.signals.set(id, createSignal(this.strings[strId]));
                    break;
                }

                case OPS.SET_SIG_NUM: {
                    const id = view.getUint16(pc, false); pc += 2;
                    const val = view.getFloat64(pc, false); pc += 8;
                    const signal = this.signals.get(id);
                    if (signal) signal.value = val;
                    break;
                }

                case OPS.INC_CONST: {
                    const tgtId = view.getUint16(pc, false); pc += 2;
                    const amount = view.getFloat64(pc, false); pc += 8;
                    const target = this.signals.get(tgtId);
                    if (target) target.value += amount;
                    break;
                }

                // === LEGACY REGISTER-BASED ARITHMETIC (for backwards compatibility) ===

                case OPS.ADD: {
                    const tgtId = view.getUint16(pc, false); pc += 2;
                    const srcA = view.getUint16(pc, false); pc += 2;
                    const srcB = view.getUint16(pc, false); pc += 2;

                    const sigA = this.signals.get(srcA);
                    const sigB = this.signals.get(srcB);
                    const target = this.signals.get(tgtId);

                    if (target && sigA && sigB) {
                        target.value = sigA.value + sigB.value;
                    }
                    break;
                }

                case OPS.SUB: {
                    const tgtId = view.getUint16(pc, false); pc += 2;
                    const srcA = view.getUint16(pc, false); pc += 2;
                    const srcB = view.getUint16(pc, false); pc += 2;

                    const sigA = this.signals.get(srcA);
                    const sigB = this.signals.get(srcB);
                    const target = this.signals.get(tgtId);

                    if (target && sigA && sigB) {
                        target.value = sigA.value - sigB.value;
                    }
                    break;
                }

                // === DOM MANIPULATION ===

                case OPS.DOM_CREATE: {
                    const nodeId = view.getUint16(pc, false); pc += 2;
                    const tagStrId = view.getUint16(pc, false); pc += 2;
                    const tagName = this.strings[tagStrId];

                    const el = document.createElement(tagName);
                    this.nodes.set(nodeId, el);
                    break;
                }

                case OPS.DOM_TEXT: {
                    const nodeId = view.getUint16(pc, false); pc += 2;
                    const strId = view.getUint16(pc, false); pc += 2;
                    const el = this.nodes.get(nodeId);
                    if (el) el.textContent = this.strings[strId];
                    break;
                }

                case OPS.DOM_APPEND: {
                    const parentId = view.getUint16(pc, false); pc += 2;
                    const childId = view.getUint16(pc, false); pc += 2;

                    const child = this.nodes.get(childId);
                    if (!child) break;

                    if (parentId === 0) {
                        // Append to root
                        this.root?.appendChild(child);
                    } else {
                        const parent = this.nodes.get(parentId);
                        parent?.appendChild(child);
                    }
                    break;
                }

                case OPS.DOM_ATTR_CLASS: {
                    const nodeId = view.getUint16(pc, false); pc += 2;
                    const strId = view.getUint16(pc, false); pc += 2;
                    const el = this.nodes.get(nodeId) as HTMLElement;
                    if (el) el.className = this.strings[strId];
                    break;
                }

                case OPS.DOM_STYLE_STATIC: {
                    const nodeId = view.getUint16(pc, false); pc += 2;
                    const propStrId = view.getUint16(pc, false); pc += 2;
                    const valStrId = view.getUint16(pc, false); pc += 2;

                    const el = this.nodes.get(nodeId) as HTMLElement;
                    if (el) {
                        const prop = kebabToCamel(this.strings[propStrId]);
                        const val = this.strings[valStrId];
                        (el.style as any)[prop] = val;
                    }
                    break;
                }

                case OPS.DOM_STYLE_DYN: {
                    const nodeId = view.getUint16(pc, false); pc += 2;
                    const propStrId = view.getUint16(pc, false); pc += 2;

                    const el = this.nodes.get(nodeId) as HTMLElement;
                    const val = this.stack.pop();

                    if (el) {
                        const prop = this.strings[propStrId];
                        if (prop === 'cssText') {
                            // Apply full cssText for dynamic styles
                            el.style.cssText = String(val);
                        } else {
                            // Apply single property
                            (el.style as any)[kebabToCamel(prop)] = String(val);
                        }
                    }
                    break;
                }

                case OPS.DOM_ATTR: {
                    const nodeId = view.getUint16(pc, false); pc += 2;
                    const attrStrId = view.getUint16(pc, false); pc += 2;
                    const valStrId = view.getUint16(pc, false); pc += 2;

                    const el = this.nodes.get(nodeId) as HTMLElement;
                    if (el) {
                        const attr = this.strings[attrStrId];
                        const val = this.strings[valStrId];
                        el.setAttribute(attr, val);
                    }
                    break;
                }

                case OPS.DOM_BIND_ATTR: {
                    const nodeId = view.getUint16(pc, false); pc += 2;
                    const attrStrId = view.getUint16(pc, false); pc += 2;
                    const sigId = view.getUint16(pc, false); pc += 2;

                    const el = this.nodes.get(nodeId) as HTMLElement;
                    const signal = this.signals.get(sigId);
                    const attr = this.strings[attrStrId];

                    if (el && signal) {
                        createEffect(() => {
                            el.setAttribute(attr, String(signal.value));
                        });
                    }
                    break;
                }

                // === REACTIVITY ===

                case OPS.DOM_BIND_TEXT: {
                    const nodeId = view.getUint16(pc, false); pc += 2;
                    const sigId = view.getUint16(pc, false); pc += 2;
                    const tmplId = view.getUint16(pc, false); pc += 2;

                    const el = this.nodes.get(nodeId);
                    const signal = this.signals.get(sigId);
                    const template = this.strings[tmplId];

                    if (el && signal) {
                        createEffect(() => {
                            el.textContent = template.replace('{}', String(signal.value));
                        });
                    }
                    break;
                }

                case OPS.DOM_ON_CLICK: {
                    const nodeId = view.getUint16(pc, false); pc += 2;
                    const jumpAddr = view.getUint32(pc, false); pc += 4;

                    const el = this.nodes.get(nodeId);
                    if (el) {
                        // Re-entrancy: click spawns new execution frame
                        el.addEventListener('click', () => {
                            this.execute(jumpAddr);
                        });
                    }
                    break;
                }

                // === REACTIVE CONTROL FLOW ===

                case OPS.DOM_IF: {
                    const sigId = view.getUint16(pc, false); pc += 2;
                    const trueAddr = view.getUint32(pc, false); pc += 4;
                    const falseAddr = view.getUint32(pc, false); pc += 4;

                    const signal = this.signals.get(sigId);

                    // Create placeholder for conditional content
                    const placeholder = document.createComment(`if:${sigId}`);
                    this.root?.appendChild(placeholder);

                    // Track nodes created by condition rendering
                    let conditionalNodes: Node[] = [];

                    // Render based on signal value
                    const renderCondition = () => {
                        // Remove previous conditional content
                        for (const node of conditionalNodes) {
                            node.parentNode?.removeChild(node);
                        }
                        conditionalNodes = [];

                        // Track nodes before execution
                        const nodesBefore = new Set(this.root?.childNodes || []);

                        // Execute appropriate block
                        const addr = signal?.value ? trueAddr : falseAddr;
                        this.execute(addr);

                        // Collect newly created nodes
                        this.root?.childNodes.forEach(node => {
                            if (!nodesBefore.has(node) && node !== placeholder) {
                                conditionalNodes.push(node);
                            }
                        });
                    };

                    // Set up reactive subscription
                    if (signal) {
                        createEffect(() => {
                            const _ = signal.value; // Track dependency
                            renderCondition();
                        });
                    } else {
                        renderCondition();
                    }
                    break;
                }

                case OPS.DOM_FOR: {
                    const listSigId = view.getUint16(pc, false); pc += 2;
                    const itemSigId = view.getUint16(pc, false); pc += 2;
                    const templateAddr = view.getUint32(pc, false); pc += 4;

                    const listSignal = this.signals.get(listSigId);

                    // Create placeholder for list content
                    const placeholder = document.createComment(`for:${listSigId}`);
                    this.root?.appendChild(placeholder);

                    // Create item signal (reused for each iteration)
                    const itemSignal = createSignal(null);
                    this.signals.set(itemSigId, itemSignal);

                    // Track nodes created by list rendering
                    let listNodes: Node[] = [];

                    const renderList = () => {
                        // Remove previous list content
                        for (const node of listNodes) {
                            node.parentNode?.removeChild(node);
                        }
                        listNodes = [];

                        // Render each item
                        const items = listSignal?.value ?? [];
                        for (const item of items) {
                            itemSignal.value = item;

                            // Track nodes before execution
                            const nodesBefore = new Set(this.root?.childNodes || []);

                            // Execute template for this item
                            this.execute(templateAddr);

                            // Collect newly created nodes
                            this.root?.childNodes.forEach(node => {
                                if (!nodesBefore.has(node) && node !== placeholder) {
                                    listNodes.push(node);
                                }
                            });
                        }
                    };

                    // Set up reactive subscription
                    if (listSignal) {
                        createEffect(() => {
                            const _ = listSignal.value; // Track dependency
                            renderList();
                        });
                    } else {
                        renderList();
                    }
                    break;
                }

                // === ROUTING ===

                case OPS.DOM_ROUTER: {
                    const routeCount = view.getUint8(pc++);
                    const routes: Array<{path: string, addr: number}> = [];

                    // Read all route definitions
                    for (let i = 0; i < routeCount; i++) {
                        const pathId = view.getUint16(pc, false); pc += 2;
                        const componentAddr = view.getUint32(pc, false); pc += 4;
                        routes.push({
                            path: this.strings[pathId],
                            addr: componentAddr
                        });
                    }

                    const container = this.root;
                    if (!container) break;

                    // Track nodes created by current route for cleanup
                    let currentRouteNodes: Node[] = [];

                    const handleRoute = () => {
                        const currentPath = window.location.pathname;

                        // Find matching route (exact match first, then fallback to first)
                        const match = routes.find(r => r.path === currentPath) || routes[0];

                        if (!match) return;

                        // Clear previous route content
                        for (const node of currentRouteNodes) {
                            node.parentNode?.removeChild(node);
                        }
                        currentRouteNodes = [];

                        // Track nodes created during this render
                        const nodesBefore = new Set(container.childNodes);

                        // Execute matched component
                        this.execute(match.addr);

                        // Collect newly created nodes
                        container.childNodes.forEach(node => {
                            if (!nodesBefore.has(node)) {
                                currentRouteNodes.push(node);
                            }
                        });
                    };

                    // Listen for navigation events
                    window.addEventListener('popstate', handleRoute);

                    // Handle programmatic navigation via custom event
                    window.addEventListener('fuse:navigate', ((e: CustomEvent) => {
                        const newPath = e.detail?.path;
                        if (newPath && newPath !== window.location.pathname) {
                            window.history.pushState({}, '', newPath);
                            handleRoute();
                        }
                    }) as EventListener);

                    // Initial render
                    handleRoute();
                    break;
                }

                // === CONTROL FLOW ===

                case OPS.JMP: {
                    const addr = view.getUint32(pc, false);
                    pc = addr;
                    break;
                }

                case OPS.JMP_TRUE: {
                    const sigId = view.getUint16(pc, false); pc += 2;
                    const addr = view.getUint32(pc, false); pc += 4;
                    const signal = this.signals.get(sigId);
                    if (signal?.value) {
                        pc = addr;
                    }
                    break;
                }

                case OPS.JMP_FALSE: {
                    const sigId = view.getUint16(pc, false); pc += 2;
                    const addr = view.getUint32(pc, false); pc += 4;
                    const signal = this.signals.get(sigId);
                    if (!signal?.value) {
                        pc = addr;
                    }
                    break;
                }

                // === NETWORK ===

                case OPS.RPC_CALL: {
                    const funcStrId = view.getUint16(pc, false); pc += 2;
                    const resultSigId = view.getUint16(pc, false); pc += 2;
                    const argc = view.getUint8(pc); pc += 1;

                    // Pop arguments from stack (right to left, so reverse for call order)
                    const args: unknown[] = [];
                    for (let i = 0; i < argc; i++) {
                        args.unshift(this.stack.pop());
                    }

                    const funcName = this.strings[funcStrId];
                    const resultSignal = this.signals.get(resultSigId);

                    // RPC call with arguments in body
                    fetch(`/api/rpc/${funcName}`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ args })
                    })
                        .then(r => r.json())
                        .then(data => {
                            if (resultSignal) resultSignal.value = data;
                        })
                        .catch(err => {
                            console.error(`RPC ${funcName} failed:`, err);
                        });
                    break;
                }

                case OPS.HALT:
                    running = false;
                    break;

                default:
                    console.error(`Unknown OpCode: 0x${op.toString(16)} at ${pc - 1}`);
                    running = false;
            }
        }
    }
}

// Auto-initialize if script is loaded directly
if (typeof window !== 'undefined') {
    (window as any).MyFuseVM = MyFuseVM;
}
