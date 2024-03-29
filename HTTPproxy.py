# Place your imports here.
import signal
from socket import *
from optparse import OptionParser
import sys
from threading import *
from time import *
from urllib.parse import urlparse

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

# Set up listening socket for incoming connections
listening_socket = socket(AF_INET, SOCK_STREAM)
listening_socket.bind((address, port))
listening_socket.listen()
listening_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)

# Signal handler for pressing ctrl-c
def ctrl_c_pressed(signal, frame):
	sys.exit(0)

# Set up signal handling (ctrl-c)
signal.signal(signal.SIGINT, ctrl_c_pressed)

# Receives data from client and parses it to check that it is a valid request.
# Sets up the server socket and sends the client request, then listens for 
# the reply and sends it back to the client.
def handle_client(client_socket, client_addr):
    cache = {}
    blocklist = {}
    cached_enabled = False
    blocklist_enabled = False
    
    # Receive request from client
    request = b''
    while True:
        request += client_socket.recv(4096)
        if request.endswith(b'\r\n\r\n'):
            break

    # DELETE LATER
    print('-----------------------------------\r\n' + 
          'THIS IS THE ORIGINAL REQUEST:\r\n' + 
          request.decode('utf-8') + '\r\n' +
          '-----------------------------------')
    
    if (b'cache/enable' in request):
        cached_enabled = True
        client_socket.sendall(b'HTTP/1.0 200 OK')
        return

    if (b'cache/disable' in request):
        cached_enabled = False
        client_socket.sendall(b'HTTP/1.0 200 OK')
        return
    
    if (b'cache/flush' in request):
        cache.clear()
        client_socket.sendall(b'HTTP/1.0 200 OK')
        return

    if (b'blocklist/enable' in request):
        blocklist_enabled = True
        client_socket.sendall(b'HTTP/1.0 200 OK')
        return

    if (b'blocklist/disable' in request):
        blocklist_enabled = False
        client_socket.sendall(b'HTTP/1.0 200 OK')
        return
    
    if (b'blocklist/flush' in request):
        blocklist.clear()
        client_socket.sendall(b'HTTP/1.0 200 OK')
        return
    
    if (b'blocklist/add/' in request):
        start = request.decode('utf-8').find('add/') + 4
        end = request.decode('utf-8').find(' HTTP/1.0')
        substring = request.decode('utf-8')[start:end]
        blocklist.add(substring)
        client_socket.sendall(b'HTTP/1.0 200 OK')
        return
    
    if (b'blocklist/remove/' in request):
        start = request.decode('utf-8').find('remove/') + 7
        end = request.decode('utf-8').find(' HTTP/1.0')
        substring = request.decode('utf-8')[start:end]
        blocklist.remove(substring)
        client_socket.sendall(b'HTTP/1.0 200 OK')
        return
    
    # Parse request
    parsed_request, server_addr, server_port = parse_request(request.decode('utf-8'))

    if (blocklist_enabled):
        for domain in blocklist:
            if domain in parsed_request:
                client_socket.sendall(b'HTTP/1.0 403 Forbidden\r\n\r\n')
                client_socket.close()
                return

    if ('501 Not Implemented\r\n\r\n' in parsed_request or '400 Bad Request\r\n\r\n' in parsed_request):
        client_socket.sendall(parsed_request.encode('utf-8'))
        client_socket.close()
        return

    # Set up server socket
    server_socket = socket(AF_INET, SOCK_STREAM)
    server_socket.connect((gethostbyname(server_addr), server_port))

    if (cached_enabled):
        # Check if the object is in the cache
        if (parsed_request in cache):
            # Verify it's up to date.
            parsed_request += (parsed_request[0:len(parsed_request) - 4] +
                               'If-Modified-Since: ' + cache[parsed_request][1]
                               + '\r\n\r\n')
            reply = b''
            server_socket.sendall(parsed_request.encode('utf-8'))
            while True:
                temp = server_socket.recv(4096)
                if (temp == b''):
                    break
                reply += temp
            string_reply = reply.decode('utf-8')
            string_reply = string_reply.replace('HTTP/1.1', 'HTTP/1.0')
            string_reply += '\r\n\r\n'
            reply = string_reply.encode('utf-8')

            # Cache has the most recent version of object
            if (b'304 Not Modified' in reply):
                client_socket.sendall(cache[parsed_request][0])

            # Server's reply contains the most recent version
            else:
                if (b'200 OK' in reply):
                    start = string_reply.find('Date: ')
                    end = string_reply.find('\r\n', start)
                    date = string_reply[start + 6:end]
                    cache[parsed_request] = (reply, date)
                client_socket.sendall(reply)

        # Object is not in cache
        else:
            reply = b''
            server_socket.sendall(parsed_request.encode('utf-8'))
            while True:
                temp = server_socket.recv(4096)
                if (temp == b''):
                    break
                reply += temp
            string_reply = reply.decode('utf-8')
            string_reply = string_reply.replace('HTTP/1.1', 'HTTP/1.0')
            string_reply += '\r\n\r\n'
            reply = string_reply.encode('utf-8')

            if (b'200 OK' in reply):
                start = string_reply.find('Date: ')
                end = string_reply.find('\r\n', start)
                date = string_reply[start + 6:end]
                cache[parsed_request] = (reply, date)
            client_socket.sendall(reply)
    
    # Cache is disabled
    else:
        # Fetch data from server
        reply = b''
        server_socket.sendall(parsed_request.encode('utf-8'))
        while True:
            temp = server_socket.recv(4096)
            if (temp == b''):
                break
            reply += temp
        string_reply = reply.decode('utf-8')
        string_reply = string_reply.replace('HTTP/1.1', 'HTTP/1.0')
        string_reply += '\r\n\r\n'
        reply = string_reply.encode('utf-8')

        # DELETE LATER
        print('-----------------------------------\r\n' + 
            'THIS IS THE REPLY SENT BACK:\r\n' + 
            reply.decode('utf-8') + '\r\n' +
            '-----------------------------------')

        # Send response
        client_socket.sendall(reply)

        server_socket.close()
        client_socket.close()

# Checks that the request is properly formatted.
# Returns error messages otherwise.
# '400 Bad Request' for malformed requests or if headers are not properly 
# formatted for parsing.
# '501 Not Implemented' for valid HTTP methods other than GET.
def parse_request(request):
    # GET http://www.google.com:8080 HTTP/1.0
    # GET protocol://domain:port/path HTTP/1.0
        # <METHOD> <URL> <HTTP VERSION>     first header
        # <HEADER NAME>: <HEADER VALUE>     all other headers
    # There must always be '\r\n' between lines and '\r\n\r\n' at the end.
    
    split_request = request.split(' ')
    lines = request.split('\r\n')
    method = split_request[0]
    protocol = urlparse(split_request[1]).scheme
    host = urlparse(split_request[1]).hostname
    netloc = urlparse(split_request[1]).netloc
    path = urlparse(split_request[1]).path
    if (len(split_request) > 2):
        version = split_request[2].strip()
    server_addr = host
    server_port = 80
    bad_headers = False

    # Check if the other headers are in the right format.
    # The last two indeces of the array will be ''
    if (len(lines) > 3):
        for i in range(1, len(lines) - 2):
            index = lines[i].find(': ')
            if (index == -1):
                bad_headers = True

    if (method == 'HEAD' or method == 'POST'):
        return 'HTTP/1.0 501 Not Implemented\r\n\r\n', server_addr, server_port

    if (len(split_request) < 3 or len(lines) < 3 or host == None or netloc == ''
        or protocol != 'http' or method != 'GET' or (len(lines) > 3 and 
        lines[len(lines) - 1] != '' and lines[len(lines) - 2] != '') or bad_headers
        or version != 'HTTP/1.0' or path == ''):
        return 'HTTP/1.0 400 Bad Request\r\n\r\n', server_addr, server_port

    # GET / HTTP/1.0
    # Host: www.google.com
    # Connection: close
    # (Additional client-specified headers, if any.)

    # Check if there is a specified port
    if (urlparse(split_request[1]).port != None):
        server_port = urlparse(split_request[1]).port

    new_request = (method + ' ' + path + ' ' + version + 
                   '\r\nHost: ' + host + 
                   '\r\nConnection: close')

    # Check if there are additional headers and add them to new request.
    # The last two indeces of the array will be ''
    # Add \r\n\r\n at the end and \r\n after every header.
    if (len(lines) > 3):
        for i in range(1, len(lines) - 2):
            if ('Connection: ' in lines[i]):
                continue
            new_request += '\r\n' + lines[i]

    new_request += '\r\n\r\n'

    # DELETE LATER
    print('-----------------------------------\r\n' + 
          'THIS IS THE PARSED REQUEST:\r\n' + 
          new_request + '\r\n' +
          '-----------------------------------')
    print('')
    print('-----------------------------------\r\n' +
          'THESE ARE THE ATTRIBUTES:\r\n' +  
          'Method: ' + method + '\r\n' +
          'Path: ' + path + '\r\n' +
          'Version: ' + version + '\r\n' +
          'Host: ' + host + '\r\n' +
          'Server addr: ' + server_addr + '\r\n' +
          'Server port: ' + str(server_port) + '\r\n' +
          '-----------------------------------')

    return new_request, server_addr, server_port

# Receive loop from client to proxy. This gathers requests that
# will eventually be sent to the origin server.
while True:
    # Wait for an incoming connection
    client_socket, client_addr = listening_socket.accept()

    # Handle each connection in a single thread.
    #handle_client(client_socket, client_addr)

    # Handle each connection in a separate thread.
    Thread(target=handle_client, args=(client_socket, client_addr)).start()