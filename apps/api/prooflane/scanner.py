import socket
import struct
import time
from dataclasses import dataclass
from .config import settings

@dataclass(frozen=True)
class Verdict:
    result: str
    engine: str
    duration: float

def receive(sock):
    result = bytearray()
    while len(result) < 8192:
        b = sock.recv(1024)
        if not b: break
        result.extend(b)
        if b'\0' in b or b'\n' in b: break
    return result.decode('utf-8', errors='replace').strip('\0\n')

def scan(data: bytes) -> Verdict:
    s = settings()
    start = time.monotonic()
    with socket.create_connection((s.clamav_host, s.clamav_port), timeout=s.scanner_timeout) as sock:
        sock.sendall(b'zVERSION\0')
        engine = receive(sock)
    if not engine.startswith('ClamAV '): raise RuntimeError('Scanner version unavailable')
    with socket.create_connection((s.clamav_host, s.clamav_port), timeout=s.scanner_timeout) as sock:
        sock.sendall(b'zINSTREAM\0')
        for offset in range(0, len(data), 65536):
            chunk = data[offset:offset+65536]
            sock.sendall(struct.pack('!I', len(chunk)) + chunk)
        sock.sendall(struct.pack('!I', 0))
        answer = receive(sock)
    if answer == 'stream: OK': result = 'CLEAN'
    elif answer.startswith('stream: ') and answer.endswith(' FOUND'): result = 'INFECTED'
    else: raise RuntimeError('Scanner error or resource limit')
    # ClamAV VERSION includes engine / signature-database version / update time.
    return Verdict(result, engine[:255], time.monotonic()-start)
