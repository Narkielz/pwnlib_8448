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
def log_send(msg): 
    if isinstance(msg, bytes):
        msg = hexdump(msg, simple=True)
    print(f"{Colors.CYAN}[>>]{Colors.RESET} {msg}")
def log_recv(msg):
    if isinstance(msg, bytes):
        msg = hexdump(msg, simple=True)
    print(f"{Colors.CYAN}[<<]{Colors.RESET} {msg}")

# =========================
# HEXDUMP
# =========================
def hexdump(data: bytes, cols: int = 16, simple: bool = False) -> str:
    """Generate hexdump of bytes"""
    if simple:
        # Simple format for logs
        hex_part = ' '.join(f'{b:02x}' for b in data[:32])
        if len(data) > 32:
            hex_part += ' ...'
        ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in data[:32])
        if len(data) > 32:
            ascii_part += '...'
        return f"{hex_part}  |{ascii_part}|"
    
    # Full hexdump format
    result = []
    for i in range(0, len(data), cols):
        chunk = data[i:i+cols]
        hex_part = ' '.join(f'{b:02x}' for b in chunk)
        hex_part = hex_part.ljust(cols * 3)
        ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
        result.append(f"{i:08x}  {hex_part}  |{ascii_part}|")
    
    return '\n'.join(result)

# =========================
# PACK / UNPACK
# =========================
def p64(x): return struct.pack("<Q", x)
def u64(x): return struct.unpack("<Q", x)[0]

def p32(x): return struct.pack("<I", x)
def u32(x): return struct.unpack("<I", x)[0]

def p16(x): return struct.pack("<H", x)
def u16(x): return struct.unpack("<H", x)[0]

def p8(x): return struct.pack("<B", x)
def u8(x): return struct.unpack("<B", x)[0]

PATTERN_CACHE = {}

def _xor_encode(data, key):
    """XOR encoding"""
    return bytes([b ^ key for b in data])

def _add_encode(data, key):
    """ADD encoding"""
    return bytes([(b + key) & 0xff for b in data])

def _sub_encode(data, key):
    """SUB encoding"""
    return bytes([(b - key) & 0xff for b in data])

def _has_bad(data, bad_bytes):
    """Check for bad bytes"""
    for b in bad_bytes:
        if b in data:
            return True
    return False

# Decoder stubs
def _arm64_decoder(key, size):
    """ARM64 decoder stub"""
    return bytes([
        0x00, 0x00, 0x00, 0x10,  # adr x0, encoded
        key, 0x00, 0x80, 0x52,   # mov w1, #key
        size & 0xff, 0x00, 0x80, 0x52,  # mov w2, #size
        0x23, 0x00, 0x40, 0x39,  # ldrb w3, [x0]
        0x63, 0x04, 0x01, 0x4a,  # eor w3, w3, w1
        0x23, 0x00, 0x00, 0x39,  # strb w3, [x0]
        0x00, 0x04, 0x00, 0x91,  # add x0, x0, #1
        0x42, 0x04, 0x00, 0xf1,  # subs x2, x2, #1
        0xe1, 0xff, 0xff, 0x54,  # b.ne decode_loop
        0x00, 0x00, 0x1f, 0xd6   # br x0
    ])

def _amd64_decoder(key, size):
    """AMD64 decoder stub"""
    return bytes([
        0xeb, 0x1e,                    # jmp short start
        0x5e,                          # pop rsi
        0x31, 0xc9,                    # xor ecx, ecx
        0x48, 0x83, 0xc1, 0x01,        # add rcx, 1
        0x48, 0x01, 0xce,              # add rsi, rcx
        0x80, 0x36, key,               # xor byte [rsi], key
        0x48, 0xff, 0xc9,              # dec rcx
        0x75, 0xf5,                    # jnz loop
        0xff, 0xe6,                    # jmp rsi
        0xe8, 0xdd, 0xff, 0xff, 0xff,  # call pop
    ])

def _x86_decoder(key, size):
    """x86 decoder stub"""
    return bytes([
        0xeb, 0x16,                    # jmp short start
        0x5e,                          # pop esi
        0x31, 0xc9,                    # xor ecx, ecx
        0x83, 0xc1, 0x01,              # add ecx, 1
        0x01, 0xce,                    # add esi, ecx
        0x80, 0x36, key,               # xor byte [esi], key
        0x49,                          # dec ecx
        0x75, 0xf9,                    # jnz loop
        0xff, 0xe6,                    # jmp esi
        0xe8, 0xe5, 0xff, 0xff, 0xff,  # call pop
    ])

def _get_decoder(arch):
    decoders = {
        "arm64": _arm64_decoder,
        "amd64": _amd64_decoder,
        "x86": _x86_decoder,
    }
    return decoders.get(arch)

def encode_shellcode(shellcode, arch, bad_bytes, fallback=True):
    strategies = [
        ("xor", _xor_encode, range(1, 256)),
        ("add", _add_encode, range(1, 256)),
        ("sub", _sub_encode, range(1, 256)),
    ]

    best_result = None
    best_removed = 0
    best_encoder = None
    best_key = None

    for name, encoder, keys in strategies:
        for key in keys:
            if key in bad_bytes:
                continue

            encoded = encoder(shellcode, key)
            remaining_bad = [b for b in bad_bytes if b in encoded]
            removed = len(bad_bytes) - len(remaining_bad)

            decoder_func = _get_decoder(arch)
            if decoder_func:
                decoder = decoder_func(key, len(encoded))
                if not _has_bad(decoder, bad_bytes):
                    forged = decoder + encoded
                    remaining_final = [b for b in bad_bytes if b in forged]
                    removed_final = len(bad_bytes) - len(remaining_final)

                    if removed_final > best_removed:
                        best_result = forged
                        best_removed = removed_final
                        best_encoder = name
                        best_key = key

                        if removed_final == len(bad_bytes):
                            return (best_result, "perfect",
                                   f"Perfect! {name} encoding with key 0x{key:02x}")

    if best_result and fallback:
        remaining = len([b for b in bad_bytes if b in best_result])
        return (best_result, "partial",
                f"Partial success: removed {best_removed}/{len(bad_bytes)} bad bytes using {best_encoder}")

    return (None, "failed", "No encoding strategy found")

# =========================
# PATTERN CREATE (CYCLIC)
# =========================
def pattern_create(size: int) -> bytes:
    if size in PATTERN_CACHE:
        return PATTERN_CACHE[size]

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
                    PATTERN_CACHE[size] = result
                    return result

    result = bytes(pattern[:size])
    PATTERN_CACHE[size] = result
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

