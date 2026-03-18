"""
Web backend ProgressBar implementation.
"""

from ...yui_common import YWidget
from .commonweb import widget_attrs, escape_html


class YProgressBarWeb(YWidget):
    """Progress bar widget."""
    
    def __init__(self, parent=None, label: str = "", max_value: int = 100):
        super().__init__(parent)
        self._label = label
        self._max_value = max_value
        self._value = 0
    
    def widgetClass(self):
        return "YProgressBar"
    
    def label(self) -> str:
        return self._label
    
    def setLabel(self, label: str):
        self._label = label
        self._notify_update()
    
    def value(self) -> int:
        return self._value
    
    def setValue(self, value: int):
        self._value = max(0, min(int(value), self._max_value))
        self._notify_update()
    
    def maxValue(self) -> int:
        return self._max_value
    
    def setMaxValue(self, max_val: int):
        self._max_value = max(1, int(max_val))
        self._notify_update()
    
    def _notify_update(self):
        dialog = self.findDialog()
        if dialog and hasattr(dialog, '_schedule_update'):
            dialog._schedule_update(self)
    
    def render(self) -> str:
        percent = (self._value / self._max_value * 100) if self._max_value > 0 else 0
        
        extra_attrs = {
            "value": str(self._value),
            "max": str(self._max_value),
        }
        
        attrs = widget_attrs(
            self.id(),
            "YProgressBar",
            self._enabled,
            self._visible,
            extra_attrs=extra_attrs
        )
        
        html = ""
        if self._label:
            html += f'<label class="mana-progressbar-label">{escape_html(self._label)}</label>'
        
        html += f'<progress {attrs}>{percent:.0f}%</progress>'
        html += f'<span class="mana-progressbar-text">{percent:.0f}%</span>'
        
        return f'<div class="mana-progressbar-container">{html}</div>'
