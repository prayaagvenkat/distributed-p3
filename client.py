""" CS 262: Design Exercise 3

Authors: Prayaag Venkat, Hugh Zhang

This code implements a fault-tolerant, persistent chat client application.
"""

import socket
import action
import sys
import select
import os

# Address/port of 3 server replicas.
SERVER_LOCATIONS = [('10.250.33.169', 3000), ('localhost', 3001), ('localhost', 3002)]

# Listen for responses from servers to this client
def listener(s: socket):
    body_size = int.from_bytes(s.recv(action.BODY_SIZE), byteorder='big')
    [resp_name, timestamp, data] = action.decode_message(s.recv(body_size))
    if(resp_name == action.OK):
        print("Action succeeded")
    elif(resp_name == action.NOTOK):
        print('Action failed')
    elif(resp_name == action.ERROR):
        print('Server error')
    else: 
        print("Server: " + ", ".join(data))

# Read inout commands from client and send to servers
def reader(socks, line: str):
    command = line.split()
    action_name = command[0]
    args = command[1:]
    
    if(len(args) > 1):
        args = [args[0], " ".join(args[1:])]

    # Replicate messages by sending to all available servers
    for s in socks:
        s.sendall(action.encode_message(action_name, args))

# Main function
def main():
    hosts = SERVER_LOCATIONS
    sockets = []
    # try connecting to all hosts
    for (host, port) in hosts:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((host, port))
            print(f'Connected to {host}:{port}')
            sockets.append(s)
        except Exception as e:
            print(e)
            continue
    
        
    while True:
        try:
            sockets_list = [sys.stdin, *sockets]

            read_sockets, write_socket, error_socket = select.select(sockets_list,[],[])

            for s in read_sockets:
                if s in sockets:
                    # Server to client response
                    listener(s)
                else:
                    # Client to server command
                    reader(sockets, sys.stdin.readline().rstrip())
        except Exception as e:
            print(e)
            break


main()