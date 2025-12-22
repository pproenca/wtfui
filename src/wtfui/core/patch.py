"""Patch types for granular DOM updates.

These patches represent the minimal operations needed to update
the DOM from one state to another, following React's approach
of updating properties in-place rather than replacing elements.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from wtfui.core.vnode import VNode


@dataclass(slots=True)
class Patch:
    """Base class for all patch operations."""

    op: str


@dataclass(slots=True)
class UpdatePropPatch(Patch):
    """Update a single property on an element.

    This is the most common patch type - updates value, class, style, etc.
    without replacing the element, preserving focus and scroll position.
    """

    op: str = "update_prop"
    target_key: str = ""
    prop_name: str = ""
    value: Any = None


@dataclass(slots=True)
class CreatePatch(Patch):
    """Insert a new element into the DOM.

    Used when a new child is added to the tree.
    """

    op: str = "create"
    vnode: VNode | None = None
    parent_key: str = ""
    index: int = 0


@dataclass(slots=True)
class DeletePatch(Patch):
    """Remove an element from the DOM.

    Used when a child is removed from the tree.
    """

    op: str = "delete"
    target_key: str = ""


@dataclass(slots=True)
class ReplacePatch(Patch):
    """Replace an element entirely.

    Only used when key or tag changes - element identity is different.
    This is the expensive operation we try to minimize.
    """

    op: str = "replace"
    old_vnode: VNode | None = None
    new_vnode: VNode | None = None


@dataclass(slots=True)
class MovePatch(Patch):
    """Move an element to a new position.

    Used when children are reordered but not added/removed.
    """

    op: str = "move"
    target_key: str = ""
    new_index: int = 0
