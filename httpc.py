import argparse
import socket
from urllib.parse import urlparse
from ReliableClient import ReliableClient

# command line arguments
parser = argparse.ArgumentParser(description='Implements HTTP get/post request')
# positional arguments
parser.add_argument('type', type=str, choices=['get', 'post'], help='type of the request')
parser.add_argument('URL', type=str)
# optional arguments
parser.add_argument('-H', help='HTTP header', action='append')
parser.add_argument('-d', '--inline_data', help='HTTP body')
parser.add_argument('-f', '--file', help='HTTP header from file')
parser.add_argument('-o', help='Write response body to file')
parser.add_argument('-l', type=int, help='Maximum number of redirects')
# mutually exclusive argument
group = parser.add_mutually_exclusive_group()
group.add_argument('-v', action='store_true', help='Verbose')
args = parser.parse_args()


def CreateRequest(type, pathandQuery, hostname, headers, body):
    # get request
    if type == 'get':
        request = "GET " + pathandQuery + " HTTP/1.1r\r\nHost:" + hostname

        # adding header
        if headers is not None:
            for item in headers:
                request += "\r\n" + item

        # ending send data
        request += "\r\n\r\n"

    # post request
    if type == 'post':
        request = "POST " + pathandQuery + " HTTP/1.1\r\nHost:" + hostname

        # adding header
        if headers is not None:
            for item in args.H:
                request += "\r\n" + item

        # two new lines before the body
        request += "\r\n\r\n"

        # adding body from command
        if body:
            request += body + "\r\n\r\n"

    return request


def SendData(hostName, port, data):
    try:
        reliclinet = ReliableClient('localhost', 3000, hostName, port, 3)
        receivedData = reliclinet.Transfer(data)
        return receivedData

    except Exception as e:
        print(e)
    #
    # finally:
    #     mySock.close()


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


def ParseResponse(response):
    lines = response.splitlines()
    firstLineParts = lines[0].split(" ")
    statusLine = lines[0]
    httpVersion = firstLineParts[0]
    code = firstLineParts[1]
    status = firstLineParts[2]
    header = response.split("\r\n\r\n")[0].splitlines()[1:]
    # check if it does not have a body in response
    body = response.split("\r\n\r\n")[1] if len(response.split("\r\n\r\n")) > 1 else None
    responseDict = {'StatusLine': statusLine, 'HTTPVersion': httpVersion, 'Code': code, 'Status': status,
                    'Header': header, 'Body': body}
    return responseDict


def PrintResponse(response):
    responseParameters = ParseResponse(response)
    print("\n****Response:****")
    print("Status Line: " + responseParameters["StatusLine"])
    print("Status: " + responseParameters["Status"])
    print("Code: " + responseParameters["Code"])
    print("Header(s): ")
    print(responseParameters["Header"])
    print("Body: " + responseParameters["Body"]) if responseParameters["Body"] is not None else print(
        "No body received!")

def PrintBody(response):
    print("\n****Response:****")
    print(ParseResponse(response)["Body"])

def ParseHeaderListtoDict(headerList):
    dict = {}
    try:
        for item in headerList:
            dict[item.split(": ", 1)[0]] = item.split(": ", 1)[1]

        return dict
    except Exception as e:
        print(e)


# reformatting the command type
args.type = args.type.lower()

# extracting parts of the link
urlparser = urlparse(args.URL)
hostname = urlparser.hostname
port = urlparser.port
port = 80 if port is None else port
pathandQuery = urlparser.path + ('?' + urlparser.query if urlparser.query else "")

# empty the output file
if args.o:
    WritetoFile(args.o, "")

# verbose
if args.v:
    print("Hostname: " + hostname)
    print("Path and query: " + pathandQuery)
    print("Header(s):")
    print(args.H)

# executing GET command
if args.type == 'get':

    request = CreateRequest(args.type, pathandQuery, hostname, args.H, None)

    # number of redirects
    redirectNum = args.l if args.l else 1

    # i range should have +1 because first loop only counts for the first request not the redirect
    for i in range(redirectNum + 1):
        response = SendData(hostname, port, request)
        responseCode = int(ParseResponse(response)["Code"])

        # verbose
        if args.v:
            print("\n****Full request:****\n" + request)
            PrintResponse(response)
        # only shows the last page after redirects body
        elif not args.v and responseCode == 200:
            PrintBody(response)

        # write response body to file
        if args.o:
            WritetoFile(args.o, ParseResponse(response)["Body"] + "\n", "a")

        # breaking in last redirect or creating new request
        if responseCode != 301 and responseCode != 302:
            break
        else:
            responseHeader = ParseResponse(response)["Header"]
            newPath = ParseHeaderListtoDict(responseHeader)["Location"]
            pathandQuery = newPath + ('?' + urlparser.query if urlparser.query else "")
            request = CreateRequest(args.type, pathandQuery, hostname, args.H, None)


# executing POST command
elif args.type == 'post':

    requestBody = args.inline_data if args.inline_data else ReadFromFile(args.file) if args.file else ""
    request = CreateRequest(args.type, pathandQuery, hostname, args.H, requestBody)

    # number of redirects
    redirectNum = args.l if args.l else 1

    for i in range(redirectNum + 1):
        response = SendData(hostname, port, request)
        responseCode = int(ParseResponse(response)["Code"])

        # verbose
        if args.v:
            print("\n****Full request:****\n" + request)
            PrintResponse(response)
        # only shows the last page after redirects body
        elif not args.v and responseCode == 200:
            PrintBody(response)

        # write response body to file
        if args.o:
            WritetoFile(args.o, ParseResponse(response)["Body"] + "\n", "a")

        # breaking in last redirect or creating new request
        if responseCode != 301 and responseCode != 302:
            break
        else:
            responseHeader = ParseResponse(response)["Header"]
            newPath = ParseHeaderListtoDict(responseHeader)["Location"]
            pathandQuery = newPath + ('?' + urlparser.query if urlparser.query else "")
            request = CreateRequest(args.type, pathandQuery, hostname, args.H, requestBody)

