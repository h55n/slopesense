import functools
import http.server
import socketserver


handler = functools.partial(
    http.server.SimpleHTTPRequestHandler,
    directory=r"D:\ANTIGRAVITY\slopesense\local_status",
)

with socketserver.TCPServer(("127.0.0.1", 3013), handler) as httpd:
    httpd.serve_forever()
