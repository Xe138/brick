# Brick is a modular and expandable chat-bot capable of basic learning and information fetching by API calls.
# Copyright (C) 2015  Bill Ballou

# This file is part of Brick.

# Brick is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.

# Brick is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Brick.  If not, see <http://www.gnu.org/licenses/>.

import os
import json
import brick
from util import log

try:
  from http.server import CGIHTTPRequestHandler
  from SocketServer import TCPServer as Server
except ImportError:
  from http.server import CGIHTTPRequestHandler
  from http.server import HTTPServer as Server

# Read port selected by the cloud for the application
PORT = int(os.getenv('PORT', 8000))
# Change current directory to avoid exposure of control files
# os.chdir('static')

# Subclass Request Handler
class Handler(CGIHTTPRequestHandler):

    def write(self, text):
      self.wfile.write(bytes(text, 'utf-8'))

    # Handle GET requests
    def do_GET(self):
        if self.path == '/status':
            domain = 'localhost:8000'
            domains = ('https://brick.prettyhefty.com', 'https://betabrick.prettyhefty.com')
            origin = self.headers.get('Origin')
            if origin in domains:
              domain = origin
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', domain)
            self.end_headers()
            status = brick.core.status()
            self.write(json.dumps(status, 'utf-8'))
            return

        if self.path == '/pulse':
            brick.heartbeat()
            self.send_response(200)
            self.end_headers()
            return

        # CGIHTTPRequestHandler.do_GET(self)

    # Handle POST requests
    def do_POST(self):
        content_len = int(self.headers.get('content-length'))
        post_body = self.rfile.read(content_len)
        self.send_response(200)
        self.end_headers()

        # Convert to JSON
        body = post_body.decode("utf-8", "replace")
        data = json.loads(body)
        brick.handler(data)
        return


httpd = Server(("", PORT), Handler)
try:
  log("Start serving at port %i" % PORT)
  httpd.serve_forever()
except KeyboardInterrupt:
  pass
httpd.server_close()