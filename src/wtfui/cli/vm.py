from pathlib import Path


def get_vm_inline(use_bundled: bool = True) -> str:
    if use_bundled:
        bundled_path = Path(__file__).parent.parent / "static" / "dist" / "vm.min.js"
        if bundled_path.exists():
            return bundled_path.read_text()

    return """
class WtfUIVM {
    signals = new Map();
    nodes = new Map();
    strings = [];
    stack = [];  // Operand stack for stack-based execution
    callStack = [];  // Return address stack for CALL/RET
    view = null;
    root = null;

    async load(url) {
        const r = await fetch(url);
        const buf = await r.arrayBuffer();
        this.view = new DataView(buf);

        // Verify header
        if (String.fromCharCode(...new Uint8Array(buf, 0, 4)) !== 'MYFU') {
            throw new Error('Invalid WtfUIByte');
        }

        let off = 6;
        // Parse strings
        const cnt = this.view.getUint16(off, false); off += 2;
        const dec = new TextDecoder();
        for (let i = 0; i < cnt; i++) {
            const len = this.view.getUint16(off, false); off += 2;
            this.strings.push(dec.decode(new Uint8Array(buf, off, len)));
            off += len;
        }

        this.root = document.getElementById('root');
        this.execute(off);
    }

    execute(pc) {
        const v = this.view;
        let run = true;
        while (run && pc < v.byteLength) {
            const op = v.getUint8(pc++);
            switch (op) {
                // --- SIGNALS & STATE (0x00 - 0x1F) ---
                case 0x01: { // INIT_SIG_NUM
                    const id = v.getUint16(pc, false); pc += 2;
                    const val = v.getFloat64(pc, false); pc += 8;
                    this.signals.set(id, { value: val, subs: new Set() });
                    break;
                }
                case 0x02: { // INIT_SIG_STR
                    const id = v.getUint16(pc, false); pc += 2;
                    const strId = v.getUint16(pc, false); pc += 2;
                    this.signals.set(id, { value: this.strings[strId], subs: new Set() });
                    break;
                }
                case 0x03: { // SET_SIG_NUM
                    const id = v.getUint16(pc, false); pc += 2;
                    const val = v.getFloat64(pc, false); pc += 8;
                    const s = this.signals.get(id);
                    if (s) { s.value = val; s.subs.forEach(f => f()); }
                    break;
                }
                case 0x25: { // INC_CONST (legacy)
                    const id = v.getUint16(pc, false); pc += 2;
                    const amt = v.getFloat64(pc, false); pc += 8;
                    const s = this.signals.get(id);
                    if (s) { s.value += amt; s.subs.forEach(f => f()); }
                    break;
                }

                // --- STACK OPERATIONS (0xA0 - 0xBF) ---
                case 0xA0: { // PUSH_NUM
                    const val = v.getFloat64(pc, false); pc += 8;
                    this.stack.push(val);
                    break;
                }
                case 0xA1: { // PUSH_STR
                    const strId = v.getUint16(pc, false); pc += 2;
                    this.stack.push(this.strings[strId]);
                    break;
                }
                case 0xA2: { // LOAD_SIG (push signal value to stack)
                    const id = v.getUint16(pc, false); pc += 2;
                    const s = this.signals.get(id);
                    this.stack.push(s ? s.value : 0);
                    break;
                }
                case 0xA3: { // STORE_SIG (pop stack, store to signal)
                    const id = v.getUint16(pc, false); pc += 2;
                    const val = this.stack.pop();
                    const s = this.signals.get(id);
                    if (s) { s.value = val; s.subs.forEach(f => f()); }
                    break;
                }
                case 0xA4: { // POP (discard N values)
                    const cnt = v.getUint8(pc++);
                    for (let i = 0; i < cnt; i++) this.stack.pop();
                    break;
                }
                case 0xA5: { // DUP (duplicate top)
                    if (this.stack.length > 0) {
                        this.stack.push(this.stack[this.stack.length - 1]);
                    }
                    break;
                }

                // --- STACK-BASED ARITHMETIC (0x22 - 0x27) ---
                case 0x22: { // MUL: pop b, pop a, push a * b
                    const b = this.stack.pop();
                    const a = this.stack.pop();
                    this.stack.push(a * b);
                    break;
                }
                case 0x23: { // DIV: pop b, pop a, push a / b
                    const b = this.stack.pop();
                    const a = this.stack.pop();
                    this.stack.push(a / b);
                    break;
                }
                case 0x24: { // MOD: pop b, pop a, push a % b
                    const b = this.stack.pop();
                    const a = this.stack.pop();
                    this.stack.push(a % b);
                    break;
                }
                case 0x26: { // ADD_STACK: pop b, pop a, push a + b
                    const b = this.stack.pop();
                    const a = this.stack.pop();
                    this.stack.push(a + b);
                    break;
                }
                case 0x27: { // SUB_STACK: pop b, pop a, push a - b
                    const b = this.stack.pop();
                    const a = this.stack.pop();
                    this.stack.push(a - b);
                    break;
                }

                // --- COMPARISON OPERATORS (0x30 - 0x35) ---
                case 0x30: { // EQ: a == b
                    const b = this.stack.pop();
                    const a = this.stack.pop();
                    this.stack.push(a === b ? 1 : 0);
                    break;
                }
                case 0x31: { // NE: a != b
                    const b = this.stack.pop();
                    const a = this.stack.pop();
                    this.stack.push(a !== b ? 1 : 0);
                    break;
                }
                case 0x32: { // LT: a < b
                    const b = this.stack.pop();
                    const a = this.stack.pop();
                    this.stack.push(a < b ? 1 : 0);
                    break;
                }
                case 0x33: { // LE: a <= b
                    const b = this.stack.pop();
                    const a = this.stack.pop();
                    this.stack.push(a <= b ? 1 : 0);
                    break;
                }
                case 0x34: { // GT: a > b
                    const b = this.stack.pop();
                    const a = this.stack.pop();
                    this.stack.push(a > b ? 1 : 0);
                    break;
                }
                case 0x35: { // GE: a >= b
                    const b = this.stack.pop();
                    const a = this.stack.pop();
                    this.stack.push(a >= b ? 1 : 0);
                    break;
                }

                // --- INTRINSIC CALLS (0xC0) ---
                case 0xC0: { // CALL_INTRINSIC
                    const intrinsicId = v.getUint8(pc++);
                    const argc = v.getUint8(pc++);
                    const args = [];
                    for (let i = 0; i < argc; i++) {
                        args.unshift(this.stack.pop());  // Pop in reverse order
                    }
                    const result = this.callIntrinsic(intrinsicId, args);
                    if (result !== undefined) {
                        this.stack.push(result);
                    }
                    break;
                }
                case 0xC1: { // CALL - call user function
                    const funcAddr = v.getUint32(pc, false); pc += 4;
                    if (this.callStack.length >= 256) {
                        throw new Error('Stack overflow: max call depth (256) exceeded');
                    }
                    this.callStack.push(pc);  // Save return address
                    pc = funcAddr;
                    break;
                }
                case 0xC2: { // RET - return from function
                    if (this.callStack.length === 0) {
                        run = false;  // Graceful termination (event handler)
                    } else {
                        pc = this.callStack.pop();
                    }
                    break;
                }

                // --- CONTROL FLOW (0x40 - 0x5F) ---
                case 0x40: { // JMP_TRUE
                    const sigId = v.getUint16(pc, false); pc += 2;
                    const addr = v.getUint32(pc, false); pc += 4;
                    const s = this.signals.get(sigId);
                    if (s && s.value) pc = addr;
                    break;
                }
                case 0x41: { // JMP_FALSE
                    const sigId = v.getUint16(pc, false); pc += 2;
                    const addr = v.getUint32(pc, false); pc += 4;
                    const s = this.signals.get(sigId);
                    if (!s || !s.value) pc = addr;
                    break;
                }
                case 0x42: { // JMP
                    pc = v.getUint32(pc, false);
                    break;
                }

                // --- DOM MANIPULATION (0x60 - 0x8F) ---
                case 0x60: { // DOM_CREATE
                    const nid = v.getUint16(pc, false); pc += 2;
                    const tid = v.getUint16(pc, false); pc += 2;
                    this.nodes.set(nid, document.createElement(this.strings[tid]));
                    break;
                }
                case 0x61: { // DOM_APPEND
                    const pid = v.getUint16(pc, false); pc += 2;
                    const cid = v.getUint16(pc, false); pc += 2;
                    const c = this.nodes.get(cid);
                    if (c) (pid === 0 ? this.root : this.nodes.get(pid))?.appendChild(c);
                    break;
                }
                case 0x62: { // DOM_TEXT
                    const nid = v.getUint16(pc, false); pc += 2;
                    const sid = v.getUint16(pc, false); pc += 2;
                    const n = this.nodes.get(nid);
                    if (n) n.textContent = this.strings[sid];
                    break;
                }
                case 0x63: { // DOM_BIND_TEXT
                    const nid = v.getUint16(pc, false); pc += 2;
                    const sid = v.getUint16(pc, false); pc += 2;
                    const tid = v.getUint16(pc, false); pc += 2;
                    const n = this.nodes.get(nid);
                    const s = this.signals.get(sid);
                    const t = this.strings[tid];
                    if (n && s) {
                        const upd = () => n.textContent = t.replace('{}', s.value);
                        s.subs.add(upd);
                        upd();
                    }
                    break;
                }
                case 0x64: { // DOM_ON_CLICK
                    const nid = v.getUint16(pc, false); pc += 2;
                    const addr = v.getUint32(pc, false); pc += 4;
                    const n = this.nodes.get(nid);
                    if (n) n.addEventListener('click', () => this.execute(addr));
                    break;
                }
                case 0x65: { // DOM_ATTR_CLASS
                    const nid = v.getUint16(pc, false); pc += 2;
                    const sid = v.getUint16(pc, false); pc += 2;
                    const n = this.nodes.get(nid);
                    if (n) n.className = this.strings[sid];
                    break;
                }
                case 0x66: { // DOM_STYLE_STATIC
                    const nid = v.getUint16(pc, false); pc += 2;
                    const propId = v.getUint16(pc, false); pc += 2;
                    const valId = v.getUint16(pc, false); pc += 2;
                    const n = this.nodes.get(nid);
                    if (n) {
                        const prop = this.strings[propId];
                        const val = this.strings[valId];
                        // Convert kebab-case to camelCase for JS style API
                        const jsProp = prop.replace(/-([a-z])/g, (_, c) => c.toUpperCase());
                        n.style[jsProp] = val;
                    }
                    break;
                }
                case 0x67: { // DOM_STYLE_DYN
                    const nid = v.getUint16(pc, false); pc += 2;
                    const propId = v.getUint16(pc, false); pc += 2;
                    const val = this.stack.pop();
                    const n = this.nodes.get(nid);
                    if (n) {
                        const prop = this.strings[propId];
                        if (prop === 'cssText') {
                            // Apply full CSS text
                            n.style.cssText = String(val);
                        } else {
                            // Convert kebab-case to camelCase
                            const jsProp = prop.replace(/-([a-z])/g, (_, c) => c.toUpperCase());
                            n.style[jsProp] = String(val);
                        }
                    }
                    break;
                }
                case 0x68: { // DOM_ATTR
                    const nid = v.getUint16(pc, false); pc += 2;
                    const attrId = v.getUint16(pc, false); pc += 2;
                    const valId = v.getUint16(pc, false); pc += 2;
                    const n = this.nodes.get(nid);
                    if (n) n.setAttribute(this.strings[attrId], this.strings[valId]);
                    break;
                }
                case 0x69: { // DOM_BIND_ATTR
                    const nid = v.getUint16(pc, false); pc += 2;
                    const attrId = v.getUint16(pc, false); pc += 2;
                    const sigId = v.getUint16(pc, false); pc += 2;
                    const n = this.nodes.get(nid);
                    const s = this.signals.get(sigId);
                    const attr = this.strings[attrId];
                    if (n && s) {
                        const upd = () => n.setAttribute(attr, s.value);
                        s.subs.add(upd);
                        upd();
                    }
                    break;
                }
                case 0x70: { // DOM_IF
                    const sigId = v.getUint16(pc, false); pc += 2;
                    const trueAddr = v.getUint32(pc, false); pc += 4;
                    const falseAddr = v.getUint32(pc, false); pc += 4;
                    const s = this.signals.get(sigId);
                    if (s && s.value) {
                        pc = trueAddr;
                    } else {
                        pc = falseAddr;
                    }
                    break;
                }
                case 0x71: { // DOM_FOR
                    const listSigId = v.getUint16(pc, false); pc += 2;
                    const itemSigId = v.getUint16(pc, false); pc += 2;
                    const templateAddr = v.getUint32(pc, false); pc += 4;
                    const listSig = this.signals.get(listSigId);
                    if (listSig && Array.isArray(listSig.value)) {
                        for (const item of listSig.value) {
                            // Create or update item signal
                            this.signals.set(itemSigId, { value: item, subs: new Set() });
                            // Execute template block
                            this.execute(templateAddr);
                        }
                    }
                    break;
                }
                case 0x88: { // DOM_ROUTER
                    const routeCount = v.getUint8(pc++);
                    const routes = [];
                    for (let i = 0; i < routeCount; i++) {
                        const pathId = v.getUint16(pc, false); pc += 2;
                        const componentAddr = v.getUint32(pc, false); pc += 4;
                        routes.push({ path: this.strings[pathId], addr: componentAddr });
                    }
                    // Simple router: match window.location.pathname
                    const currentPath = window.location.pathname;
                    for (const route of routes) {
                        if (currentPath === '/' + route.path || currentPath === route.path) {
                            this.execute(route.addr);
                            break;
                        }
                    }
                    break;
                }

                case 0xFF: run = false; break;  // HALT
                default: console.error('Unknown op:', op.toString(16)); run = false;
            }
        }
    }

    callIntrinsic(id, args) {
        switch (id) {
            case 0x01: // PRINT
                console.log(...args);
                return undefined;
            case 0x02: // LEN
                return args[0]?.length ?? 0;
            case 0x03: // STR
                return String(args[0]);
            case 0x04: // INT
                return Math.floor(Number(args[0]));
            case 0x05: // RANGE
                return Array.from({length: args[0]}, (_, i) => i);
            default:
                console.error('Unknown intrinsic:', id);
                return undefined;
        }
    }
}
"""
