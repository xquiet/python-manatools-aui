"""
Web backend dialog implementation.

YDialogWeb is the main container for web-based UI. It manages an HTTP server,
WebSocket connections, and the event loop for user interaction.
"""

import queue
import threading
import logging
import json
from typing import Optional, List, TYPE_CHECKING

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
        
        # Build widget registry
        self._build_widget_registry()
        
        # Start HTTP server in background thread
        from .server import WebServer
        self._server = WebServer(self)
        self._server_thread = threading.Thread(target=self._server.start, daemon=True)
        self._server_thread.start()
        
        # Wait for server to be ready
        import time
        for _ in range(50):  # Wait up to 5 seconds
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
        
        # Close all WebSocket connections
        with self._websocket_lock:
            for ws in self._websockets:
                try:
                    ws.close()
                except Exception:
                    pass
            self._websockets.clear()
        
        # Stop server
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
        
        # Find widget by ID
        widget = self._widget_registry.get(widget_id)
        if not widget:
            logger.warning("Widget not found: %s", widget_id)
            return
        
        # Parse reason
        reason_map = {
            "Activated": YEventReason.Activated,
            "ValueChanged": YEventReason.ValueChanged,
            "SelectionChanged": YEventReason.SelectionChanged,
        }
        reason = reason_map.get(reason_str, YEventReason.Activated)
        
        # Update widget state if provided
        if "value" in event_data:
            if hasattr(widget, "setValue"):
                widget.setValue(event_data["value"])
            elif hasattr(widget, "_value"):
                widget._value = event_data["value"]
        
        if "checked" in event_data:
            if hasattr(widget, "setChecked"):
                widget.setChecked(event_data["checked"])
        
        if "selectedIndex" in event_data:
            if hasattr(widget, "_handle_selection_change"):
                widget._handle_selection_change(event_data["selectedIndex"])
        
        # Create and post event
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
        """Schedule a UI update for a widget."""
        # Re-render the widget and broadcast update
        try:
            html = widget.render()
            self._broadcast({
                "type": "update",
                "updates": [{
                    "action": "replace",
                    "target": f"#{widget.id()}",
                    "html": html
                }]
            })
        except Exception as e:
            logger.exception("Failed to schedule update: %s", e)
    
    def render(self) -> str:
        """Render the dialog to HTML."""
        # Get application title
        title = "ManaTools"
        try:
            from ...yui import YUI
            app = YUI.application()
            if app:
                title = app.applicationTitle() or title
        except Exception:
            pass
        
        # Determine dialog class based on type
        type_class = {
            YDialogType.YMainDialog: "main",
            YDialogType.YPopupDialog: "popup",
            YDialogType.YWizardDialog: "wizard",
        }.get(self._dialog_type, "main")
        
        color_class = {
            YDialogColorMode.YDialogNormalColor: "",
            YDialogColorMode.YDialogInfoColor: "info",
            YDialogColorMode.YDialogWarnColor: "warn",
        }.get(self._color_mode, "")
        
        classes = f"mana-dialog mana-dialog-{type_class}"
        if color_class:
            classes += f" mana-dialog-{color_class}"
        
        # Render child content
        content = ""
        if self.child():
            content = self.child().render()
        
        return f'''<div id="{self.id()}" class="{classes}" data-widget-class="YDialog">
    <header class="mana-dialog-header">
        <h1 class="mana-dialog-title">{escape_html(title)}</h1>
    </header>
    <main class="mana-dialog-content">
        {content}
    </main>
</div>'''
