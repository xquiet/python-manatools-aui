"""Web backend Tree implementation."""
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
    
    def widgetClass(self):
        return "YTree"
    
    def addItem(self, item):
        if isinstance(item, str):
            item = YTreeItem(item)
        self._root_items.append(item)
        return item
    
    def deleteAllItems(self):
        self._root_items.clear()
        self._selected_items.clear()
    
    def rebuildTree(self):
        self._notify_update()
    
    def _notify_update(self):
        dialog = self.findDialog()
        if dialog and hasattr(dialog, '_schedule_update'):
            dialog._schedule_update(self)
    
    def _render_item(self, item, level=0) -> str:
        indent = level * 20
        children_html = ""
        if item.hasChildren():
            for child in item.childrenBegin():
                children_html += self._render_item(child, level + 1)
        
        selected = "selected" if item in self._selected_items else ""
        open_class = "open" if item.isOpen() else "collapsed"
        
        return f'''<div class="mana-tree-item {selected} {open_class}" style="padding-left: {indent}px" data-level="{level}">
            <span class="mana-tree-label">{escape_html(item.label())}</span>
            {f'<div class="mana-tree-children">{children_html}</div>' if children_html else ''}
        </div>'''
    
    def render(self) -> str:
        html = ""
        if self._label:
            html += f'<label class="mana-tree-label">{escape_html(self._label)}</label>'
        
        items_html = ""
        for item in self._root_items:
            items_html += self._render_item(item)
        
        attrs = widget_attrs(self.id(), "YTree", self._enabled, self._visible)
        html += f'<div {attrs}>{items_html}</div>'
        
        return f'<div class="mana-tree-container">{html}</div>'
