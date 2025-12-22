"""Tests for reconciliation system - stable keys, VNode, and diffing."""

from wtfui.core.element import Element
from wtfui.ui import Text


class TestStableKeys:
    """Phase 1: Stable element identity via keys."""

    def test_element_accepts_explicit_key(self):
        """Element can receive user-provided key."""
        el = Element(key="my-key")
        assert el.key == "my-key"

    def test_element_generates_key_when_none_provided(self):
        """Element generates internal key when not provided."""
        el = Element()
        assert el._internal_key is not None
        assert isinstance(el._internal_key, str)

    def test_explicit_key_becomes_internal_key(self):
        """User-provided key is used as internal key."""
        el = Element(key="user-key")
        assert el._internal_key == "user-key"

    def test_generated_key_includes_element_type(self):
        """Generated key includes the element's tag name."""
        el = Element()
        assert "Element" in el._internal_key

    def test_child_key_includes_parent_key(self):
        """Child's generated key includes parent's key for tree-stable identity."""
        parent = Element(key="parent")
        with parent:
            child = Element()
        assert "parent" in child._internal_key

    def test_child_key_includes_position(self):
        """Child's generated key includes position index."""
        parent = Element(key="root")
        with parent:
            child0 = Element()
            child1 = Element()
        # Keys should be different (position encoded)
        assert child0._internal_key != child1._internal_key

    def test_key_stable_across_same_structure(self):
        """Same tree structure produces same keys."""
        # First render
        parent1 = Element(key="root")
        with parent1:
            child1 = Element()

        # Second render (same structure)
        parent2 = Element(key="root")
        with parent2:
            child2 = Element()

        assert child1._internal_key == child2._internal_key

    def test_key_not_in_props(self):
        """Key is extracted from props, not stored in them."""
        el = Element(key="my-key", other="value")
        assert "key" not in el.props
        assert el.props.get("other") == "value"


class TestVNode:
    """Phase 2: Virtual DOM snapshot."""

    def test_vnode_from_element(self):
        """VNode captures element state."""
        from wtfui.core.vnode import VNode

        el = Element(key="test", foo="bar")
        vnode = VNode.from_element(el)

        assert vnode.key == "test"
        assert vnode.tag == "Element"
        assert vnode.props == {"foo": "bar"}
        assert vnode.children == []

    def test_vnode_captures_children(self):
        """VNode recursively captures children."""
        from wtfui.core.vnode import VNode

        parent = Element(key="parent")
        with parent:
            Element(key="child1")
            Element(key="child2")

        vnode = VNode.from_element(parent)

        assert len(vnode.children) == 2
        assert vnode.children[0].key == "child1"
        assert vnode.children[1].key == "child2"

    def test_vnode_preserves_element_reference(self):
        """VNode keeps reference to original element."""
        from wtfui.core.vnode import VNode

        el = Element(key="test")
        vnode = VNode.from_element(el)

        assert vnode.element is el

    def test_vnode_nested_tree(self):
        """VNode correctly captures nested tree structure."""
        from wtfui.core.vnode import VNode

        root = Element(key="root")
        with root:
            with Element(key="level1"):
                Element(key="level2")

        vnode = VNode.from_element(root)

        assert vnode.key == "root"
        assert len(vnode.children) == 1
        assert vnode.children[0].key == "level1"
        assert len(vnode.children[0].children) == 1
        assert vnode.children[0].children[0].key == "level2"

    def test_vnode_uses_internal_key_when_no_explicit_key(self):
        """VNode uses _internal_key when element has no explicit key."""
        from wtfui.core.vnode import VNode

        el = Element()  # No explicit key
        vnode = VNode.from_element(el)

        assert vnode.key == el._internal_key

    def test_vnode_captures_text_content(self):
        """VNode captures text element content."""
        from wtfui.core.vnode import VNode

        text = Text("Hello")
        vnode = VNode.from_element(text)

        assert vnode.tag == "Text"
        # Text content should be in props or accessible
        assert "content" in vnode.props or vnode.props.get("_content") == "Hello"


class TestPatches:
    """Phase 4: Patch types for granular DOM updates."""

    def test_update_prop_patch(self):
        """UpdatePropPatch captures property changes."""
        from wtfui.core.patch import UpdatePropPatch

        patch = UpdatePropPatch(target_key="el-1", prop_name="value", value="new")

        assert patch.op == "update_prop"
        assert patch.target_key == "el-1"
        assert patch.prop_name == "value"
        assert patch.value == "new"

    def test_create_patch(self):
        """CreatePatch captures new element creation."""
        from wtfui.core.patch import CreatePatch
        from wtfui.core.vnode import VNode

        vnode = VNode(key="new-el", tag="Div", props={}, children=[])
        patch = CreatePatch(vnode=vnode, parent_key="parent", index=0)

        assert patch.op == "create"
        assert patch.vnode is vnode
        assert patch.parent_key == "parent"
        assert patch.index == 0

    def test_delete_patch(self):
        """DeletePatch captures element removal."""
        from wtfui.core.patch import DeletePatch

        patch = DeletePatch(target_key="old-el")

        assert patch.op == "delete"
        assert patch.target_key == "old-el"

    def test_replace_patch(self):
        """ReplacePatch captures full element replacement."""
        from wtfui.core.patch import ReplacePatch
        from wtfui.core.vnode import VNode

        old = VNode(key="old", tag="Div", props={}, children=[])
        new = VNode(key="new", tag="Span", props={}, children=[])
        patch = ReplacePatch(old_vnode=old, new_vnode=new)

        assert patch.op == "replace"
        assert patch.old_vnode is old
        assert patch.new_vnode is new

    def test_move_patch(self):
        """MovePatch captures element reordering."""
        from wtfui.core.patch import MovePatch

        patch = MovePatch(target_key="moved", new_index=2)

        assert patch.op == "move"
        assert patch.target_key == "moved"
        assert patch.new_index == 2


class TestReconciler:
    """Phase 3: Diffing algorithm."""

    def test_reconcile_identical_returns_empty(self):
        """Identical trees produce no patches."""
        from wtfui.core.reconciler import reconcile
        from wtfui.core.vnode import VNode

        old = VNode(key="root", tag="Div", props={"class": "foo"}, children=[])
        new = VNode(key="root", tag="Div", props={"class": "foo"}, children=[])

        patches = reconcile(old, new)
        assert patches == []

    def test_reconcile_none_to_new_creates(self):
        """Creating from nothing produces CreatePatch."""
        from wtfui.core.patch import CreatePatch
        from wtfui.core.reconciler import reconcile
        from wtfui.core.vnode import VNode

        new = VNode(key="new", tag="Div", props={}, children=[])

        patches = reconcile(None, new)
        assert len(patches) == 1
        assert isinstance(patches[0], CreatePatch)
        assert patches[0].vnode is new

    def test_reconcile_old_to_none_deletes(self):
        """Removing element produces DeletePatch."""
        from wtfui.core.patch import DeletePatch
        from wtfui.core.reconciler import reconcile
        from wtfui.core.vnode import VNode

        old = VNode(key="old", tag="Div", props={}, children=[])

        patches = reconcile(old, None)
        assert len(patches) == 1
        assert isinstance(patches[0], DeletePatch)
        assert patches[0].target_key == "old"

    def test_reconcile_different_tags_replaces(self):
        """Different tags produce ReplacePatch."""
        from wtfui.core.patch import ReplacePatch
        from wtfui.core.reconciler import reconcile
        from wtfui.core.vnode import VNode

        old = VNode(key="el", tag="Div", props={}, children=[])
        new = VNode(key="el", tag="Span", props={}, children=[])

        patches = reconcile(old, new)
        assert len(patches) == 1
        assert isinstance(patches[0], ReplacePatch)

    def test_reconcile_different_keys_replaces(self):
        """Different keys produce ReplacePatch."""
        from wtfui.core.patch import ReplacePatch
        from wtfui.core.reconciler import reconcile
        from wtfui.core.vnode import VNode

        old = VNode(key="old-key", tag="Div", props={}, children=[])
        new = VNode(key="new-key", tag="Div", props={}, children=[])

        patches = reconcile(old, new)
        assert len(patches) == 1
        assert isinstance(patches[0], ReplacePatch)

    def test_reconcile_prop_change_updates(self):
        """Changed props produce UpdatePropPatch."""
        from wtfui.core.patch import UpdatePropPatch
        from wtfui.core.reconciler import reconcile
        from wtfui.core.vnode import VNode

        old = VNode(key="el", tag="Div", props={"class": "old"}, children=[])
        new = VNode(key="el", tag="Div", props={"class": "new"}, children=[])

        patches = reconcile(old, new)
        assert len(patches) == 1
        assert isinstance(patches[0], UpdatePropPatch)
        assert patches[0].prop_name == "class"
        assert patches[0].value == "new"

    def test_reconcile_removed_prop_updates_to_none(self):
        """Removed props produce UpdatePropPatch with None."""
        from wtfui.core.patch import UpdatePropPatch
        from wtfui.core.reconciler import reconcile
        from wtfui.core.vnode import VNode

        old = VNode(key="el", tag="Div", props={"class": "foo"}, children=[])
        new = VNode(key="el", tag="Div", props={}, children=[])

        patches = reconcile(old, new)
        assert len(patches) == 1
        assert isinstance(patches[0], UpdatePropPatch)
        assert patches[0].prop_name == "class"
        assert patches[0].value is None

    def test_reconcile_added_child_creates(self):
        """Added children produce CreatePatch."""
        from wtfui.core.patch import CreatePatch
        from wtfui.core.reconciler import reconcile
        from wtfui.core.vnode import VNode

        child = VNode(key="child", tag="Span", props={}, children=[])
        old = VNode(key="parent", tag="Div", props={}, children=[])
        new = VNode(key="parent", tag="Div", props={}, children=[child])

        patches = reconcile(old, new)
        assert any(isinstance(p, CreatePatch) for p in patches)

    def test_reconcile_removed_child_deletes(self):
        """Removed children produce DeletePatch."""
        from wtfui.core.patch import DeletePatch
        from wtfui.core.reconciler import reconcile
        from wtfui.core.vnode import VNode

        child = VNode(key="child", tag="Span", props={}, children=[])
        old = VNode(key="parent", tag="Div", props={}, children=[child])
        new = VNode(key="parent", tag="Div", props={}, children=[])

        patches = reconcile(old, new)
        assert any(isinstance(p, DeletePatch) for p in patches)

    def test_reconcile_children_slot_matching(self):
        """Children are matched by position first (slot-by-slot)."""
        from wtfui.core.patch import UpdatePropPatch
        from wtfui.core.reconciler import reconcile
        from wtfui.core.vnode import VNode

        old_child = VNode(key="c1", tag="Span", props={"text": "old"}, children=[])
        new_child = VNode(key="c1", tag="Span", props={"text": "new"}, children=[])
        old = VNode(key="parent", tag="Div", props={}, children=[old_child])
        new = VNode(key="parent", tag="Div", props={}, children=[new_child])

        patches = reconcile(old, new)
        # Should update prop, not replace
        assert any(isinstance(p, UpdatePropPatch) and p.prop_name == "text" for p in patches)


class TestPatchSerialization:
    """Patches can be serialized to JSON for WebSocket transport."""

    def test_update_prop_patch_to_dict(self):
        """UpdatePropPatch serializes correctly."""
        from wtfui.core.patch import UpdatePropPatch

        patch = UpdatePropPatch(target_key="el-1", prop_name="value", value="new")
        data = patch_to_dict(patch)

        assert data["op"] == "update_prop"
        assert data["target_key"] == "el-1"
        assert data["prop_name"] == "value"
        assert data["value"] == "new"

    def test_create_patch_to_dict(self):
        """CreatePatch serializes with HTML for new element."""
        from wtfui.core.patch import CreatePatch
        from wtfui.core.vnode import VNode

        vnode = VNode(key="new-el", tag="Div", props={"class": "foo"}, children=[])
        patch = CreatePatch(vnode=vnode, parent_key="parent", index=0)
        data = patch_to_dict(patch)

        assert data["op"] == "create"
        assert data["parent_key"] == "parent"
        assert data["index"] == 0
        # HTML should be included for creating new elements
        assert "html" in data or "vnode" in data

    def test_delete_patch_to_dict(self):
        """DeletePatch serializes correctly."""
        from wtfui.core.patch import DeletePatch

        patch = DeletePatch(target_key="old-el")
        data = patch_to_dict(patch)

        assert data["op"] == "delete"
        assert data["target_key"] == "old-el"


def patch_to_dict(patch):
    """Convert patch to dict for JSON serialization."""
    from dataclasses import asdict

    from wtfui.core.patch import CreatePatch

    data = asdict(patch)
    # CreatePatch needs special handling for vnode
    if isinstance(patch, CreatePatch) and patch.vnode is not None:
        data["vnode"] = {
            "key": patch.vnode.key,
            "tag": patch.vnode.tag,
            "props": patch.vnode.props,
        }
    return data
