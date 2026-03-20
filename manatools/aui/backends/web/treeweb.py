"""
Web backend Tree implementation.
Author: Matteo Pasotti <xquiet@coriolite.com>
License: LGPLv2+
"""
from ...yui_common import YSelectionWidget, YTreeItem
from .commonweb import widget_attrs, escape_html


class YTreeWeb(YSelectionWidget):
    """Tree view widget."""

    def __init__(self, parent=None, label: str = "", multiselection=False, recursiveselection=False):
        super().__init__(parent)
        self._label = label
        self._multiselection = multiselection
        self._recursiveselection = recursiveselection
        self._root_items = []
        # Maps stable string id -> YTreeItem for O(1) lookup on click events.
        self._item_registry: dict = {}

    def widgetClass(self):
        return "YTree"

    def addItem(self, item):
        if isinstance(item, str):
            item = YTreeItem(item)
        self._root_items.append(item)
        self._register_item_tree(item)
        # honour pre-selected items coming from the caller
        if item.selected():
            self.selectItem(item, True)
        return item

    def deleteAllItems(self):
        self._root_items.clear()
        self._selected_items.clear()
        self._item_registry.clear()

    def rebuildTree(self):
        self._notify_update()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _item_id(self, item: YTreeItem) -> str:
        """Return a stable DOM-safe id string for a YTreeItem."""
        return f"{self.id()}-item-{id(item)}"

    def _register_item_tree(self, item: YTreeItem):
        """Recursively register item and all its descendants."""
        self._item_registry[self._item_id(item)] = item
        if item.selected():
            self.selectItem(item, True)
        if item.hasChildren():
            for child in item.childrenBegin():
                self._register_item_tree(child)

    def _handle_item_click(self, item_id: str):
        """Called by the dialog event dispatcher when a tree item is clicked.

        Updates internal selection state and returns the clicked YTreeItem
        (or None if the id is unknown).
        """
        item = self._item_registry.get(item_id)
        if item is None:
            return None
        if not self._multiselection:
            self._selected_items.clear()
        self.selectItem(item, True)
        return item

    def _notify_update(self):
        dialog = self.findDialog()
        if dialog and hasattr(dialog, '_schedule_update'):
            dialog._schedule_update(self)

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def _render_item(self, item: YTreeItem, level: int = 0) -> str:
        indent = level * 20
        item_id = self._item_id(item)
        selected_class = "selected" if item in self._selected_items else ""
        open_class = "open" if item.isOpen() else "collapsed"

        children_html = ""
        if item.hasChildren():
            for child in item.childrenBegin():
                children_html += self._render_item(child, level + 1)

        children_block = (
            f'<div class="mana-tree-children">{children_html}</div>'
            if children_html else ""
        )

        # data-item-id links the DOM node back to the YTreeItem via
        # _item_registry; data-tree-id identifies the owning YTreeWeb widget.
        # stopPropagation in the JS handler (see below) prevents bubbling so
        # that only the innermost clicked item fires the event.
        return (
            f'<div class="mana-tree-item {selected_class} {open_class}"'
            f' style="padding-left:{indent}px"'
            f' data-level="{level}"'
            f' data-item-id="{item_id}"'
            f' data-tree-id="{self.id()}">'
            f'<span class="mana-tree-toggle"></span>'
            f'<span class="mana-tree-label">{escape_html(item.label())}</span>'
            f'{children_block}'
            f'</div>'
        )

    def render(self) -> str:
        # Rebuild registry on every full render so ids stay consistent after
        # deleteAllItems() + re-population cycles.
        self._item_registry.clear()
        for item in self._root_items:
            self._register_item_tree(item)

        label_html = ""
        if self._label:
            label_html = (
                f'<label class="mana-tree-label">'
                f'{escape_html(self._label)}'
                f'</label>'
            )

        items_html = "".join(self._render_item(item) for item in self._root_items)
        attrs = widget_attrs(self.id(), "YTree", self._enabled, self._visible)

        return (
            f'<div class="mana-tree-container" data-container-for="{self.id()}">'
            f'{label_html}'
            f'<div {attrs}>{items_html}</div>'
            f'</div>'
        )