""" CS 262: Design Exercise 3

Authors: Prayaag Venkat, Hugh Zhang

This code implements a fault-tolerant, persistent chat server application.
"""

import asyncio
import socket 
import re
import action
import pickle
import os
import atexit
from datetime import datetime as dt
import sys

# Save and read state from this file
DATA_FILE = 'usernames.pickle'

# Number of seconds after which message is considered stable
STABLE_THRESHOLD = 2

# Poll time between two machines in system
STABLE_POLL_TIME = 0.2


class User:
    """
    This class represents a User in the chat system.

    Attributes
    ----------
    _name : str
        Name of the user
    _messages : list of str
        Backlog of messages to be delivered to this user
    _connection : socket
        Socket on which this user can receive messages from server
    """

    # Initialize all fields to empty
    def __init__(self, name: str, msgs=[]):
        self._name = name
        self._messages = msgs
        self._connection = None

    # Connect user to socket, to receive messages from server
    async def connect(self, loop, sock: socket):
        self._connection = sock

        # flush stored messages
        for message in self._messages:
            await self.send_message(loop, message)

    # Disconnect user from socket
    def disconnect(self):
        self._connection = None
    

    # check if user is online
    def status(self):
        return self._connection != None

    # Send a message to this user. 
    async def send_message(self, loop, text: str):
        if self.status():
           await loop.sock_sendall(self._connection, action.encode_message(action.STRING, [text]))
        else:
            self._messages.append(text)

    
class ChatStore:
    """
    This class represents a data structure that stores users in the chat system.

    Attributes
    ----------
    _users : dict of {str:User}
        Dictionary of users in the system, indexed by name
    _pending_messages : asyncio.Queue
        Queue of pending messages from clients to server; to be processed.

    """

    # Initialize fields to be empty, create new users
    def __init__(self, data):
        # key: user name str
        # value: User class
        self._users = {}
        self._pending_messages = asyncio.Queue()

        for (user,msgs) in data:
            self.create_user(user,msgs)
        
        

    # create a new user
    def create_user(self, name: str, msgs=[]):
        self._users[name] = User(name,msgs)

    # Delete user
    def delete_user(self, name: str):
        del self._users[name]

    # List all users, with name matching regex pattern
    def list_users(self, pattern: str = '*'):
        return list(filter(lambda user_name: re.search(pattern, user_name), self._users.keys()))

    # set whether a user is online
    async def connect(self, name: str, loop, sock):
        if name in self._users:
            await self._users[name].connect(loop, sock)
            return True
        else:
            return False

    # Disconnect a user
    def disconnect(self, name: str):
        if name in self._users:
            self._users[name].disconnect()
            return True
        else:
            return False

    # Add a request from the client to the queue of pending messages
    async def create_message(self, name: str, timestamp, text: str) -> bool:
        await self._pending_messages.put((name, timestamp, text))

    # Process pending messages
    async def process_messages(self, loop):
        while True:
            (name, timestamp, text) = await self._pending_messages.get()

            if name in self._users:
                # Execute message if it is stable. Else, put it back on Queue.
                if (dt.now() - timestamp).total_seconds() >= STABLE_THRESHOLD:
                    await self._users[name].send_message(loop, text)
                else: 
                    await self._pending_messages.put((name, timestamp, text))
            
            self._pending_messages.task_done()


# Handles client requests
async def reply(store: ChatStore, connection: socket,
            loop: asyncio.AbstractEventLoop) -> None:
    try:
        name = ''
        while header_bytes := await loop.sock_recv(connection, action.BODY_SIZE):
            content_bytes = await loop.sock_recv(connection, int.from_bytes(header_bytes, byteorder='big'))
            [action_name, timestamp, data] = action.decode_message(content_bytes)
            print("ACTION: ", action_name)
            resp = None
            if(action_name == "create"):
                user = data[0]
                store.create_user(user)
                resp = action.encode_message(action.OK, [])
            elif(action_name == 'connect'):
                name = data[0]
                status = action.OK if await store.connect(name, loop, connection) else action.NOTOK
                resp = action.encode_message(status, [])
            elif(action_name == 'delete'):
                user = data[0]
                store.delete_user(user)
                if user == name:
                    name = ''
                resp = action.encode_message(action.OK, [])
            elif(action_name == 'list'):
                pattern = data[0] if len(data) >= 1 else None
                users = store.list_users(pattern)
                resp = action.encode_message(action.LIST, users)
            elif(action_name == 'send'):
                [user, text] = data
                await store.create_message(user, timestamp, text)
            else:
                resp = action.encode_message(action.NOTOK, [])

            if resp:
                await loop.sock_sendall(connection, resp)

    except Exception as ex:
        print(ex)
    finally:
        store.disconnect(name)
        connection.close()

# Listen for client input and process existing/pending messages concurrently
async def listen(store: ChatStore, server_socket: socket,
                                loop: asyncio.AbstractEventLoop):
    
    asyncio.create_task(store.process_messages(loop))

    while True:
        connection, address = await loop.sock_accept(server_socket)
        connection.setblocking(False)
        print(f"Got a connection from {address}")
        asyncio.create_task(reply(store, connection, loop))


# Pickle list of users
def save_data(store: ChatStore):
    print('Saving server state...')
    with open(DATA_FILE, 'wb') as handle:
        data = []
        for name, user in store._users.items():
            data.append((name, user._messages))
        pickle.dump(data, handle)

# Load up pickled list of users
def load_data():
    try:
        with open(DATA_FILE, 'rb') as handle:
            print('Loading store from file')
            data = pickle.load(handle)

            return ChatStore(data)
        
    except:
        return None

# Main function
async def main():
    # init store with saved data
    store = load_data()
    if store:
        print(list(store._users.keys()))
    else:
        print('Starting new store')
        store = ChatStore([])

    # Read port number of host from command line
    port = int(sys.argv[1])
    
    # save data on exit
    atexit.register(save_data, store)

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_address = ('0.0.0.0', port)
    print("Server address " + str(server_address))
    server_socket.setblocking(False)
    server_socket.bind(server_address)
    server_socket.listen()


    await listen(store, server_socket, asyncio.get_event_loop())

asyncio.run(main())