"""
Web backend ComboBox implementation.
"""

from ...yui_common import YSelectionWidget, YItem
from .commonweb import widget_attrs, escape_html, format_label_with_shortcut


class YComboBoxWeb(YSelectionWidget):
    """Dropdown combo box widget."""
    
    def __init__(self, parent=None, label: str = "", editable: bool = False):
        super().__init__(parent)
        self._label = label
        self._editable = editable
    
    def widgetClass(self):
        return "YComboBox"
    
    def isEditable(self) -> bool:
        return self._editable
    
    def value(self) -> str:
        """Return the currently selected/entered value."""
        if self._selected_items:
            return self._selected_items[0].label()
        return ""
    
    def setValue(self, value: str):
        """Set the value (selects matching item or sets text if editable)."""
        for item in self._items:
            if item.label() == value:
                self._selected_items = [item]
                self._notify_update()
                return
        # If editable and no match, we could store the value
        if self._editable:
            self._notify_update()
    
    def _handle_selection_change(self, index: int):
        """Handle selection change from browser."""
        if 0 <= index < len(self._items):
            self._selected_items = [self._items[index]]
    
    def _notify_update(self):
        dialog = self.findDialog()
        if dialog and hasattr(dialog, '_schedule_update'):
            dialog._schedule_update(self)
    
    def render(self) -> str:
        html = ""
        
        # Label
        if self._label:
            label_html = format_label_with_shortcut(escape_html(self._label))
            html += f'<label class="mana-combobox-label">{label_html}</label>'
        
        # Select element
        attrs = widget_attrs(
            self.id(),
            "YComboBox",
            self._enabled,
            self._visible
        )
        
        options_html = ""
        for i, item in enumerate(self._items):
            selected = " selected" if item in self._selected_items else ""
            options_html += f'<option value="{i}"{selected}>{escape_html(item.label())}</option>'
        
        html += f'<select {attrs}>{options_html}</select>'
        
        return f'<div class="mana-combobox-container">{html}</div>'
