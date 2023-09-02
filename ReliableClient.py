##pakcet types: 0-> data, 1-> SYN, 2-> SYNACK, 3-> Ack, 4-> FIN, 5-> FINACK##
from collections import OrderedDict
import math
import threading
import time
import ipaddress

from packet import Packet
import socket


class ReliableClient:

    def __init__(self, routerAddress, routerPort, peerAddress, peerPort, segmentSize, timeoutInterval=0.05):
        self.connection = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.routerAddress = routerAddress
        self.routerPort = routerPort
        self.peerAddress = ipaddress.ip_address(socket.gethostbyname(peerAddress))
        self.peerPort = peerPort
        self.segmentSize = segmentSize
        self.timeoutInterval = timeoutInterval
        self.sendBase = 0
        self.receivedData = OrderedDict()
        self.FINACK = False
        self.connectionTerminated = False

    def ConnectionSetTimeout(self, timeout):
        self.connection.settimeout(timeout)

    def CancellConnectionTimeout(self):
        self.connection.settimeout(None)

    def SingleSend(self, packetType, seq_num, data):
        p = Packet(packet_type=packetType,
                   seq_num=seq_num,
                   peer_ip_addr=self.peerAddress,
                   peer_port=self.peerPort,
                   payload=data)
        try:
            self.connection.sendto(p.to_bytes(), (self.routerAddress, self.routerPort))
            # print('sent type:', p.packet_type)
        except Exception as e:
            print(e)

    def SingleReceive(self):
        response, sender = self.connection.recvfrom(1024)
        p = Packet.from_bytes(response)
        return p

    def Handshake(self):
        try:
            print("sending SYN...")
            self.ConnectionSetTimeout(0.5)
            self.SingleSend(1, 0, ''.encode())

            print("waiting for SYNACK...")
            response = self.SingleReceive()
            self.CancellConnectionTimeout()

            if response.packet_type == 2:
                print('SYNACK received! Sending SYNACK ...')
                self.SingleSend(2, 0, ''.encode())
                return True
            else:
                return False

        except socket.timeout:
            return False

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
        self.connectionTerminated = False
        self.FINACK = False

    def RetrieveReceivedData(self):
        # wait for connection termination
        while not self.connectionTerminated:
            time.sleep(self.timeoutInterval)
            pass

        self.receivedData = OrderedDict(sorted(self.receivedData.items()))
        receivedData = b''.join(self.receivedData.values())
        print('received data is: ', receivedData.decode())
        return receivedData.decode()

    def TerminateConnection(self):
        while not self.FINACK:
            # send FIN
            self.SingleSend(4, self.sendBase, ''.encode())
            time.sleep(self.timeoutInterval)

    def Transfer(self, data):
        segmentsPayload, nofSegments = self.Segment(data)

        successfulHandshake = False
        while not successfulHandshake:
            successfulHandshake = self.Handshake()
            if successfulHandshake:
                print("Successful handshake!")
            else:
                print("Unsuccessful handshake")

        self.InitializeConnectionVariables()
        threading.Thread(target=self.ReceptionHandler, args=(self.connection,)).start()
        # send upon the reception of the data from application layer
        for i in range(nofSegments):
            self.SingleSend(0, i, segmentsPayload[i])

        # resend unacknowledged packets
        time.sleep(self.timeoutInterval)
        while self.sendBase < nofSegments:
            self.SingleSend(0, self.sendBase, segmentsPayload[self.sendBase])
            time.sleep(self.timeoutInterval)

        # connection termination by sending FIN
        print("Sent request to the server. Sending FIN...")
        self.TerminateConnection()

        receivedData = self.RetrieveReceivedData()
        print("TIME WAIT state")
        return receivedData

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

    def ReceptionHandler(self, connection):
        while True:
            try:
                response, sender = connection.recvfrom(1024)
                packet = Packet.from_bytes(response)
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
                    self.connectionTerminated = True
                    # send FINACK
                    self.SingleSend(5, self.GetAckNumber(), ''.encode())

                # FINACK
                elif packet.packet_type == 5:
                    print('Received FINACK! -> FIN wait 2 state')
                    self.FINACK = True

            except Exception as e:
                print(e)


# reliclinet = ReliableClient('localhost', 3000, 'localhost', 8007, 3)
# received = reliclinet.Transfer('hello ahmed I am Mohamed!')
# print("End")
