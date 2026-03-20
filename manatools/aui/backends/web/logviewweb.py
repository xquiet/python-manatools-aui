"""
Web backend LogView implementation.
Author: Matteo Pasotti <xquiet@coriolite.com>
License: LGPLv2+
"""
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

    def render_update(self) -> tuple:
        """Return (target_selector, html) for partial DOM updates.

        Only the inner scrollable div is replaced on appendLines/clearText,
        leaving the static label untouched.
        """
        widget_id = self.id()
        height = self._visible_lines * 1.5

        extra_attrs = {
            "style": f"height:{height}em; overflow-y:auto;",
        }
        # widget_attrs puts id="{widget_id}" on the element — that id lives on
        # the inner div so _flush_update's #id selector lands here, not on the
        # outer container which holds the label.
        attrs = widget_attrs(
            widget_id, "YLogView", self._enabled, self._visible,
            extra_attrs=extra_attrs
        )

        log_html = '<br>'.join(escape_html(line) for line in self._log_entries)
        inner_html = (
            f'<div {attrs}>'
            f'<pre class="mana-logview-content">{log_html}</pre>'
            f'</div>'
        )

        return f'#{widget_id}', inner_html

    def render(self) -> str:
        """Full initial render: static label + dynamic inner div.

        Structure:
            <div class="mana-logview-container">   <- no id, no data-container-for
                <label>...</label>                  <- static, never replaced
                <div id="{widget_id}" ...>          <- render_update() targets this
                    <pre>...</pre>
                </div>
            </div>

        On appendLines/clearText, _flush_update uses render_update() which
        replaces only the inner div, leaving the label intact.
        Do NOT add data-container-for to the outer div.
        """
        label_html = ""
        if self._label:
            label_html = (
                f'<label class="mana-logview-label">'
                f'{escape_html(self._label)}'
                f'</label>'
            )

        _, inner_html = self.render_update()

        return (
            f'<div class="mana-logview-container">'
            f'{label_html}'
            f'{inner_html}'
            f'</div>'
        )