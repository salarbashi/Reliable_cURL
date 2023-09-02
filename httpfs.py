import argparse
import socket
import threading
from datetime import datetime
from babel.dates import format_datetime
import os
import pathlib
from ReliableServer import ReliableServer

# command line arguments
parser = argparse.ArgumentParser(description='Implements HTTP get/post request')
# optional arguments
parser.add_argument('-p', '--port', type=int, help='Port')
parser.add_argument('-d', '--dir', type=str, help='Directory path')
# mutually exclusive argument
group = parser.add_mutually_exclusive_group()
group.add_argument('-v', action='store_true', help='Verbose')
args = parser.parse_args()


def Run_TCP_listener(port):
    reliserver = ReliableServer(port, 3)
    reliserver.RunServer(HTTP_file_handler)


def ParseRequest(request):
    lines = request.splitlines()
    firstLineParts = lines[0].split(" ")
    requestLine = lines[0]
    type = firstLineParts[0]
    path = firstLineParts[1]
    httpVersion = firstLineParts[2]
    header = request.split("\r\n\r\n")[0].splitlines()[1:]
    # check if it does not have a body in response
    body = request.split("\r\n\r\n")[1] if len(request.split("\r\n\r\n")) > 1 else None
    responseDict = {'RequestLine': requestLine, 'HTTPVersion': httpVersion, 'Type': type, 'Path': path,
                    'Header': header, 'Body': body}
    return responseDict


def ParseHeaderListtoDict(headerList):
    dict = {}
    try:
        for item in headerList:
            dict[item.split(": ", 1)[0]] = item.split(": ", 1)[1]

        return dict
    except Exception as e:
        print(e)


def HTTPDateTime():
    now = datetime.utcnow()
    format = 'EEE, dd LLL yyyy hh:mm:ss'
    return format_datetime(now, format, locale='en') + ' GMT'


def Transfer(socketInstance: ReliableServer, data):
    socketInstance.Transfer(data)


def SendUnauthorized(socketInstance):
    response = 'HTTP/1.0 403 Forbidden\r\nDate:' + HTTPDateTime() + '\r\n\r\n'
    if args.v:
        print("\n****Sent Response:****\n" + response)
    Transfer(socketInstance, response)


def SendOkResponse(socketInstance, body=None, header=None):
    response = 'HTTP/1.0 200 OK\r\n'

    if header is not None:
        response += header + '\r\n'
    if body is not None:
        response += '\r\n' + body
    response += '\r\n'

    if args.v:
        print("\n****Sent Response:****\n" + response)

    Transfer(socketInstance, response)


def SendNotFound(socketInstance):
    response = 'HTTP/1.0 404 NotFound\r\n\r\n'
    if args.v:
        print("\n****Sent Response:****\n" + response)
    Transfer(socketInstance, response)


def SendInternalServerError(socketInstance):
    response = 'HTTP/1.0 500 InternalServerError\r\n\r\n'
    if args.v:
        print("\n****Sent Response:****\n" + response)
    Transfer(socketInstance, response)


def FileList2Body(fileList):
    body = ''
    for file in fileList:
        body += file + '\r\n'
    # remove the last \r\n, each \r or \n is just one character in string
    body = body[:-2]
    return body


def GetDirectoryFileList(dir):
    return [f for f in os.listdir(dir) if os.path.isfile(os.path.join(dir, f))]


def ReadFromFile(fileAddress):
    try:
        with open(fileAddress, 'r') as file:
            lines = file.readlines()
            file.close()
            returnText = ''
            for index, item in enumerate(lines):
                returnText += item
                # if it is not the last item in the list
                if index != len(lines) - 1:
                    returnText += '\n'
            return returnText

    except Exception as e:
        print(e)


def WritetoFile(fileAddress, content: str, mode: str = "w"):
    try:
        with open(fileAddress, mode) as file:
            file.write(content)

    except Exception as e:
        print(e)
        raise Exception("WriteError")


def HTTP_file_handler(request, socketInstance):
    if args.v:
        print("\n****Received Request:****\n" + request)

        path = ParseRequest(request)["Path"]
        requestType = ParseRequest(request)["Type"]

        # check if it is requesting a dir other than current dir
        # HTTP 403
        if path.count('/') > 1:
            SendUnauthorized(socketInstance)
            return

        filename = path[1:]
        fileAddress = crntdir + filename

        # GET
        if requestType == 'GET':

            # get for dir list
            if path == '/':
                fileList = GetDirectoryFileList(crntdir)
                SendOkResponse(socketInstance, FileList2Body(fileList))

            # get to download a file
            if path[0] == '/':
                # check if file exists
                if pathlib.Path(fileAddress).is_file():
                    fileData = ReadFromFile(fileAddress)
                    header = 'Content-Type: text/html; charset=utf-8\r\nContent-Length: ' + str(len(fileData))
                    body = fileData
                    SendOkResponse(socketInstance, body, header)
                else:
                    SendNotFound(socketInstance)

        elif requestType == 'POST':
            fileData = ParseRequest(request)["Body"]
            try:
                WritetoFile(fileAddress, fileData)
                SendOkResponse(socketInstance)
            except:
                SendInternalServerError(socketInstance)


# Main

# if user has not entered dir, set it to default
crntdir = os.path.dirname(os.path.abspath(__file__)) + '\\htdocs\\' if args.dir is None else args.dir
# check port, default: 80
port = args.port if args.port is not None else 80

# Run server
Run_TCP_listener(port)
