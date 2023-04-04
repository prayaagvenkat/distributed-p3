import asyncio
import socket 
import re
import action
import pickle
import os
import atexit
from datetime import datetime as dt
import sys

DATA_FILE = 'usernames.pickle'
STABLE_THRESHOLD = 2
STABLE_POLL_TIME = 0.2
VALID_ACTIONS = ['create', 'connect', 'delete', 'list', 'send']

# data
class User:
    def __init__(self, name: str):
        self._name = name
        self._messages = []
        self._connection = None

    async def connect(self, loop, sock: socket):
        self._connection = sock

        # flush stored messages
        for message in self._messages:
            await self.send_message(loop, message)

    def disconnect(self):
        self._connection = None
    
    # check if user is online
    def status(self):
        return self._connection != None

    async def send_message(self, loop, text: str):
        if self.status():
           await loop.sock_sendall(self._connection, action.encode_message(action.STRING, [text]))
        else:
            self._messages.append(text)

    
class ChatStore:
    def __init__(self, users):
        # key: user name str
        # value: User class
        self._users = {}
        self._pending_messages = asyncio.Queue()

        for user in users:
            self.create_user(user)

    # create a new user
    def create_user(self, name: str):
        self._users[name] = User(name)

    def delete_user(self, name: str):
        del self._users[name]

    def list_users(self, pattern: str = '*'):
        return list(filter(lambda user_name: re.search(pattern, user_name), self._users.keys()))

    # set whether a user is online
    async def connect(self, name: str, loop, sock):
        if name in self._users:
            await self._users[name].connect(loop, sock)
            return True
        else:
            return False

    def disconnect(self, name: str):
        if name in self._users:
            self._users[name].disconnect()
            return True
        else:
            return False

    async def create_request(self, action_name: str, timestamp, data, connection) -> bool:
        await self._pending_messages.put((action_name, timestamp, data, connection))

    async def process_requests(self, loop):
        while True:
            (action_name, timestamp, data, connection) = await self._pending_messages.get()

            if (dt.now() - timestamp).total_seconds() >= STABLE_THRESHOLD:
                try:
                    name = ''
                    print("ACTION: ", action_name)
                    resp = None

                    if(action_name == "create"):
                        user = data[0]
                        self.create_user(user)
                        resp = action.encode_message(action.OK, [])
                    elif(action_name == 'connect'):
                        name = data[0]
                        status = action.OK if await self.connect(name, loop, connection) else action.NOTOK
                        resp = action.encode_message(status, [])
                    elif(action_name == 'delete'):
                        user = data[0]
                        self.delete_user(user)
                        if user == name:
                            name = ''
                        resp = action.encode_message(action.OK, [])
                    elif(action_name == 'list'):
                        pattern = data[0] if len(data) >= 1 else None
                        users = self.list_users(pattern)
                        resp = action.encode_message(action.LIST, users)
                    elif(action_name == 'send'):
                        
                        
                        [name, text] = data
                        print('hi')
                        await self._users[name].send_message(loop, text)
                        print('ho')
                    else:
                        resp = action.encode_message(action.NOTOK, [])

                    if resp:
                        await loop.sock_sendall(connection, resp)



                except Exception as ex:
                    print(ex)
                finally:
                    self.disconnect(name)
                    connection.close()

            else: 
                await self._pending_messages.put((action_name, timestamp, data, connection))
            
            self._pending_messages.task_done()

async def receive(store: ChatStore, connection: socket,
            loop: asyncio.AbstractEventLoop) -> None:
    try:
        while header_bytes := await loop.sock_recv(connection, action.BODY_SIZE):
            content_bytes = await loop.sock_recv(connection, int.from_bytes(header_bytes, byteorder='big'))
            [action_name, timestamp, data] = action.decode_message(content_bytes)
            await loop.sock_sendall(connection, action.encode_message(action.RECV, []))
            await store.create_request(action_name, timestamp, data, connection)

    except Exception as ex:
        print(ex)


async def listen(store: ChatStore, server_socket: socket,
                                loop: asyncio.AbstractEventLoop):
    
    asyncio.create_task(store.process_requests(loop))

    while True:
        print('hello')
        connection, address = await loop.sock_accept(server_socket)
        connection.setblocking(False)
        print(f"Got a connection from {address}")
        asyncio.create_task(receive(store, connection, loop))


def save_data(store: ChatStore):
    print('Saving server state...')
    with open(DATA_FILE, 'wb') as handle:
        pickle.dump(list(store._users.keys()), handle, protocol=pickle.HIGHEST_PROTOCOL)


def load_data():
    try:
        with open(DATA_FILE, 'rb') as handle:
            return pickle.load(handle)
    except:
        return []


async def main():
    # init store with saved data
    usernames = load_data()
    print(usernames)
    store = ChatStore(users=usernames)

    port = int(sys.argv[1])
    
    # save data on exit
    atexit.register(save_data, store)

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_address = ('localhost', port)
    print("Server address " + str(server_address))
    server_socket.setblocking(False)
    server_socket.bind(server_address)
    server_socket.listen()


    await listen(store, server_socket, asyncio.get_event_loop())

asyncio.run(main())