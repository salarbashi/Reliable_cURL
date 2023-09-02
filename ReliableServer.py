##pakcet types: 0-> data, 1-> SYN, 2-> SYNACK, 3-> Ack, 4-> FIN, 5-> FINACK##
import socket
import time
from collections import OrderedDict
from packet import Packet
import ipaddress
import math
import threading


class ReliableServer:
    def __init__(self, serverport, segmentSize, timeoutInterval=0.05):
        self.connection = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sender = None
        self.serverPort = serverport
        self.peerAddress = ''
        self.peerPort = 0
        self.segmentSize = segmentSize
        self.timeoutInterval = timeoutInterval
        self.sendBase = 0
        self.receivedData = OrderedDict()
        self.peerTerminatedConnection = False
        self.FINACK = False

    def RunServer(self, serverHandler):
        try:
            self.connection.bind(('', self.serverPort))
            print("Server is listening at port: ", self.serverPort)
            threading.Thread(target=self.ReceptionHandler, args=(self.connection, serverHandler)).start()
        except Exception as e:
            print(e)

    # segmentation
    def Segment(self, data):
        dataBytes = data.encode()
        segments = OrderedDict()

        if len(dataBytes) < self.segmentSize:
            segments[0] = dataBytes
        else:
            nofSegments = math.ceil(len(dataBytes) / self.segmentSize)

            for i in range(nofSegments):
                firstIndex = self.segmentSize * i
                lastIndex = firstIndex + self.segmentSize - 1
                # +1 after lastIndex is to include up to the lastIndex th item
                segments[i] = dataBytes[firstIndex:lastIndex + 1]

        return segments, nofSegments

    def InitializeConnectionVariables(self):
        self.sendBase = 0
        self.receivedData.clear()
        self.peerTerminatedConnection = False
        self.FINACK = False

    def TerminateConnection(self):
        while not self.FINACK:
            self.SingleSend(4, self.sendBase, ''.encode())
            time.sleep(self.timeoutInterval)

    def Transfer(self, data):
        segmentsPayload, nofSegments = self.Segment(data)

        print("Sending response to the client...")

        # send response to the client
        for i in range(nofSegments):
            self.SingleSend(0, i, segmentsPayload[i])

        # resend unacknowledged packets
        time.sleep(self.timeoutInterval)
        while self.sendBase < nofSegments:
            self.SingleSend(0, self.sendBase, segmentsPayload[self.sendBase])
            time.sleep(self.timeoutInterval)

        # connection termination by sending FIN
        self.TerminateConnection()
        print("Sent Response to the client!")

    def RetrieveReceivedData(self):
        self.receivedData = OrderedDict(sorted(self.receivedData.items()))
        receivedData = b''.join(self.receivedData.values())
        return receivedData.decode()

    def SingleSend(self, packetType, seq_num, data):
        p = Packet(packet_type=packetType,
                   seq_num=seq_num,
                   peer_ip_addr=self.peerAddress,
                   peer_port=self.peerPort,
                   payload=data)
        self.connection.sendto(p.to_bytes(), self.sender)
        # print('sent type:', p.packet_type)

    def GetAckNumber(self):
        orderedData = OrderedDict(sorted(self.receivedData.items()))
        expected = 0
        for i in range(len(orderedData)):
            if i in orderedData:
                expected += 1
            else:
                break
        return expected

    def SendAck(self):
        expected = self.GetAckNumber()
        self.SingleSend(3, expected, ''.encode())

    def ReceptionHandler(self, connection, serverHandler):
        while True:
            try:
                response, self.sender = connection.recvfrom(1024)
                packet = Packet.from_bytes(response)
                self.peerPort = packet.peer_port
                self.peerAddress = packet.peer_ip_addr
                # print('received type:', packet.packet_type)

                # ACK
                if packet.packet_type == 3:
                    if packet.seq_num > self.sendBase:
                        self.sendBase = packet.seq_num

                # data
                elif packet.packet_type == 0:
                    self.receivedData[packet.seq_num] = packet.payload
                    self.SendAck()

                # FIN
                elif packet.packet_type == 4:
                    # send FINACK
                    self.SingleSend(5, self.GetAckNumber(), ''.encode())

                    # do it only on first FIN reception
                    if not self.peerTerminatedConnection:
                        print("Client data received!")
                        threading.Thread(target=serverHandler, args=(self.RetrieveReceivedData(), self)).start()
                    self.peerTerminatedConnection = True


                # SYN
                elif packet.packet_type == 1:
                    self.InitializeConnectionVariables()
                    print('SYN received! Sending SYNACK ...')
                    self.SingleSend(2, 0, ''.encode())

                # FINACK
                elif packet.packet_type == 5:
                    self.FINACK = True

            except Exception as e:
                print(e)


# def ServerHandler(data, socketInstance):
#     print('received data is: ', data)
#     socketInstance.Transfer('Hi mohamed! This is the Server.')
#
#
# reliserver = ReliableServer(8007, 3)
# reliserver.RunServer(ServerHandler)
