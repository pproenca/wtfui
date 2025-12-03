// src/flow/static/reactivity.ts
/**
 * Micro-Signal Kernel for FlowByte VM.
 *
 * A minimal (~500 bytes gzipped) reactivity system that powers
 * the FlowByte Virtual Machine's reactive updates.
 */

// The currently executing effect (for dependency tracking)
let activeEffect: (() => void) | null = null;

export type Signal<T> = {
    value: T;
    subscribe: (fn: () => void) => () => void;
};

/**
 * Create a reactive signal.
 *
 * @param initialValue - The initial value of the signal
 * @returns A Signal object with getter/setter and subscription
 */
export function createSignal<T>(initialValue: T): Signal<T> {
    let _value = initialValue;
    const subscribers = new Set<() => void>();

    return {
        get value() {
            // Auto-track dependency if inside an effect
            if (activeEffect) {
                subscribers.add(activeEffect);
            }
            return _value;
        },
        set value(newValue: T) {
            if (_value !== newValue) {
                _value = newValue;
                // Notify all subscribers
                subscribers.forEach(fn => fn());
            }
        },
        subscribe(fn: () => void) {
            subscribers.add(fn);
            // Return unsubscribe function
            return () => subscribers.delete(fn);
        }
    };
}

/**
 * Create a reactive effect that auto-tracks dependencies.
 *
 * @param fn - The effect function to run
 */
export function createEffect(fn: () => void): void {
    activeEffect = fn;
    fn(); // Run once to capture dependencies
    activeEffect = null;
}

/**
 * Create a computed value that derives from signals.
 *
 * @param fn - The computation function
 * @returns A Signal-like object with a value getter
 */
export function computed<T>(fn: () => T): { readonly value: T } {
    let cachedValue: T;
    let isDirty = true;

    const signal = createSignal<T>(undefined as T);

    createEffect(() => {
        if (isDirty) {
            cachedValue = fn();
            isDirty = false;
        }
        signal.value = cachedValue;
    });

    return {
        get value() {
            return signal.value;
        }
    };
}
