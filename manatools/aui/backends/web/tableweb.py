"""Web backend Table implementation."""
from ...yui_common import YSelectionWidget, YTableHeader, YTableItem
from .commonweb import widget_attrs, escape_html

class YTableWeb(YSelectionWidget):
    """Table view widget."""
    def __init__(self, parent=None, header: YTableHeader = None, multiSelection: bool = False):
        super().__init__(parent)
        self._header = header or YTableHeader()
        self._multi_selection = multiSelection
        self._rows = []
    
    def widgetClass(self):
        return "YTable"
    
    def addItem(self, item):
        if isinstance(item, YTableItem):
            self._rows.append(item)
        return item
    
    def deleteAllItems(self):
        self._rows.clear()
        self._selected_items.clear()
    
    def _notify_update(self):
        dialog = self.findDialog()
        if dialog and hasattr(dialog, '_schedule_update'):
            dialog._schedule_update(self)
    
    def render(self) -> str:
        # Header
        header_html = "<thead><tr>"
        for i in range(self._header.columns()):
            header_html += f'<th>{escape_html(self._header.header(i))}</th>'
        header_html += "</tr></thead>"
        
        # Body
        body_html = "<tbody>"
        for row in self._rows:
            selected = "selected" if row in self._selected_items else ""
            body_html += f'<tr class="{selected}">'
            for i in range(row.cellCount()):
                cell = row.cell(i)
                body_html += f'<td>{escape_html(cell.label()) if cell else ""}</td>'
            body_html += "</tr>"
        body_html += "</tbody>"
        
        attrs = widget_attrs(self.id(), "YTable", self._enabled, self._visible)
        return f'<table {attrs}>{header_html}{body_html}</table>'
