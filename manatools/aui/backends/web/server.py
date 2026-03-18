"""
HTTP and WebSocket server for the web backend.

This module provides a simple HTTP server that serves the dialog HTML
and handles WebSocket connections for real-time event communication.
"""

import http.server
import socketserver
import threading
import json
import os
import logging
import hashlib
import base64
import struct
import socket
from typing import Optional, TYPE_CHECKING, Callable
from urllib.parse import urlparse, parse_qs

if TYPE_CHECKING:
    from .dialogweb import YDialogWeb

logger = logging.getLogger("manatools.aui.web.server")


class WebSocketHandler:
    """
    Simple WebSocket handler implementing RFC 6455.
    
    This is a minimal implementation that handles text frames only.
    """
    
    GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
    
    def __init__(self, request, client_address, on_message: Callable[[str], None], on_close: Callable[[], None]):
        self.request = request
        self.client_address = client_address
        self.on_message = on_message
        self.on_close = on_close
        self._closed = False
        self._lock = threading.Lock()
    
    @classmethod
    def handshake(cls, request_handler) -> Optional["WebSocketHandler"]:
        """
        Perform WebSocket handshake. Returns WebSocketHandler on success.
        """
        try:
            key = request_handler.headers.get('Sec-WebSocket-Key')
            if not key:
                return None
            
            # Calculate accept key
            accept = hashlib.sha1((key + cls.GUID).encode()).digest()
            accept_key = base64.b64encode(accept).decode()
            
            # Send handshake response
            response = (
                "HTTP/1.1 101 Switching Protocols\r\n"
                "Upgrade: websocket\r\n"
                "Connection: Upgrade\r\n"
                f"Sec-WebSocket-Accept: {accept_key}\r\n"
                "\r\n"
            )
            request_handler.wfile.write(response.encode())
            request_handler.wfile.flush()
            
            return cls(
                request_handler.request,
                request_handler.client_address,
                lambda msg: None,  # Placeholder, set by caller
                lambda: None
            )
        except Exception as e:
            logger.exception("WebSocket handshake failed: %s", e)
            return None
    
    def receive_frame(self) -> Optional[str]:
        """Receive a WebSocket frame and return the text payload."""
        try:
            # Read first two bytes
            header = self.request.recv(2)
            if len(header) < 2:
                return None
            
            fin = (header[0] >> 7) & 1
            opcode = header[0] & 0x0F
            masked = (header[1] >> 7) & 1
            payload_len = header[1] & 0x7F
            
            # Handle close frame
            if opcode == 0x08:
                self._closed = True
                return None
            
            # Handle ping
            if opcode == 0x09:
                self._send_pong()
                return self.receive_frame()
            
            # Only handle text frames
            if opcode != 0x01:
                return self.receive_frame()
            
            # Extended payload length
            if payload_len == 126:
                ext = self.request.recv(2)
                payload_len = struct.unpack(">H", ext)[0]
            elif payload_len == 127:
                ext = self.request.recv(8)
                payload_len = struct.unpack(">Q", ext)[0]
            
            # Masking key
            mask_key = self.request.recv(4) if masked else b''
            
            # Payload
            payload = self.request.recv(payload_len)
            
            # Unmask if needed
            if masked:
                payload = bytes(b ^ mask_key[i % 4] for i, b in enumerate(payload))
            
            return payload.decode('utf-8')
        except Exception as e:
            if not self._closed:
                logger.debug("WebSocket receive error: %s", e)
            return None
    
    def send(self, message: str):
        """Send a text message through the WebSocket."""
        with self._lock:
            if self._closed:
                return
            try:
                payload = message.encode('utf-8')
                length = len(payload)
                
                # Build frame
                frame = bytearray()
                frame.append(0x81)  # FIN + text opcode
                
                if length < 126:
                    frame.append(length)
                elif length < 65536:
                    frame.append(126)
                    frame.extend(struct.pack(">H", length))
                else:
                    frame.append(127)
                    frame.extend(struct.pack(">Q", length))
                
                frame.extend(payload)
                self.request.sendall(bytes(frame))
            except Exception as e:
                logger.debug("WebSocket send error: %s", e)
                self._closed = True
    
    def _send_pong(self):
        """Send a pong frame."""
        with self._lock:
            try:
                self.request.sendall(bytes([0x8A, 0x00]))  # Pong with no payload
            except Exception:
                pass
    
    def close(self):
        """Close the WebSocket connection."""
        with self._lock:
            if self._closed:
                return
            self._closed = True
            try:
                # Send close frame
                self.request.sendall(bytes([0x88, 0x00]))
            except Exception:
                pass
    
    def run(self):
        """Main loop to receive and process messages."""
        try:
            while not self._closed:
                message = self.receive_frame()
                if message is None:
                    break
                try:
                    self.on_message(message)
                except Exception as e:
                    logger.exception("Error handling WebSocket message: %s", e)
        finally:
            self._closed = True
            try:
                self.on_close()
            except Exception:
                pass


class ManaToolsRequestHandler(http.server.BaseHTTPRequestHandler):
    """HTTP request handler for ManaTools web backend."""
    
    # Reference to the dialog, set by the server
    dialog: Optional["YDialogWeb"] = None
    
    def log_message(self, format, *args):
        """Override to use Python logging instead of stderr."""
        logger.debug(format, *args)
    
    def do_GET(self):
        """Handle GET requests."""
        parsed = urlparse(self.path)
        path = parsed.path
        
        if path == "/" or path == "/index.html":
            self._serve_main_page()
        elif path == "/ws":
            self._handle_websocket()
        elif path.startswith("/static/"):
            self._serve_static(path[8:])  # Remove /static/ prefix
        elif path == "/events":
            # SSE endpoint for browsers without WebSocket
            self._serve_sse()
        else:
            self.send_error(404, "Not Found")
    
    def do_POST(self):
        """Handle POST requests for events."""
        parsed = urlparse(self.path)
        
        if parsed.path == "/event":
            self._handle_event_post()
        else:
            self.send_error(404, "Not Found")
    
    def _serve_main_page(self):
        """Serve the main HTML page."""
        if not self.dialog:
            self.send_error(500, "No dialog available")
            return
        
        try:
            html_content = self._build_full_page()
            
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", len(html_content.encode()))
            self.end_headers()
            self.wfile.write(html_content.encode())
        except Exception as e:
            logger.exception("Error serving main page: %s", e)
            self.send_error(500, str(e))
    
    def _build_full_page(self) -> str:
        """Build the complete HTML page with dialog content."""
        # Get application title
        title = "ManaTools"
        try:
            from ...yui import YUI
            app = YUI.application()
            if app:
                title = app.applicationTitle() or title
        except Exception:
            pass
        
        # Get dialog content
        dialog_html = self.dialog.render() if self.dialog else ""
        
        return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <link rel="stylesheet" href="/static/css/manatools.css">
</head>
<body>
    <div id="mana-app">
        {dialog_html}
    </div>
    <script src="/static/js/manatools.js"></script>
</body>
</html>'''
    
    def _serve_static(self, filename: str):
        """Serve static files (CSS, JS)."""
        # Security: prevent path traversal
        if ".." in filename or filename.startswith("/"):
            self.send_error(403, "Forbidden")
            return
        
        static_dir = os.path.join(os.path.dirname(__file__), "static")
        filepath = os.path.join(static_dir, filename)
        
        if not os.path.isfile(filepath):
            self.send_error(404, "Not Found")
            return
        
        # Determine content type
        if filename.endswith(".css"):
            content_type = "text/css"
        elif filename.endswith(".js"):
            content_type = "application/javascript"
        elif filename.endswith(".png"):
            content_type = "image/png"
        elif filename.endswith(".svg"):
            content_type = "image/svg+xml"
        else:
            content_type = "application/octet-stream"
        
        try:
            with open(filepath, "rb") as f:
                content = f.read()
            
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", len(content))
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            logger.exception("Error serving static file: %s", e)
            self.send_error(500, str(e))
    
    def _handle_websocket(self):
        """Upgrade connection to WebSocket and handle messages."""
        ws = WebSocketHandler.handshake(self)
        if not ws:
            self.send_error(400, "WebSocket handshake failed")
            return
        
        # Register with dialog
        if self.dialog:
            self.dialog._register_websocket(ws)
        
        def on_message(message: str):
            try:
                data = json.loads(message)
                if self.dialog:
                    self.dialog._handle_ws_message(data)
            except json.JSONDecodeError:
                logger.warning("Invalid JSON in WebSocket message: %s", message)
        
        def on_close():
            if self.dialog:
                self.dialog._unregister_websocket(ws)
        
        ws.on_message = on_message
        ws.on_close = on_close
        
        # Run WebSocket message loop (blocking)
        ws.run()
    
    def _handle_event_post(self):
        """Handle event POST requests (fallback for non-WebSocket)."""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            data = json.loads(body)
            
            if self.dialog:
                self.dialog._handle_ws_message(data)
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status": "ok"}')
        except Exception as e:
            logger.exception("Error handling event POST: %s", e)
            self.send_error(500, str(e))
    
    def _serve_sse(self):
        """Serve Server-Sent Events (fallback for browsers without WebSocket)."""
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        
        # Keep connection open for events
        # This is a simplified implementation
        try:
            while True:
                # Send keepalive
                self.wfile.write(b": keepalive\n\n")
                self.wfile.flush()
                threading.Event().wait(30)  # Wait 30 seconds
        except Exception:
            pass


class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    """HTTP server that handles requests in separate threads."""
    allow_reuse_address = True
    daemon_threads = True


class WebServer:
    """
    Main web server for the ManaTools web backend.
    
    Manages HTTP server, WebSocket connections, and serves the dialog UI.
    """
    
    def __init__(self, dialog: "YDialogWeb", host: str = "127.0.0.1", port: int = 0):
        """
        Initialize the web server.
        
        Args:
            dialog: The YDialogWeb instance to serve
            host: Host to bind to (default: localhost only)
            port: Port to bind to (0 for auto-select)
        """
        self.dialog = dialog
        self.host = host
        self.port = port
        self._server: Optional[ThreadedHTTPServer] = None
        self._running = False
        self._lock = threading.Lock()
    
    def start(self):
        """Start the HTTP server (blocking call)."""
        with self._lock:
            if self._running:
                return
            
            # Create custom handler class with dialog reference
            handler_class = type(
                'DialogRequestHandler',
                (ManaToolsRequestHandler,),
                {'dialog': self.dialog}
            )
            
            # Find available port if port is 0
            self._server = ThreadedHTTPServer((self.host, self.port), handler_class)
            self.port = self._server.server_address[1]
            self._running = True
        
        logger.info("Web server started at %s", self.get_url())
        
        try:
            self._server.serve_forever()
        except Exception as e:
            logger.exception("Server error: %s", e)
        finally:
            self._running = False
    
    def stop(self):
        """Stop the HTTP server."""
        with self._lock:
            if self._server and self._running:
                self._server.shutdown()
                self._running = False
    
    def get_url(self) -> str:
        """Get the URL where the dialog is accessible."""
        return f"http://{self.host}:{self.port}/"
    
    def is_running(self) -> bool:
        """Check if the server is running."""
        return self._running
