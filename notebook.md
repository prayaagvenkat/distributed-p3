# Design Notebook

## Replication strategy

Our replication strategy follows the section ''Synchronized Real-Time Clocks'' in ''Replication Management using the State Machine Approach'' by Fred B. Schneider (available on Canvas) at a high-level. Essentially, we make use of the assumption that different machines in our system have approximately synchronized real time clocks. In order to achieve 2-fault tolerance against crash/failstop failures, we maintain 3 replicas of the server as follows:

- Each replica is itself persistent (see section below).
- Each client sends a given request to all servers. The client attaches its local clock time to this message.
- Each replica processes client requests in the following way:
    - Requests are added to a queue upon receipt by server.
    - To decide which request to process next, the server processes the *stable* request with the earliest timestamp.
    - A request is considered *stable* if the local time on the server exceeds the timestamp on the message by at least 1 second. 
    - Note: If no stable requests are available, the server will just wait (up to at most 1 second).
    - The choice of 1 second delay is somewhat arbitrary. The only constraint on the delay is that it should exceed the time it takes to send a message between any client-server pair. Empirically, we found 1 second satisfies this constraint while not significantly compromising performance of the system.
- Each client will receive responses from (up to) 3 replicas. For the purposes of demonstration, we print all the reponses received. However, in a practical implementation, a client can just print one of the responses (e.g. the first one received).

This replication strategy ensures the following correctness properties are satisfied:
1. All replicas are in agreement about the order of requests and will deliver identical responses to clients.
2. The system is 2-fault tolerant. If any 2 replicas experience failures, the remaining replica can carry out the server functionality unaffected.
3. Every replica processes requests from a single client in the correct order (i.e. order that they were sent by the client).
4. Every replica processes requests from multiple client in the correct order (i.e. order that they were originally sent by the multiple clients).

### Advantages

- This strategy is straightforward to implement and relies on a concrete assumption whose validity can be assessed easily beforehand. This also makes testing and debugging easier. Overall, the complexity of code is not significantly more than the original version in Design Exercise 1.
- Relatively little communication overhead is required to achieve fault tolerance. To send a message in a system with N replicas, a client sends N replicas of the mssage. No communication between replicas of the server is required.
- The strategy can be easily scaled to achieve N-fault tolerance, for arbitrary N (not just N = 3).
- The strategy does satisfy fault tolerance (as proven formally by Schneider).

### Disadvantages

- We rely on approximate clock synchronization of machines. In our setting, this is indeed the case, but is not always true in general.
- Servers may lag behind client by up to 1 second. There are more complicated strategies to mitigate this issue, but we did not implement them because we felt that the lag did not impact performance significantly.

## Persistence

## General design choices

- One of the main design choices we made was to use the python module ''asyncio''. This allows us to execute the server actions concurrently without explicitly managing threads. This makes our code easier to check and avoid common bugs arising from trying to explicitly manage threads.
- For the wire protocol, we chose the simplest specification that allowed us to correctly implement the necessary functionality. Our protocol permits encoding of appropriately-formatted string data corresponding as a sequence of bytes that can be communicated over a socket.
- We highlight our usage of Python's ``select()'' utility. This allows us to monitor, from the client-side, for a socket corresponding to the server. It allows for the client to wait for asynchronous communication from the server.
- For our design, we implemented two classes "User" and "ChatStore". These are just data structures we use to collect information about users. The server maintains a "ChatStore" object that is updated based on commands it receives from clients.

