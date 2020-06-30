# -*- coding:utf-8 -*-
import json
import threading
import queue
from dispatcher import TaskDispatcher
import tools
from tools import WebServer, CLIENT_CLOSE_EXCEPTION


taskDispatcher = TaskDispatcher()
taskQueue = queue.Queue()
dataCacheSize = 10


# 下载线程
def downloadLoop():
    while True:
        task = taskQueue.get()
        print('Handle: %s' % tools.stringify(task))
        taskDispatcher.dispatch(**task)



class DownloadServer(WebServer):
    ESTABLISHED = 0
    IN_TRANSIT = 1

    def do_POST(self, client):
        try:
            body = client.rfile.read(int(client.headers['Content-Length']))
            task = json.loads(body.decode('utf-8'))
            print('\n\nReceive: %s\n' % tools.stringify(task))
            taskQueue.put(task)
            tools.normalResponse(client, "success")
        except Exception as e:
            tools.normalResponse(client, "failed")

    def new_client(self, client):
        client.status = self.ESTABLISHED

    def message_received(self, client, msg):
        try:
            if client.status == self.ESTABLISHED:
                task = json.loads(msg.decode('utf-8'))
                taskQueue.put(task)
                client.task = task
                print('\n\nReceive: %s\n' % tools.stringify(task))

                if task['type'] == 'stream':
                    client.status = self.IN_TRANSIT
                    task['close'] = lambda : self.close(client)
                    task['dataQueue'] = queue.Queue(dataCacheSize)
                    for i in range(dataCacheSize):
                        task['dataQueue'].put(None)

            elif client.status == self.IN_TRANSIT:
                desc, chunk = msg.split(b'\r\n', 1)
                data = json.loads(desc.decode('utf-8'))
                data['chunk'] = chunk
                client.task['dataQueue'].put(data)

            self.send_message(client, 'success')
        except:
            self.send_message(client, 'failed')

    def client_left(self, client):
        if client.task and client.task.get('type') == 'stream':
            client.task['dataQueue'].put(CLIENT_CLOSE_EXCEPTION)

def main(port=18888):
    t = threading.Thread(target=downloadLoop, daemon=True)
    t.start()

    server = DownloadServer(port)

    while True:
        try:
            print("Listening on port %d for clients..." % port)
            server.serve_forever()
        except KeyboardInterrupt:
            if taskDispatcher.task:
                taskDispatcher.shutdown()
            else:
                break

if __name__ == '__main__':
    main()
