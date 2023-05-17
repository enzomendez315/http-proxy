# Place your imports here.
import signal
from socket import *
from optparse import OptionParser
import sys
from threading import *
from time import *
from urllib.parse import urlparse

# Start of program execution
# Parse out the command line server address and port number to listen to
parser = OptionParser()
# Proxy listens for incoming client connections on port number -p
parser.add_option('-p', type='int', dest='serverPort')
# Proxy listens for incoming client connections on network interface -a
parser.add_option('-a', type='string', dest='serverAddress')
(options, args) = parser.parse_args()

port = options.serverPort   # -p
address = options.serverAddress     # -a
if address is None:
    address = 'localhost'
if port is None:
    port = 2100

# FROM ASSIGNMENT: First thing is to establish a socket that the proxy
# can use to listen for incoming connections.

# Set up listening socket for incoming connections
listening_socket = socket(socket.AF_INET, socket.SOCK_STREAM)
listening_socket.bind((address, port))
listening_socket.listen()
listening_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

# FROM ASSIGNMENT: Once a client has connected, the proxy should read data
# from the client and check for a properly formatted HTTP request.
    # <METHOD> <URL> <HTTP VERSION>     first header
    # <HEADER NAME>: <HEADER VALUE>     all other headers
    # There must always be "\r\n" between lines and "\r\n\r\n" at the end.

# Signal handler for pressing ctrl-c
def ctrl_c_pressed(signal, frame):
	sys.exit(0)

# Set up signal handling (ctrl-c)
signal.signal(signal.SIGINT, ctrl_c_pressed)

# FROM ASSIGNMENT: Once the proxy has parsed the URL, it can make a connection
# to the origin server and send the HTTP request for the appropriate object.
    # Accept from client
        # GET http://www.google.com/ HTTP/1.0
    # Send to origin server
        # GET / HTTP/1.0
        # Host: www.google.com
        # Connection: close
        # (Additional client-specified headers, if any.)
        # -----------------------------------
        # http://www.example.com:8080

# Receives data from client and parses it to check that it is a valid request.
# Sets up the server socket and sends the client request, then listens for 
# the reply and sends it back to the client.
def handle_client(client_socket, client_addr):
    # Receive request
    request = client_socket.recv(4096)
    while True:
        temp = client_socket.recv(4096)
        request += temp
        if request.endswith(b'\r\n\r\n'):
            break

    # Parse request
    parsed_request = parse_request(request.decode('utf-8'))

    # Set up server socket
    server_socket = socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.connect(address, port)

    while True:
        # Fetch data from origin
        server_socket.sendall(parsed_request.encode('utf-8'))
        reply = server_socket.recv(4096)

        # Send response
        client_socket.sendall(reply)

        for i in range(10):
            sleep(1)
            print(f'Handling request from client {client_addr}')
        print('Client request handled')
        client_socket.close()

# Checks that the request is properly formatted.
# Returns error messages otherwise.
# “400 Bad Request” for malformed requests or if headers are not properly 
# formatted for parsing.
# "501 Not Implemented” for valid HTTP methods other than GET.
def parse_request(request):
    # GET http://www.google.com/ HTTP/1.0
        # <METHOD> <URL> <HTTP VERSION>     first header
        # <HEADER NAME>: <HEADER VALUE>     all other headers
    # There must always be "\r\n" between lines and "\r\n\r\n" at the end.
    
    split_request = request.split(" ")
    method = split_request[0]
    host = urlparse(split_request[1]).hostname
    version = split_request[2]

    if (method is not "GET"):
        return "501 Not Implemented"

    if (request[-8:None] != "HTTP/1.0"):
        return "400 Bad Request"

    # GET / HTTP/1.0
    # Host: www.google.com
    # Connection: close
    # (Additional client-specified headers, if any.)
    # -----------------------------------
    # http://www.example.com:8080

    new_request = split_request[0] + " / " + version + "\r\nHost: " + host
    + "\r\nConnection: close"

    return new_request

# Receive loop from client to proxy. This gathers requests that
# will eventually be sent to the origin server.
while True:
    # Wait for an incoming connection
    client_socket, client_addr = listening_socket.accept()

    # Handle each connection in a single thread.
    handle_client(client_socket, client_addr)

    # Handle each connection in a separate thread.
    #Thread(target=handle_client, args=(client_socket, client_addr)).start()