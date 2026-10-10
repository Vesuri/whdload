#!/usr/bin/env python3
"""Regression checks for fragmented requests and short debugger-pipe writes."""
import socket
import threading
from types import SimpleNamespace
import unittest
from powerdrome import Gdb, SENT, receive_request

class TransportTests(unittest.TestCase):
    def test_fragmented_large_request(self):
        request='gdb '+('printf "ääää"\n'*40000)
        payload=request.encode()
        client,server=socket.socketpair()
        replies=[]
        def send():
            with client:
                for start in range(0,len(payload),137):
                    client.sendall(payload[start:start+137])
                client.shutdown(socket.SHUT_WR)
                replies.append(client.recv(16))
        sender=threading.Thread(target=send)
        sender.start()
        with server:
            self.assertEqual(receive_request(server),request.strip())
            server.sendall(b'ok')
        sender.join(timeout=5)
        self.assertFalse(sender.is_alive())
        self.assertEqual(replies,[b'ok'])

    def test_partial_pipe_writes_include_terminator(self):
        class PartialWriter:
            def __init__(self): self.data=bytearray()
            def write(self,data):
                count=min(13,len(data))
                self.data.extend(data[:count])
                return count
        writer=PartialWriter()
        debugger=Gdb.__new__(Gdb)
        debugger.p=SimpleNamespace(stdin=writer)
        debugger.read_until=lambda token,timeout: 'done'
        command='print $pc\n'*10000
        self.assertEqual(debugger.cmd(command),'done')
        self.assertEqual(bytes(writer.data),(command+f'\necho {SENT}\\n\n').encode())

if __name__=='__main__': unittest.main()
