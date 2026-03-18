"""Web backend LogView implementation."""
from ...yui_common import YWidget
from .commonweb import widget_attrs, escape_html

class YLogViewWeb(YWidget):
    """Log view widget for displaying log messages."""
    def __init__(self, parent=None, label: str = "", visibleLines: int = 10, storedLines: int = 0):
        super().__init__(parent)
        self._label = label
        self._visible_lines = visibleLines
        self._stored_lines = storedLines if storedLines > 0 else visibleLines * 10
        self._log_entries = []
    
    def widgetClass(self):
        return "YLogView"
    
    def label(self) -> str:
        return self._label
    
    def setLabel(self, label: str):
        self._label = label
        self._notify_update()
    
    def appendLines(self, text: str):
        """Append lines to the log."""
        lines = text.split('\n')
        self._log_entries.extend(lines)
        # Trim to stored limit
        if len(self._log_entries) > self._stored_lines:
            self._log_entries = self._log_entries[-self._stored_lines:]
        self._notify_update()
    
    def clearText(self):
        """Clear all log entries."""
        self._log_entries.clear()
        self._notify_update()
    
    def logText(self) -> str:
        """Get all log text."""
        return '\n'.join(self._log_entries)
    
    def _notify_update(self):
        dialog = self.findDialog()
        if dialog and hasattr(dialog, '_schedule_update'):
            dialog._schedule_update(self)
    
    def render(self) -> str:
        height = self._visible_lines * 1.5  # Approximate line height in em
        
        extra_attrs = {
            "style": f"height: {height}em; overflow-y: auto;",
        }
        
        attrs = widget_attrs(self.id(), "YLogView", self._enabled, self._visible, extra_attrs=extra_attrs)
        
        html = ""
        if self._label:
            html += f'<label class="mana-logview-label">{escape_html(self._label)}</label>'
        
        log_html = '<br>'.join(escape_html(line) for line in self._log_entries)
        html += f'<div {attrs}><pre class="mana-logview-content">{log_html}</pre></div>'
        
        return f'<div class="mana-logview-container">{html}</div>'
