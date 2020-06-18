import json
import threading
import time
import queue
from dispatcher import TaskDispatcher
from tools import WebsocketServer, CONN_CLOSE_EXCEPTION


dataCacheSize = 10
taskQueue = queue.Queue()
taskDispatcher = TaskDispatcher()

# 下载线程
def downloadLoop():
    while True:
        task = taskQueue.get()
        print('Handle: %s' % json.dumps(task, indent=4, ensure_ascii=False, \
            default=lambda x: '<not serializable>'))
        taskDispatcher.dispatch(**task)


# 客户端连接状态
ESTABLISHED = 0
IN_TRANSIT = 1

class VideoDownloadServer(WebsocketServer):

    def new_client(self, client):
        client['status'] = ESTABLISHED

    def message_received(self, client, message):
        if client['status'] == ESTABLISHED:
            task = json.loads(message, encoding='utf-8')
            taskQueue.put(task)
            client['task'] = task

            print('\n\nReceive: %s\n' % json.dumps(task, indent=4, ensure_ascii=False))

            if task['type'] == 'stream':
                client['status'] = IN_TRANSIT
                task['close'] = lambda : self.close(client)
                task['dataQueue'] = queue.Queue(dataCacheSize)

                for i in range(dataCacheSize):
                    task['dataQueue'].put(None)

        elif client['status'] == IN_TRANSIT:
            desc, chunk = message.split(b'\r\n', 1)
            data = json.loads(desc, encoding='utf-8')
            data['chunk'] = chunk
            client['task']['dataQueue'].put(data)

        self.send_message(client, 'success')

    def client_left(self, client):
        if client.get('task') and client['task'].get('type') == 'stream':
            client['task']['dataQueue'].put(CONN_CLOSE_EXCEPTION)

def main(port=18888):
    t = threading.Thread(target=downloadLoop, daemon=True)
    t.start()

    server = VideoDownloadServer(port)

    while True:
        try:
            print("Listening on port %d for clients.." % port)
            server.serve_forever()
        except KeyboardInterrupt:
            if taskDispatcher.task:
                taskDispatcher.shutdown()
            else:
                break

if __name__ == '__main__':
    main()
