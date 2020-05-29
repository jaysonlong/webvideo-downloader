# -*- coding:utf-8 -*-
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import threading
import time
import dispatcher
import bilibiliMultiPart

downloadTasks = []

def downloadLoop():
    while True:
        if len(downloadTasks):
            data = downloadTasks.pop(0)
            print('Receive: %s\n' % json.dumps(data, indent=4))

            try:
                if 'pRange' in data and data['pRange']:
                    bilibiliMultiPart.downloadRangeParts(data['linksurl'], data['fileName'], data['pRange'])
                else:
                    dispatcher.download(data['linksurl'], data['fileName'])
            except Exception as e:
                print(e)
        else:
            time.sleep(0.5)

class MyHandler(BaseHTTPRequestHandler):
    def respond(self, respStr):
        self.send_response_only(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(respStr.encode('utf-8'))

    def do_POST(self):
        contentLength = int(self.headers['Content-Length'])
        postData = self.rfile.read(contentLength).decode('utf-8')
        
        if postData == 'ping':
            self.respond('pong')
        else:
            data = json.loads(postData)
            downloadTasks.append(data)
            self.respond('success.')

def main(port=18888):
    t = threading.Thread(target=downloadLoop)
    t.setDaemon(True)
    t.start()

    print('server running at 127.0.0.1:%d...' % port)

    try:
        server = HTTPServer(('127.0.0.1', port), MyHandler)
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()

if __name__ == '__main__':
    main()