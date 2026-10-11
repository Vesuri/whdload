#!/usr/bin/env python3
"""Regression checks for fragmented requests and short debugger-pipe writes."""
import socket
import threading
from types import SimpleNamespace
import unittest
from powerdrome import Gdb, SENT, receive_request, send_request

class TransportTests(unittest.TestCase):
    def test_fragmented_large_request(self):
        request='gdb '+('printf "ääää"\n'*40000)
        body=request.encode()
        payload=f'PD1 {len(body)}\n'.encode()+body
        client,server=socket.socketpair()
        replies=[]
        def send():
            with client:
                for start in range(0,len(payload),137):
                    client.sendall(payload[start:start+137])
                replies.append(client.recv(16))
        sender=threading.Thread(target=send)
        sender.start()
        with server:
            self.assertEqual(receive_request(server),request.strip())
            server.sendall(b'ok')
        sender.join(timeout=5)
        self.assertFalse(sender.is_alive())
        self.assertEqual(replies,[b'ok'])

    def test_named_socket_multiple_open_requests(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory(dir='tmp') as directory:
            address=str(Path(directory)/'transport.sock')
            with socket.socket(socket.AF_UNIX) as listener:
                listener.bind(address);listener.listen(1)
                requests=['gdb '+('print $pc\n'*n) for n in (20000,30000,25000)]
                received=[]
                def server():
                    for _ in requests:
                        connection,_=listener.accept()
                        with connection:
                            connection.settimeout(5)
                            received.append(receive_request(connection))
                            connection.sendall(b'ok')
                worker=threading.Thread(target=server)
                worker.start()
                for request in requests:
                    with socket.socket(socket.AF_UNIX) as client:
                        client.settimeout(5);client.connect(address)
                        send_request(client,request)
                        self.assertEqual(client.recv(16),b'ok')
                worker.join(timeout=5)
                self.assertFalse(worker.is_alive())
                self.assertEqual(received,[request.strip() for request in requests])

    def test_truncated_payload(self):
        client,server=socket.socketpair()
        with client,server:
            client.sendall(b'PD1 100\nshort')
            client.shutdown(socket.SHUT_WR)
            with self.assertRaises(EOFError): receive_request(server)

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
        debugger.sent=SENT
        debugger.read_until=lambda token,timeout: 'done'
        command='print $pc\n'*10000
        self.assertEqual(debugger.cmd(command),'done')
        self.assertEqual(bytes(writer.data),(command+f'\necho {SENT}\\n\n').encode())

if __name__=='__main__': unittest.main()
