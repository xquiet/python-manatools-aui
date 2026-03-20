# -*- coding: utf-8 -*-
"""
Web backend dialog implementation.

Author: Matteo Pasotti <xquiet@coriolite.com>

License: LGPLv2+

YDialogWeb is the main container for web-based UI. It manages an HTTP server,
WebSocket connections, and the event loop for user interaction.
"""

import queue
import threading
import logging
import json
from typing import Optional, List, TYPE_CHECKING
from importlib.resources import files

from ...yui_common import (
    YSingleChildContainerWidget,
    YDialogType,
    YDialogColorMode,
    YEvent,
    YWidgetEvent,
    YCancelEvent,
    YTimeoutEvent,
    YKeyEvent,
    YMenuEvent,
    YEventReason,
    YUINoDialogException,
)
from .commonweb import escape_html

if TYPE_CHECKING:
    from .server import WebSocketHandler, WebServer

logger = logging.getLogger("manatools.aui.web.YDialogWeb")

# ---------------------------------------------------------------------------
# Page builder
# ---------------------------------------------------------------------------

class PageBuilder:
    """
    Builds the full HTML page by loading ``templates/dialog.html`` from the
    package and substituting the three runtime slots:

    * ``{{ id }}``          - dialog id
    * ``{{ title }}``       - dialog title
    * ``{{ classes }}``     - dialog classes
    * ``{{ content }}``     - rendered content

    The template is read from disk exactly once (class-level cache) so
    repeated requests pay no I/O cost.
    """

    _template: Optional[str] = None
    _template_lock = threading.Lock()

    @classmethod
    def _load_template(cls) -> str:
        if cls._template is None:
            with cls._template_lock:
                if cls._template is None:
                    cls._template = (
                        files("manatools.aui.backends.web")
                        .joinpath("templates/dialog.html")
                        .read_text(encoding="utf-8")
                    )
        return cls._template

    @classmethod
    def build(cls, *, _id: str, title: str, classes: str, content: str) -> str:
        """Return the complete HTML dialog as a string."""
        return (
            cls._load_template()
            .replace("{{ id }}", _id)
            .replace("{{ classes }}", classes)
            .replace("{{ title }}", title)
            .replace("{{ content }}", content)
        )


class YDialogWeb(YSingleChildContainerWidget):
    """
    Web-based dialog implementation.

    Manages an HTTP server to serve the dialog as HTML and uses WebSocket
    for real-time event communication with the browser.
    """

    _open_dialogs: List["YDialogWeb"] = []

    def __init__(self, dialog_type=YDialogType.YMainDialog, color_mode=YDialogColorMode.YDialogNormalColor):
        super().__init__()
        self._dialog_type = dialog_type
        self._color_mode = color_mode
        self._is_open = False
        self._event_queue: queue.Queue = queue.Queue()
        self._server: Optional["WebServer"] = None
        self._server_thread: Optional[threading.Thread] = None
        self._websockets: List["WebSocketHandler"] = []
        self._websocket_lock = threading.Lock()
        self._default_button = None
        self._widget_registry: dict = {}  # id -> widget mapping
        self._pending_updates: dict = {}  # widget_id -> threading.Timer
        self._pending_lock = threading.Lock()

        YDialogWeb._open_dialogs.append(self)
        logger.debug("YDialogWeb created: %s", self.debugLabel())

    def widgetClass(self):
        return "YDialog"

    @staticmethod
    def currentDialog(doThrow=True) -> Optional["YDialogWeb"]:
        """Return the topmost open dialog, or raise if none."""
        if YDialogWeb._open_dialogs:
            return YDialogWeb._open_dialogs[-1]
        if doThrow:
            raise YUINoDialogException("No dialog is currently open")
        return None

    @staticmethod
    def topmostDialog(doThrow=True) -> Optional["YDialogWeb"]:
        """Same as currentDialog."""
        return YDialogWeb.currentDialog(doThrow=doThrow)

    def isTopmostDialog(self) -> bool:
        """Return whether this dialog is the topmost."""
        return YDialogWeb._open_dialogs[-1] == self if YDialogWeb._open_dialogs else False

    def open(self):
        """
        Start the HTTP server and make the dialog accessible via browser.

        This is non-blocking - call waitForEvent() to process events.
        """
        if self._is_open:
            return

        self._build_widget_registry()

        from .server import WebServer
        self._server = WebServer(self)
        self._server_thread = threading.Thread(target=self._server.start, daemon=True)
        self._server_thread.start()

        import time
        for _ in range(50):
            if self._server.is_running():
                break
            time.sleep(0.1)

        self._is_open = True
        print(f"\n{'='*50}")
        print(f"  Dialog available at: {self._server.get_url()}")
        print(f"  Open this URL in your web browser")
        print(f"{'='*50}\n")

    def isOpen(self) -> bool:
        return self._is_open

    def waitForEvent(self, timeout_millisec: int = 0) -> YEvent:
        """
        Block until an event is received from the browser.

        Args:
            timeout_millisec: Timeout in milliseconds (0 = no timeout)

        Returns:
            YEvent (YWidgetEvent, YCancelEvent, YTimeoutEvent, etc.)
        """
        if not self._is_open:
            self.open()

        timeout = timeout_millisec / 1000.0 if timeout_millisec > 0 else None

        try:
            event = self._event_queue.get(timeout=timeout)
            return event
        except queue.Empty:
            return YTimeoutEvent()

    def destroy(self, doThrow=True) -> bool:
        """Close the dialog and stop the server."""
        logger.debug("Destroying dialog: %s", self.debugLabel())

        # Notify all connected browsers before closing so they show a clean
        # "session ended" state instead of looping on reconnect.
        try:
            self._broadcast({
                "type": "shutdown",
                "reason": "The application has closed.",
            })
        except Exception:
            pass

        # Close all WebSocket connections
        with self._websocket_lock:
            for ws in self._websockets:
                try:
                    ws.close()
                except Exception:
                    pass
            self._websockets.clear()

        if self._server:
            self._server.stop()
            self._server = None

        self._is_open = False

        if self in YDialogWeb._open_dialogs:
            YDialogWeb._open_dialogs.remove(self)

        return True

    @classmethod
    def deleteTopmostDialog(cls, doThrow=True) -> bool:
        """Delete the topmost dialog."""
        if cls._open_dialogs:
            return cls._open_dialogs[-1].destroy(doThrow)
        return False

    @classmethod
    def deleteAllDialogs(cls, doThrow=True) -> bool:
        """Delete all open dialogs."""
        ok = True
        while cls._open_dialogs:
            try:
                cls._open_dialogs[-1].destroy(doThrow)
            except Exception:
                ok = False
                try:
                    cls._open_dialogs.pop()
                except Exception:
                    break
        return ok

    def setDefaultButton(self, button) -> bool:
        """Set the default button for this dialog."""
        if button is None:
            self._default_button = None
            return True

        try:
            if button.widgetClass() != "YPushButton":
                logger.error("Default button must be a YPushButton")
                return False
        except Exception:
            return False

        self._default_button = button
        return True

    def _post_event(self, event: YEvent):
        """Post an event to the dialog's event queue."""
        self._event_queue.put(event)

    def _register_websocket(self, ws: "WebSocketHandler"):
        """Register a new WebSocket connection."""
        with self._websocket_lock:
            self._websockets.append(ws)
        logger.debug("WebSocket connected, total: %d", len(self._websockets))

    def _unregister_websocket(self, ws: "WebSocketHandler"):
        """Unregister a WebSocket connection."""
        with self._websocket_lock:
            if ws in self._websockets:
                self._websockets.remove(ws)
        logger.debug("WebSocket disconnected, remaining: %d", len(self._websockets))

    def _broadcast(self, message: dict):
        """Broadcast a message to all connected WebSocket clients."""
        data = json.dumps(message)
        with self._websocket_lock:
            for ws in list(self._websockets):
                try:
                    ws.send(data)
                except Exception as e:
                    logger.debug("Failed to send to WebSocket: %s", e)

    def _handle_ws_message(self, data: dict):
        """Handle a message received via WebSocket."""
        msg_type = data.get("type", "")

        if msg_type == "event":
            self._handle_widget_event(data)
        elif msg_type == "close":
            self._post_event(YCancelEvent())
        elif msg_type == "key":
            self._handle_key_event(data)
        else:
            logger.warning("Unknown WebSocket message type: %s", msg_type)

    def _handle_widget_event(self, data: dict):
        """Handle a widget event from the browser."""
        widget_id = data.get("widget_id", "")
        reason_str = data.get("reason", "Activated")
        event_data = data.get("data", {})

        widget = self._widget_registry.get(widget_id)
        if not widget:
            logger.warning("Widget not found: %s", widget_id)
            return

        reason_map = {
            "Activated":        YEventReason.Activated,
            "ValueChanged":     YEventReason.ValueChanged,
            "SelectionChanged": YEventReason.SelectionChanged,
        }
        reason = reason_map.get(reason_str, YEventReason.Activated)

        if "value" in event_data:
            if hasattr(widget, "setValue"):
                widget.setValue(event_data["value"])
            elif hasattr(widget, "_value"):
                widget._value = event_data["value"]

        if "checked" in event_data:
            if hasattr(widget, "setChecked"):
                widget.setChecked(event_data["checked"])

        # Tree item selection — uses a stable item id instead of a
        # flat index because tree items are nested.
        if "itemId" in event_data:
            if hasattr(widget, '_handle_item_click'):
                widget._handle_item_click(event_data["itemId"])
 
        # (existing selectedIndex / selectedValue block follows unchanged)
        if "selectedIndex" in event_data or "selectedValue" in event_data:
            if hasattr(widget, "_handle_selection_change"):
                # Prefer value-based lookup: avoids off-by-one caused by a
                # non-selectable label <option> at index 0 in the rendered HTML.
                selected_value = event_data.get("selectedValue")
                selected_index = event_data.get("selectedIndex", 0)
                widget._handle_selection_change(selected_index, selected_value)

        event = YWidgetEvent(widget, reason)
        self._post_event(event)

    def _handle_key_event(self, data: dict):
        """Handle a keyboard event from the browser."""
        key = data.get("key", "")
        widget_id = data.get("widget_id", "")

        widget = self._widget_registry.get(widget_id)
        event = YKeyEvent(key, widget)
        self._post_event(event)

    def _build_widget_registry(self):
        """Build a mapping of widget IDs to widget objects."""
        self._widget_registry.clear()
        self._register_widget_tree(self)

    def _register_widget_tree(self, widget):
        """Recursively register all widgets in the tree."""
        self._widget_registry[widget.id()] = widget

        if hasattr(widget, '_children'):
            for child in widget._children:
                self._register_widget_tree(child)

    def _schedule_update(self, widget):
        """Schedule a UI update for a widget.

        Rapid successive calls for the same widget within a short window are
        coalesced: only the last state is broadcast.  This prevents multiple
        stale intermediate renders arriving at the browser out of order when
        application code mutates a widget in several steps (e.g. deleteAllItems
        -> setLabel -> addItems).
        """
        widget_id = widget.id()
        with self._pending_lock:
            existing = self._pending_updates.get(widget_id)
            if existing is not None:
                existing.cancel()
            timer = threading.Timer(
                0.05,  # 50 ms coalesce window
                self._flush_update,
                args=(widget,),
            )
            self._pending_updates[widget_id] = timer
            timer.start()

    def _flush_update(self, widget):
        """Actually broadcast the update for a widget (called by the timer).
 
        If the widget exposes a ``render_update()`` method it is called instead
        of ``render()`` so that widgets with static parts (e.g. a label that
        must not be duplicated on every value change, like YProgressBar) can
        return a precise (selector, html) pair targeting only their dynamic
        inner element.
 
        Falls back to the original behaviour for all other widgets:
        targets ``[data-container-for="<id>"]`` first so that widgets that
        wrap themselves in a container div (e.g. ComboBox with a label) are
        replaced atomically, then falls back to ``#<id>`` for simple widgets.
        """
        with self._pending_lock:
            self._pending_updates.pop(widget.id(), None)
        try:
            if hasattr(widget, 'render_update'):
                target, html = widget.render_update()
            else:
                html = widget.render()
                target = f'[data-container-for="{widget.id()}"], #{widget.id()}'
 
            self._broadcast({
                "type": "update",
                "updates": [{
                    "action": "replace",
                    "target": target,
                    "html": html,
                }]
            })
        except Exception as e:
            logger.exception("Failed to flush update: %s", e)

    def render(self) -> str:
        """Render the dialog to HTML."""
        title = "ManaTools"
        try:
            from ...yui import YUI
            app = YUI.application()
            if app:
                title = app.applicationTitle() or title
        except Exception:
            pass

        type_class = {
            YDialogType.YMainDialog:   "main",
            YDialogType.YPopupDialog:  "popup",
            YDialogType.YWizardDialog: "wizard",
        }.get(self._dialog_type, "main")

        color_class = {
            YDialogColorMode.YDialogNormalColor: "",
            YDialogColorMode.YDialogInfoColor:   "info",
            YDialogColorMode.YDialogWarnColor:   "warn",
        }.get(self._color_mode, "")

        classes = f"mana-dialog mana-dialog-{type_class}"
        if color_class:
            classes += f" mana-dialog-{color_class}"

        content = self.child().render() if self.child() else ""
        return PageBuilder.build(
            _id=self.id(),
            title=escape_html(title),
            classes=classes,
            content=content,
        )