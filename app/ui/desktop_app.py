import os
import sys
import webbrowser
import http.server
import socketserver
import threading
from typing import Optional


class ModularUIApp:
    """
    Lightweight local web server launcher for the modular Windows UI prototype.
    Serves the modular frontend UI at http://localhost:8080.
    Zero external heavy GUI framework dependencies.
    """

    def __init__(self, port: int = 8080):
        self.port = port
        self.ui_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "ui")
        self.server: Optional[socketserver.TCPServer] = None

    def start(self, open_browser: bool = True):
        os.chdir(self.ui_dir)
        handler = http.server.SimpleHTTPRequestHandler

        socketserver.TCPServer.allow_reuse_address = True
        self.server = socketserver.TCPServer(("", self.port), handler)
        url = f"http://localhost:{self.port}"
        print(f"==================================================")
        print(f"🎬 MODULAR UI APPLICATION LAUNCHED")
        print(f"URL: {url}")
        print(f"UI Directory: {self.ui_dir}")
        print(f"==================================================")

        if open_browser:
            webbrowser.open(url)

        try:
            self.server.serve_forever()
        except KeyboardInterrupt:
            print("\nUI Server stopped cleanly.")
            self.server.shutdown()


def launch_ui():
    app = ModularUIApp()
    app.start()


if __name__ == "__main__":
    launch_ui()
