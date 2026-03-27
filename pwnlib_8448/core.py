#!/usr/bin/env python3
from typing import Optional, Union
import socket
import struct
import string
import subprocess
import sys
import os
import pty
import select
import re

# =========================
# COLORS & LOGGER
# =========================
class Colors:
    RESET  = "\033[0m"
    RED    = "\033[31m"
    GREEN  = "\033[32m"
    YELLOW = "\033[33m"
    BLUE   = "\033[34m"
    CYAN   = "\033[36m"
    BOLD   = "\033[1m"

def log_info(msg): print(f"{Colors.BLUE}[INFO]{Colors.RESET} {msg}")
def log_ok(msg):   print(f"{Colors.GREEN}[OK]{Colors.RESET} {msg}")
def log_warn(msg): print(f"{Colors.YELLOW}[WARN]{Colors.RESET} {msg}")
def log_error(msg):print(f"{Colors.RED}[ERROR]{Colors.RESET} {msg}")
def log_send(msg): print(f"{Colors.CYAN}[>>]{Colors.RESET} {msg}")
def log_recv(msg): print(f"{Colors.CYAN}[<<]{Colors.RESET} {msg}")

# =========================
# PACK / UNPACK
# =========================
def p64(x): return struct.pack("<Q", x)
def u64(x): return struct.unpack("<Q", x)[0]

def p32(x): return struct.pack("<I", x)
def u32(x): return struct.unpack("<I", x)[0]

_PATTERN_CACHE = {}

# =========================
# PATTERN CREATE (CYCLIC)
# =========================
def pattern_create(size: int) -> bytes:
    if size in _PATTERN_CACHE:
        return _PATTERN_CACHE[size]
    
    charset = (string.ascii_lowercase +
               string.ascii_uppercase +
               string.digits)
    
    pattern = bytearray()
    
    for a in charset:
        for b in charset:
            for c in charset:
                pattern += bytes([ord(a), ord(b), ord(c)])
                if len(pattern) >= size:
                    result = bytes(pattern[:size])
                    _PATTERN_CACHE[size] = result
                    return result
    
    result = bytes(pattern[:size])
    _PATTERN_CACHE[size] = result
    return result


# =========================
# PATTERN OFFSET (CYCLIC FIND)
# =========================
def pattern_offset(value: Union[int, bytes], 
                   size: int = 10000, 
                   arch: int = 64) -> Optional[int]:
    
    pattern = pattern_create(size)
    
    if isinstance(value, int):
        fmt = "<I" if arch == 32 else "<Q"
        value = struct.pack(fmt, value)
    elif not isinstance(value, bytes):
        raise TypeError(f"value must be int or bytes, received: {type(value)}")    
    window_sizes = [8, 4, 3]  
    
    for window in window_sizes:
        if len(value) >= window:
            for i in range(len(value) - window + 1):
                chunk = value[i:i+window]
                idx = pattern.find(chunk)
                if idx != -1:
                    return idx
    
    if arch == 64 and len(value) >= 8:
        value_le = struct.pack('<Q', struct.unpack('>Q', value[:8])[0])
        idx = pattern.find(value_le)
        if idx != -1:
            return idx
    
    return None



# =========================
# ANSI CLEAN
# =========================
def clean_ansi(data):
    return re.sub(rb'\x1b\[[0-9;]*[a-zA-Z]', b'', data)

# =========================
# REMOTE (SOCKET)
# =========================
class Remote:
    def __init__(self, host, port, timeout=5):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.clean = True

        self.s = socket.socket()
        self.s.settimeout(self.timeout)

        log_info(f"Connecting to {host}:{port} ...")
        try:
            self.s.connect((host, port))
            log_ok("Connection established")
        except socket.timeout:
            log_error("Connection timed out")
            sys.exit(1)
        except socket.error as e:
            log_error(f"Connection failed: {e}")
            sys.exit(1)

    def send(self, data):
        if isinstance(data, str):
            data = data.encode()
        log_send(data)
        try:
            self.s.sendall(data)
        except socket.error as e:
            log_error(f"Send failed: {e}")
            self.close()
            sys.exit(1)

    def sendline(self, data):
        if isinstance(data, str):
            data = data.encode()
        self.send(data + b"\n")

    def recv(self, n=4096):
        try:
            data = self.s.recv(n)
            if not data:
                log_warn("Connection closed by remote")
                return b""
            log_recv(data)
            return data
        except socket.timeout:
            return b""
        except socket.error as e:
            log_error(f"Receive failed: {e}")
            self.close()
            sys.exit(1)

    def recvuntil(self, delim):
        data = b""
        while delim not in data:
            chunk = self.recv(1)
            if not chunk:
                break
            data += chunk
        return data

    def recvline(self):
        return self.recvuntil(b"\n")

    def interactive(self):
        log_info("Interactive (REMOTE)")

        while True:
            try:
                r, _, _ = select.select([self.s, sys.stdin], [], [])

                if self.s in r:
                    data = self.s.recv(4096)
                    if not data:
                        log_warn("Connection closed")
                        break

                    if self.clean:
                        data = clean_ansi(data)

                    sys.stdout.buffer.write(data)
                    sys.stdout.flush()

                if sys.stdin in r:
                    data = os.read(sys.stdin.fileno(), 1024)
                    if not data:
                        break
                    self.s.sendall(data)

            except KeyboardInterrupt:
                log_warn("Exiting interactive")
                break

        self.close()

    def close(self):
        try:
            self.s.close()
            log_info("Connection closed")
        except:
            pass


# =========================
# PROCESS (PTY LOCAL)
# =========================
class Process:
    def __init__(self, path):
        log_info(f"Starting process: {path}")

        binary = path[0] if isinstance(path, list) else path
        if not os.path.exists(binary):
            log_error(f"Binary not found: {binary}")
            sys.exit(1)

        self.master, self.slave = pty.openpty()

        self.p = subprocess.Popen(
            path if isinstance(path, list) else [path],
            stdin=self.slave,
            stdout=self.slave,
            stderr=self.slave,
            preexec_fn=os.setsid,
            close_fds=True
        )

        os.close(self.slave)

        log_ok("Process started (PTY mode)")

    def send(self, data):
        if isinstance(data, str):
            data = data.encode()
        log_send(data)
        try:
            os.write(self.master, data)
        except OSError:
            log_warn("Write failed (process may have exited)")

    def sendline(self, data):
        if isinstance(data, str):
            data = data.encode()
        self.send(data + b"\n")

    def recv(self, n=1024):
        try:
            r, _, _ = select.select([self.master], [], [], 1)
            if r:
                data = os.read(self.master, n)
                if data:
                    log_recv(data)
                return data
            return b""
        except OSError:
            return b""

    def recvuntil(self, delim):
        data = b""
        while delim not in data:
            chunk = self.recv(1)
            if not chunk:
                break
            data += chunk
        return data

    def recvline(self):
        return self.recvuntil(b"\n")

    def interactive(self):
        log_info("Interactive (LOCAL PTY)")

        try:
            os.write(self.master, b"export TERM=dumb\n")
        except:
            pass

        while True:
            try:
                r, _, _ = select.select([self.master, sys.stdin], [], [])

                if self.master in r:
                    try:
                        data = os.read(self.master, 1024)
                        if not data:
                            log_warn("Process exited")
                            break
                        sys.stdout.buffer.write(clean_ansi(data))
                        sys.stdout.flush()
                    except OSError:
                        log_warn("PTY closed")
                        break

                if sys.stdin in r:
                    data = os.read(sys.stdin.fileno(), 1024)
                    if not data:
                        break
                    os.write(self.master, data)

            except KeyboardInterrupt:
                log_warn("Exiting interactive")
                break

        self.close()

    def close(self):
        try:
            self.p.kill()
        except:
            pass

        try:
            os.close(self.master)
        except:
            pass

        log_info("Process closed cleanly")
