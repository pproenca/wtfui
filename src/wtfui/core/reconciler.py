"""React-style reconciliation algorithm.

Implements the diffing algorithm that compares old and new VNode trees
and produces minimal patches to update the DOM.

Key principles (from React 19):
1. Slot-by-slot matching first (position N old vs position N new)
2. Map-based lookup for remaining children by key
3. Never replace element if key/tag matches - only update props
"""

from typing import TYPE_CHECKING

from wtfui.core.patch import (
    CreatePatch,
    DeletePatch,
    MovePatch,
    Patch,
    ReplacePatch,
    UpdatePropPatch,
)

if TYPE_CHECKING:
    from wtfui.core.vnode import VNode


def reconcile(old: VNode | None, new: VNode | None) -> list[Patch]:
    """Reconcile two VNode trees and produce patches.

    Args:
        old: Previous VNode tree (None if creating).
        new: New VNode tree (None if deleting).

    Returns:
        List of patches to transform old into new.
    """
    patches: list[Patch] = []

    # Case 1: Creating from nothing
    if old is None and new is not None:
        patches.append(CreatePatch(vnode=new, parent_key="", index=0))
        return patches

    # Case 2: Deleting existing
    if old is not None and new is None:
        patches.append(DeletePatch(target_key=old.key))
        return patches

    # Case 3: Both exist - compare them
    if old is not None and new is not None:
        # Different key or tag means completely different element
        if old.key != new.key or old.tag != new.tag:
            patches.append(ReplacePatch(old_vnode=old, new_vnode=new))
            return patches

        # Same identity - diff props
        patches.extend(_diff_props(old, new))

        # Diff children
        patches.extend(_reconcile_children(old, new))

    return patches


def _diff_props(old: VNode, new: VNode) -> list[Patch]:
    """Compare props and produce UpdatePropPatch for changes.

    Args:
        old: Previous VNode.
        new: New VNode.

    Returns:
        List of UpdatePropPatch for changed properties.
    """
    patches: list[Patch] = []

    # Check for changed or new props
    for prop_name, new_value in new.props.items():
        old_value = old.props.get(prop_name)
        if old_value != new_value:
            patches.append(
                UpdatePropPatch(
                    target_key=old.key,
                    prop_name=prop_name,
                    value=new_value,
                )
            )

    # Check for removed props
    for prop_name in old.props:
        if prop_name not in new.props:
            patches.append(
                UpdatePropPatch(
                    target_key=old.key,
                    prop_name=prop_name,
                    value=None,
                )
            )

    return patches


def _reconcile_children(old: VNode, new: VNode) -> list[Patch]:
    """Reconcile children using React's algorithm.

    1. Fast path: Slot-by-slot matching (position N old vs position N new)
    2. Map-based lookup: Build map for remaining old children
    3. Cleanup: Delete unmatched old children

    Args:
        old: Parent VNode with old children.
        new: Parent VNode with new children.

    Returns:
        List of patches for child operations.
    """
    patches: list[Patch] = []
    old_children = old.children
    new_children = new.children

    # Build key -> index map for old children
    old_key_map: dict[str, int] = {child.key: i for i, child in enumerate(old_children)}

    # Track which old children have been matched
    matched_old_indices: set[int] = set()

    # Phase 1: Slot-by-slot matching with key lookup
    for new_idx, new_child in enumerate(new_children):
        # Try to find matching old child by key
        old_idx = old_key_map.get(new_child.key)

        if old_idx is not None:
            # Found match - reconcile the pair
            matched_old_indices.add(old_idx)
            child_patches = reconcile(old_children[old_idx], new_child)
            patches.extend(child_patches)

            # Check if child moved
            if old_idx != new_idx:
                patches.append(MovePatch(target_key=new_child.key, new_index=new_idx))
        else:
            # No match - this is a new child
            patches.append(
                CreatePatch(
                    vnode=new_child,
                    parent_key=old.key,
                    index=new_idx,
                )
            )

    # Phase 2: Delete unmatched old children
    for old_idx, old_child in enumerate(old_children):
        if old_idx not in matched_old_indices:
            patches.append(DeletePatch(target_key=old_child.key))

    return patches
