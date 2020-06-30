# -*- coding:utf-8 -*-
import re, sys
import struct
from base64 import b64encode
from hashlib import sha1
from socketserver import ThreadingMixIn, TCPServer, StreamRequestHandler
from http.server import BaseHTTPRequestHandler


'''
+-+-+-+-+-------+-+-------------+-------------------------------+
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-------+-+-------------+-------------------------------+
|F|R|R|R| opcode|M| Payload len |    Extended payload length    |
|I|S|S|S|  (4)  |A|     (7)     |             (16/64)           |
|N|V|V|V|       |S|             |   (if payload len==126/127)   |
| |1|2|3|       |K|             |                               |
+-+-+-+-+-------+-+-------------+ - - - - - - - - - - - - - - - +
|     Extended payload length continued, if payload len == 127  |
+ - - - - - - - - - - - - - - - +-------------------------------+
|                     Payload Data continued ...                |
+---------------------------------------------------------------+
'''

FIN    = 0x80
OPCODE = 0x0f
MASKED = 0x80
PAYLOAD_LEN = 0x7f
PAYLOAD_LEN_EXT16 = 0x7e
PAYLOAD_LEN_EXT64 = 0x7f
OPCODE_TEXT = 0x01
CLOSE_CONN  = 0x8

DEBUG = False


# -------------------------------- API --------------------------------

class API:

    # -- user implemented interface --
    
    # http
    def do_GET(self, handler):
        pass
    def do_POST(self, handler):
        pass

    # websocket
    def new_client(self, client):
        pass
    def client_left(self, client):
        pass
    def message_received(self, client, msg):
        pass

    # -- library implemented interface --
    
    def send_message(self, to_client, msg):
        pass
    def send_message_to_all(self, msg):
        pass
    def close(self, to_client):
        pass



# ---------------- WebServer (needs to be inherited) ----------------

class WebServer(ThreadingMixIn, TCPServer, API):

    allow_reuse_address = True
    daemon_threads = True
    clients=[]

    def __init__(self, port, host='0.0.0.0'):
        self.port=port
        TCPServer.__init__(self, (host, port), MixedHandler)

    def _new_client(self, client):
        self.clients.append(client)
        self.new_client(client)

    def _client_left(self, client):
        self.client_left(client)
        if client in self.clients:
            self.clients.remove(client)

    def _message_received(self, client, msg):
        self.message_received(client, msg)

    def send_message(self, client, msg):
        client.send_message(msg)

    def send_message_to_all(self, msg):
        for client in self.clients:
            self.send_message(client, msg)

    def close(self, client):
        client.close()


# ------------ MixedHandler (support both http and websocket) ------------

class MixedHandler(BaseHTTPRequestHandler):

    def __init__(self, socket, addr, server):
        self.server=server
        StreamRequestHandler.__init__(self, socket, addr, server)

    # -- common --
    
    def setup(self):
        StreamRequestHandler.setup(self)
        self.is_websocket = self.rfile.peek().find(b'Upgrade: websocket') != -1

        if self.is_websocket:
            self.keep_alive = True
            self.finished = False
            self.handshake_done = False
            self.valid_client = False
            self.bytes_buffer = bytearray()

    def handle(self):
        if self.is_websocket:
            while not self.finished and self.keep_alive:
                if not self.handshake_done:
                    self.handshake()
                elif self.valid_client:
                    self.read_message()
        else:
            BaseHTTPRequestHandler.handle(self)

    def finish(self):
        if self.is_websocket:
            if not self.finished:
                self.finished = True
                StreamRequestHandler.finish(self)
                self.server._client_left(self)
        else:
            StreamRequestHandler.finish(self)

    def __getattr__(self, name):
        if name.startswith('_'):
            raise AttributeError()

    # -- http --
    
    def log_message(self, format, *args):
        DEBUG and BaseHTTPRequestHandler.log_message(self, format, *args)

    def do_GET(self):
        self.server.do_GET(self)

    def do_POST(self):
        self.server.do_POST(self)

    # -- websocket --

    def handshake(self):
        msg_len = len(self.rfile.peek())
        message = self.rfile.read(msg_len).decode().strip()
        upgrade = re.search('\nupgrade[\s]*:[\s]*websocket', message.lower())
        if not upgrade:
            self.keep_alive = False
            return
        key = re.search('\n[sS]ec-[wW]eb[sS]ocket-[kK]ey[\s]*:[\s]*(.*)\r\n', message)
        if key:
            key = key.group(1)
        else:
            DEBUG and print("Client tried to connect but was missing a key")
            self.keep_alive = False
            return
        response = self.make_handshake_response(key)
        self.handshake_done = self.request.send(response.encode())
        self.valid_client = True
        self.server._new_client(self)
        
    def make_handshake_response(self, key):
        return \
          'HTTP/1.1 101 Switching Protocols\r\n'\
          'Upgrade: websocket\r\n'              \
          'Connection: Upgrade\r\n'             \
          'Sec-WebSocket-Accept: %s\r\n'        \
          '\r\n' % self.calculate_response_key(key)
    
    def read_message(self):
        b1, b2 = self.rfile.read(2)

        fin    = b1 & FIN
        opcode = b1 & OPCODE
        masked = b2 & MASKED
        payload_length = b2 & PAYLOAD_LEN

        if opcode == CLOSE_CONN:
            DEBUG and print("Client asked to close connection.")
            self.keep_alive = 0
            return
        if not masked:
            DEBUG and print("Client must always be masked.")
            self.keep_alive = 0
            return

        if payload_length == 126:
            payload_length = struct.unpack(">H", self.rfile.read(2))[0]
        elif payload_length == 127:
            payload_length = struct.unpack(">Q", self.rfile.read(8))[0]
        
        masks = self.rfile.read(4)
        payload = self.rfile.read(payload_length)

        payload_int = int.from_bytes(payload, sys.byteorder)
        masks_int = int.from_bytes(masks * (payload_length//4) + masks[:payload_length%4], sys.byteorder)
        decoded = (payload_int ^ masks_int).to_bytes(payload_length, sys.byteorder)
        self.bytes_buffer += decoded

        if fin == FIN:
            self.server._message_received(self, self.bytes_buffer)
            self.bytes_buffer = bytearray()

    def send_message(self, message):
        if isinstance(message, bytes):
            payload = message
        elif isinstance(message, str):
            payload = message.encode('UTF-8')
        else:
            DEBUG and print('Message has to be a string or bytes. Given type is %s' % type(message))
            return False

        header  = bytearray()
        payload_length = len(payload)

        # Normal payload
        if payload_length <= 125:
            header.append(FIN | OPCODE_TEXT)
            header.append(payload_length)
        # Extended payload
        elif payload_length >= 126 and payload_length <= 65535:
            header.append(FIN | OPCODE_TEXT)
            header.append(PAYLOAD_LEN_EXT16)
            header.extend(struct.pack(">H", payload_length))
        # Huge extended payload
        elif payload_length < 18446744073709551616:
            header.append(FIN | OPCODE_TEXT)
            header.append(PAYLOAD_LEN_EXT64)
            header.extend(struct.pack(">Q", payload_length))
        else:
            raise Exception("Message too big. Consider breaking it into chunks.")
            return

        self.request.send(header + payload)
        
    def calculate_response_key(self, key):
        GUID = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'
        hash = sha1(key.encode() + GUID.encode())
        response_key = b64encode(hash.digest()).strip()
        return response_key.decode('ASCII')

    def close(self):
        if not self.finished:
            self.finished = True
            StreamRequestHandler.finish(self)

        
