This document serves as the **Constitution of the Flow Framework**. It was ratified following the rigorous architectural audit of the `2025-12-02` Implementation Plan.

These principles are non-negotiable. They serve as the "North Star" for all future architectural decisions, ensuring Flow remains a **world-class, industry-shifting runtime** rather than a derivative wrapper.

---

# The Flow Manifesto: Principles of the Universal Python Runtime

## Preamble
We reject the notion that Python is solely a backend language. We reject the necessity of the "JavaScript Tax" for interactive UIs. We believe that by leveraging the cutting edge of the Python interpreter (3.14+), we can create a unified, high-performance, and elegant development experience that rivals any ecosystem in existence.

---

## Tenet I: Indentation is Topology
**"The code shape must match the UI shape."**

In HTML/JSX, the hierarchy is defined by closing tags `</div>`. In Python, hierarchy is defined by whitespace. Flow embraces this fundamental truth of the language.

* **The Rule:** We do not use function nesting `Div(Text())` for hierarchy. We use **Context Managers** (`with Div():`).
* **The Why:** This aligns the visual structure of the code with the visual structure of the DOM. It eliminates "bracket hell" and enforces clean, readable component trees.
* **The Constraint:** Any UI element capable of containing children *must* be implemented as a Context Manager.



---

## Tenet II: The Principle of Universal Isomorphism
**"Define Once, Render Anywhere."**

A component defined in Flow is not HTML. It is not a DOM node. It is an abstract instruction. The framework must strictly decouple the *definition* of UI from the *execution* of UI.

* **The Rule:** No `Element` shall ever know how to render itself. It must only know how to describe itself to a `Renderer`.
* **The Architecture:** We adhere strictly to the **Bridge Pattern**.
    * **Server (SSR):** `HTMLRenderer` converts abstract nodes to strings.
    * **Client (Wasm):** `DOMRenderer` converts abstract nodes to `js.document` calls.
* **The Constraint:** Hard-coding HTML strings or DOM API calls inside a Component is strictly forbidden.



---

## Tenet III: Zero-Friction Development (The "Ghost Build")
**"If I have to install Node.js to write Python, we have failed."**

We acknowledge that a build step is necessary for production, but we reject it for development. The Developer Experience (DX) must be instantaneous.

* **The Rule:** `python app.py` must be the only command required to start a full-stack dev environment.
* **The Mechanism:** We use **Import Hooks** (`sys.meta_path`) to intercept, transpile, and serve client code in-memory on the fly.
* **The Constraint:** There shall be no physical `dist/` or `node_modules/` folders generated during the development lifecycle. The build system must be invisible.



---

## Tenet IV: Native Leverage (3.14 or Death)
**"We do not polyfill; we leverage the runtime."**

Flow is built for the future of Python, not the past. We aggressively utilize the architectural breakthroughs of Python 3.14.

* **The Rule:** We do not fight the interpreter; we ride it.
* **The Implementation:**
    * **No-GIL:** We use `threading.Lock` and `ThreadPoolExecutor` for parallel DOM-diffing, ensuring thread safety without the performance penalty of `multiprocessing`.
    * **PEP 649:** We use `annotationlib` for lazy dependency injection, solving the circular import crisis of large applications.
    * **Tail-Call Optimization:** We write recursive rendering logic confident that the 3.14 interpreter will optimize it.

---

## Tenet V: Atomic Reactivity
**"State changes are precise surgeries, not full-body transplants."**

We reject the "Virtual DOM Diffing" of the entire tree for every state change. It is inefficient.

* **The Rule:** Reactivity is fine-grained. A `Signal` update must identify the exact `RenderNode` that depends on it and update *only* that node.
* **The Architecture:** We use the Observer Pattern via `Signal` and `Effect`.
* **The Constraint:** We do not use `setState`. State is mutable (`state.count.value += 1`). The framework is responsible for detecting the mutation, not the developer.

---

## Tenet VI: The Security Firewall (AST Separation)
**"The Client is a privilege-reduced environment."**

We acknowledge that the Client and Server share code, but they do not share secrets.

* **The Rule:** Code intended for the Server (DB connections, API keys) must physically cease to exist in the Client bundle.
* **The Mechanism:** We use **AST Transformation** to strip sensitive logic.
    * **Server Context:** `@rpc` function body is kept intact.
    * **Client Context:** `@rpc` function body is replaced with a `fetch()` stub.
* **The Constraint:** The framework must fail to compile if it detects server-side libraries (like `sqlalchemy` or `os`) leaking into the Client scope.

---

## Tenet VII: Ecosystem Bridges, Not Walls
**"We stand on the shoulders of giants (even if they are JavaScript)."**

We do not attempt to rewrite the entire history of UI libraries (Maps, Charts, Grids) in Python.

* **The Rule:** Flow must be able to consume standard Web Components and React libraries dynamically.
* **The Mechanism:** We support **ES Module Dynamic Imports**. A Python wrapper can point to a CDN URL (`esm.sh/react-map-gl`) and hydration must happen automatically.
* **The Constraint:** No `npm install`. Dependencies are URLs, resolved by the browser.
