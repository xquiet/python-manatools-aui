# -*- coding: utf-8 -*-
"""
Web backend Label implementation.

Author: Matteo Pasotti <xquiet@coriolite.com>

License: LGPLv2+
"""
from ...yui_common import YWidget
from .commonweb import widget_attrs, escape_html, format_label_with_shortcut


class YLabelWeb(YWidget):
    """Text label widget."""

    def __init__(self, parent=None, text: str = "", isHeading: bool = False, isOutputField: bool = False):
        super().__init__(parent)
        self._text = text
        self._is_heading = isHeading
        self._is_output_field = isOutputField

    def widgetClass(self):
        return "YLabel"

    def label(self) -> str:
        return self._text

    def text(self) -> str:
        return self._text

    def setText(self, text: str):
        self._text = text
        self._notify_update()

    def setLabel(self, text: str):
        self.setText(text)

    def isHeading(self) -> bool:
        return self._is_heading

    def isOutputField(self) -> bool:
        return self._is_output_field

    def _notify_update(self):
        """Notify dialog that this widget needs re-render."""
        dialog = self.findDialog()
        if dialog and hasattr(dialog, '_schedule_update'):
            dialog._schedule_update(self)

    def render(self) -> str:
        """Render the label to HTML."""
        extra_classes = ""
        if self._is_heading:
            extra_classes = "mana-heading"
        elif self._is_output_field:
            extra_classes = "mana-output"

        attrs = widget_attrs(
            self.id(),
            "YLabel",
            self._enabled,
            self._visible,
            extra_classes,
        )

        # Static UI labels (e.g. field captions) may carry &X shortcut notation
        # and benefit from format_label_with_shortcut.
        # Dynamic output text set via setText() must not go through shortcut
        # formatting: it is plain user/application data and should only be
        # HTML-escaped for safety, never further transformed.
        if self._is_output_field or self._is_heading:
            text_html = escape_html(self._text)
        else:
            text_html = format_label_with_shortcut(escape_html(self._text))

        if self._is_heading:
            return f'<h2 {attrs}>{text_html}</h2>'
        else:
            return f'<span {attrs}>{text_html}</span>'