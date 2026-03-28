#!/usr/bin/env python3
# pwnlib_8448.py - Complete Multi-Architecture Exploitation Library

import struct
import sys
import os
import re
import time
import socket
import select
import subprocess
import pty
import string
import signal
from typing import Optional, Union, List, Dict, Tuple
from datetime import datetime

# =========================
# MODERN LOGGING SYSTEM
# =========================

class Logger:
    
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    GRAY = "\033[90m"
    
    SYM_INFO = "●"
    SYM_OK = "✓"
    SYM_WARN = "⚠"
    SYM_ERROR = "✗"
    SYM_DEBUG = "◆"
    SYM_SEND = "▶"
    SYM_RECV = "◀"
    SYM_CRASH = "‼"
    
    def __init__(self, debug: bool = False):
        self.debug = debug
        self._start_time = time.time()
    
    def _timestamp(self) -> str:
        return f"{self.GRAY}[{time.time() - self._start_time:06.2f}]{self.RESET}"
    
    def info(self, msg): print(f"{self._timestamp()} {self.BLUE}{self.SYM_INFO}{self.RESET} {msg}")
    def success(self, msg): print(f"{self._timestamp()} {self.GREEN}{self.SYM_OK}{self.RESET} {msg}")
    def warn(self, msg): print(f"{self._timestamp()} {self.YELLOW}{self.SYM_WARN}{self.RESET} {msg}")
    def error(self, msg): print(f"{self._timestamp()} {self.RED}{self.SYM_ERROR}{self.RESET} {msg}")
    def debug(self, msg): 
        if self.debug: print(f"{self._timestamp()} {self.GRAY}{self.SYM_DEBUG}{self.RESET} {self.DIM}{msg}{self.RESET}")
    def send(self, data):
        hex_str = ' '.join(f'{b:02x}' for b in data[:32])
        ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in data[:32])
        print(f"{self._timestamp()} {self.CYAN}{self.SYM_SEND}{self.RESET} {hex_str}  |{ascii_str}|")
    def recv(self, data):
        hex_str = ' '.join(f'{b:02x}' for b in data[:32])
        ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in data[:32])
        print(f"{self._timestamp()} {self.MAGENTA}{self.SYM_RECV}{self.RESET} {hex_str}  |{ascii_str}|")
    def crash(self, msg): print(f"{self._timestamp()} {self.RED}{self.SYM_CRASH}{self.RESET} {self.BOLD}{msg}{self.RESET}")
    def separator(self, title=""):
        if title:
            padding = (60 - len(title) - 2) // 2
            print(f"{self.GRAY}{'─' * padding} {title} {'─' * padding}{self.RESET}")
        else:
            print(f"{self.GRAY}{'─' * 60}{self.RESET}")

_logger = Logger()
def set_debug(enabled): _logger.debug = enabled
def log_info(msg): _logger.info(msg)
def log_ok(msg): _logger.success(msg)
def log_warn(msg): _logger.warn(msg)
def log_error(msg): _logger.error(msg)

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

# =========================
# ENCODING ENGINE - COMPLETE MULTI-ARCH DECODERS
# =========================

def _xor_encode(data, key): return bytes([b ^ key for b in data])
def _add_encode(data, key): return bytes([(b + key) & 0xff for b in data])
def _sub_encode(data, key): return bytes([(b - key) & 0xff for b in data])
def _has_bad(data, bad_bytes):
    for b in bad_bytes:
        if b in data: return True
    return False

# ============================================
# DECODER STUBS - ALL ARCHITECTURES & OS
# ============================================

# ARM64 LINUX Decoder
def _arm64_linux_decoder(key, size):
    return bytes([
        0x00, 0x00, 0x00, 0x10,           # adr x0, encoded
        key & 0xff, 0x00, 0x80, 0x52,     # mov w1, #key
        size & 0xff, 0x00, 0x80, 0x52,    # mov w2, #size
        0x23, 0x00, 0x40, 0x39,           # ldrb w3, [x0]
        0x63, 0x04, 0x01, 0x4a,           # eor w3, w3, w1
        0x23, 0x00, 0x00, 0x39,           # strb w3, [x0]
        0x00, 0x04, 0x00, 0x91,           # add x0, x0, #1
        0x42, 0x04, 0x00, 0xf1,           # subs x2, x2, #1
        0xe1, 0xff, 0xff, 0x54,           # b.ne decode_loop
        0x00, 0x00, 0x1f, 0xd6            # br x0
    ])

# AMD64 LINUX Decoder (x86-64)
def _amd64_linux_decoder(key, size):
    return bytes([
        0xeb, 0x1e,                       # jmp short start
        0x5e,                             # pop rsi
        0x31, 0xc9,                       # xor ecx, ecx
        0x48, 0x83, 0xc1, 0x01,           # add rcx, 1
        0x48, 0x01, 0xce,                 # add rsi, rcx
        0x80, 0x36, key,                  # xor byte [rsi], key
        0x48, 0xff, 0xc9,                 # dec rcx
        0x75, 0xf5,                       # jnz loop
        0xff, 0xe6,                       # jmp rsi
        0xe8, 0xdd, 0xff, 0xff, 0xff      # call pop
    ])

# x86 LINUX Decoder (32-bit)
def _x86_linux_decoder(key, size):
    return bytes([
        0xeb, 0x16,                       # jmp short start
        0x5e,                             # pop esi
        0x31, 0xc9,                       # xor ecx, ecx
        0x83, 0xc1, 0x01,                 # add ecx, 1
        0x01, 0xce,                       # add esi, ecx
        0x80, 0x36, key,                  # xor byte [esi], key
        0x49,                             # dec ecx
        0x75, 0xf9,                       # jnz loop
        0xff, 0xe6,                       # jmp esi
        0xe8, 0xe5, 0xff, 0xff, 0xff      # call pop
    ])

# AMD64 WINDOWS Decoder (x86-64)
def _amd64_windows_decoder(key, size):
    return bytes([
        0xeb, 0x1e,                       # jmp short start
        0x5e,                             # pop rsi
        0x31, 0xc9,                       # xor ecx, ecx
        0x48, 0x83, 0xc1, 0x01,           # add rcx, 1
        0x48, 0x01, 0xce,                 # add rsi, rcx
        0x80, 0x36, key,                  # xor byte [rsi], key
        0x48, 0xff, 0xc9,                 # dec rcx
        0x75, 0xf5,                       # jnz loop
        0xff, 0xe6,                       # jmp rsi
        0xe8, 0xdd, 0xff, 0xff, 0xff      # call pop
    ])

# x86 WINDOWS Decoder (32-bit)
def _x86_windows_decoder(key, size):
    return bytes([
        0xeb, 0x16,                       # jmp short start
        0x5e,                             # pop esi
        0x31, 0xc9,                       # xor ecx, ecx
        0x83, 0xc1, 0x01,                 # add ecx, 1
        0x01, 0xce,                       # add esi, ecx
        0x80, 0x36, key,                  # xor byte [esi], key
        0x49,                             # dec ecx
        0x75, 0xf9,                       # jnz loop
        0xff, 0xe6,                       # jmp esi
        0xe8, 0xe5, 0xff, 0xff, 0xff      # call pop
    ])

# Universal decoder selector
def get_decoder(arch: str, os_type: str = "linux"):
    decoders = {
        ("arm64", "linux"): _arm64_linux_decoder,
        ("amd64", "linux"): _amd64_linux_decoder,
        ("x86", "linux"): _x86_linux_decoder,
        ("amd64", "windows"): _amd64_windows_decoder,
        ("x86", "windows"): _x86_windows_decoder,
    }
    return decoders.get((arch, os_type))

def encode_shellcode(shellcode: bytes, arch: str, os_type: str = "linux", 
                     bad_bytes: List[int] = None, fallback: bool = True) -> Tuple[Optional[bytes], str, str]:
    if bad_bytes is None:
        bad_bytes = [0x00]
    
    strategies = [
        ("xor", _xor_encode, range(1, 256)),
        ("add", _add_encode, range(1, 256)),
        ("sub", _sub_encode, range(1, 256)),
    ]
    
    best_result, best_removed, best_encoder, best_key = None, 0, None, None
    
    for name, encoder, keys in strategies:
        for key in keys:
            if key in bad_bytes:
                continue
            
            encoded = encoder(shellcode, key)
            removed = len(bad_bytes) - len([b for b in bad_bytes if b in encoded])
            
            decoder_func = get_decoder(arch, os_type)
            if decoder_func:
                decoder = decoder_func(key, len(encoded))
                if not _has_bad(decoder, bad_bytes):
                    forged = decoder + encoded
                    removed_final = len(bad_bytes) - len([b for b in bad_bytes if b in forged])
                    
                    if removed_final > best_removed:
                        best_result, best_removed, best_encoder, best_key = forged, removed_final, name, key
                        if removed_final == len(bad_bytes):
                            return (best_result, "perfect", f"Perfect! {name} encoding with key 0x{key:02x}")
    
    if best_result and fallback:
        return (best_result, "partial", f"Partial: removed {best_removed}/{len(bad_bytes)} bad bytes using {best_encoder}")
    
    return (None, "failed", "No encoding strategy found")

# =========================
# PATTERN CREATE / OFFSET
# =========================

PATTERN_CACHE = {}

def pattern_create(size: int) -> bytes:
    if size in PATTERN_CACHE:
        return PATTERN_CACHE[size]
    
    charset = string.ascii_lowercase + string.ascii_uppercase + string.digits
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

def pattern_offset(value: Union[int, bytes], size: int = 10000, arch: int = 64) -> Optional[int]:
    pattern = pattern_create(size)
    
    if isinstance(value, int):
        value = struct.pack("<Q" if arch == 64 else "<I", value)
    elif not isinstance(value, bytes):
        raise TypeError(f"value must be int or bytes")
    
    for window in [8, 4, 3]:
        if len(value) >= window:
            for i in range(len(value) - window + 1):
                idx = pattern.find(value[i:i+window])
                if idx != -1:
                    return idx
    return None

def clean_ansi(data: bytes) -> bytes:
    return re.sub(rb'\x1b\[[0-9;]*[a-zA-Z]', b'', data)

def hexdump(data: bytes, cols: int = 16, simple: bool = False) -> str:
    if simple:
        hex_part = ' '.join(f'{b:02x}' for b in data[:32])
        ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in data[:32])
        return f"{hex_part}  |{ascii_part}|"
    
    result = []
    for i in range(0, len(data), cols):
        chunk = data[i:i+cols]
        hex_part = ' '.join(f'{b:02x}' for b in chunk).ljust(cols * 3)
        ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
        result.append(f"{i:08x}  {hex_part}  |{ascii_part}|")
    return '\n'.join(result)

# =========================
# REMOTE (SOCKET)
# =========================

class Remote:
    def __init__(self, host: str, port: int, debug: bool = False, timeout: int = 5):
        self.host = host
        self.port = port
        self.buffer = b""
        self.log = Logger(debug)
        
        self.sock = socket.socket()
        self.sock.settimeout(timeout)
        
        self.log.info(f"Connecting to {host}:{port}")
        try:
            self.sock.connect((host, port))
            self.log.success("Connection established")
        except Exception as e:
            self.log.error(f"Connection failed: {e}")
            raise
    
    def _recv_raw(self, n: int) -> bytes:
        try:
            return self.sock.recv(n)
        except:
            return b""
    
    def recv(self, n: int = 4096, timeout: float = None) -> bytes:
        if timeout:
            self.sock.settimeout(timeout)
        try:
            data = self.sock.recv(n)
            if data:
                self.log.recv(data)
            return data
        except:
            return b""
        finally:
            if timeout:
                self.sock.settimeout(5)
    
    def recvuntil(self, delim: Union[str, bytes], timeout: float = None) -> bytes:
        if isinstance(delim, str):
            delim = delim.encode()
        
        data = self.buffer
        self.buffer = b""
        start = time.time()
        
        while delim not in data:
            if timeout and (time.time() - start) > timeout:
                break
            chunk = self.recv(1, timeout=timeout)
            if not chunk:
                break
            data += chunk
        
        if delim in data:
            parts = data.split(delim, 1)
            result = parts[0] + delim
            if len(parts) > 1:
                self.buffer = parts[1]
            self.log.recv(result)
            return result
        return data
    
    def recvline(self, keepends: bool = False, timeout: float = None) -> bytes:
        data = self.recvuntil(b"\n", timeout=timeout)
        if not keepends and data.endswith(b"\n"):
            data = data[:-1]
        return data
    
    def recvlines(self, n: int = 1, keepends: bool = False, timeout: float = None) -> List[bytes]:
        lines = []
        for _ in range(n):
            line = self.recvline(keepends, timeout)
            if not line:
                break
            lines.append(line)
        return lines
    
    def send(self, data: Union[str, bytes]) -> None:
        if isinstance(data, str):
            data = data.encode()
        self.log.send(data)
        self.sock.sendall(data)
    
    def sendline(self, data: Union[str, bytes]) -> None:
        self.send(data + b"\n" if isinstance(data, bytes) else data + "\n")
    
    def interactive(self) -> None:
        self.log.info("Interactive mode (Ctrl+C to exit)")
        try:
            while True:
                rlist, _, _ = select.select([self.sock, sys.stdin], [], [])
                if self.sock in rlist:
                    data = self.sock.recv(4096)
                    if not data:
                        break
                    sys.stdout.buffer.write(clean_ansi(data))
                    sys.stdout.flush()
                if sys.stdin in rlist:
                    data = os.read(sys.stdin.fileno(), 1024)
                    if not data:
                        break
                    self.sock.sendall(data)
        except KeyboardInterrupt:
            print()
            self.log.info("Interactive mode ended")
    
    def close(self) -> None:
        try:
            self.sock.close()
        except:
            pass
        self.log.info("Connection closed")

# =========================
# PROCESS (LOCAL)
# =========================

class Process:
    def __init__(self, argv: Union[str, List[str]], debug: bool = False):
        self.argv = argv if isinstance(argv, list) else [argv]
        self.buffer = b""
        self.log = Logger(debug)
        
        self.log.info(f"Spawning process: {self.argv[0]}")
        if not os.path.exists(self.argv[0]):
            self.log.error(f"Binary not found: {self.argv[0]}")
            raise FileNotFoundError(f"Binary not found: {self.argv[0]}")
        
        self.master, self.slave = pty.openpty()
        self.process = subprocess.Popen(
            self.argv,
            stdin=self.slave,
            stdout=self.slave,
            stderr=self.slave,
            preexec_fn=os.setsid,
            close_fds=True
        )
        os.close(self.slave)
        self.log.success(f"Process started (PID: {self.process.pid})")
    
    def _recv_raw(self, n: int) -> bytes:
        try:
            rlist, _, _ = select.select([self.master], [], [], 0.05)
            if rlist:
                return os.read(self.master, n)
            return b""
        except OSError:
            return b""
    
    def recv(self, n: int = 4096, timeout: float = None) -> bytes:
        start = time.time()
        if len(self.buffer) >= n:
            data = self.buffer[:n]
            self.buffer = self.buffer[n:]
            return data
        
        data = self.buffer
        self.buffer = b""
        
        while len(data) < n:
            if timeout and (time.time() - start) > timeout:
                break
            chunk = self._recv_raw(n - len(data))
            if chunk:
                data += chunk
            else:
                time.sleep(0.01)
        
        if len(data) > n:
            self.buffer = data[n:]
            data = data[:n]
        
        if data:
            self.log.recv(data)
        return data
    
    def recvuntil(self, delim: Union[str, bytes], timeout: float = None) -> bytes:
        if isinstance(delim, str):
            delim = delim.encode()
        
        data = self.buffer
        self.buffer = b""
        start = time.time()
        
        while delim not in data:
            if timeout and (time.time() - start) > timeout:
                break
            chunk = self._recv_raw(1024)
            if chunk:
                data += chunk
            else:
                time.sleep(0.01)
        
        if delim in data:
            parts = data.split(delim, 1)
            result = parts[0] + delim
            if len(parts) > 1:
                self.buffer = parts[1]
            self.log.recv(result)
            return result
        return data
    
    def recvline(self, keepends: bool = False, timeout: float = None) -> bytes:
        data = self.recvuntil(b"\n", timeout=timeout)
        if not keepends and data.endswith(b"\n"):
            data = data[:-1]
        return data
    
    def recvlines(self, n: int = 1, keepends: bool = False, timeout: float = None) -> List[bytes]:
        lines = []
        for _ in range(n):
            line = self.recvline(keepends, timeout)
            if not line:
                break
            lines.append(line)
        return lines
    
    def send(self, data: Union[str, bytes]) -> None:
        if isinstance(data, str):
            data = data.encode()
        self.log.send(data)
        os.write(self.master, data)
    
    def sendline(self, data: Union[str, bytes]) -> None:
        self.send(data + b"\n" if isinstance(data, bytes) else data + "\n")
    
    def _get_status(self) -> Dict:
        if self.process.poll() is None:
            return {"running": True}
        
        signals = {
            -11: (11, "SIGSEGV", "Segmentation Fault"),
            -10: (10, "SIGBUS", "Bus Error"),
            -4: (4, "SIGILL", "Illegal Instruction"),
            -6: (6, "SIGABRT", "Aborted"),
        }
        
        code = self.process.returncode
        if code in signals:
            return {"running": False, "crashed": True, "signal": signals[code][0], 
                    "signal_name": signals[code][1], "exit_code": code}
        return {"running": False, "crashed": code != 0, "exit_code": code}
    
    def _extract_address(self, data: bytes) -> Optional[str]:
        patterns = [r'0x[0-9a-f]{8,16}', r'at 0x[0-9a-f]+', r'address 0x[0-9a-f]+', r'pc=0x[0-9a-f]+']
        text = data.decode('utf-8', errors='ignore')
        for pat in patterns:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                return match.group(0)
        return None
    
    def debug_crash(self, payload: bytes = None, timeout: float = 2) -> Dict:
        saved_debug = self.log.debug
        self.log.debug = False
        output = b""
        
        try:
            if payload:
                self.send(payload)
            
            start = time.time()
            while self.process.poll() is None:
                chunk = self._recv_raw(4096)
                if chunk:
                    output += chunk
                if timeout and (time.time() - start) > timeout:
                    break
                time.sleep(0.01)
            
            while True:
                chunk = self._recv_raw(4096)
                if not chunk:
                    break
                output += chunk
            
            status = self._get_status()
            crash = {
                "crashed": status.get("crashed", False),
                "signal": status.get("signal"),
                "signal_name": status.get("signal_name"),
                "address": None,
                "output": output,
                "exit_code": status.get("exit_code")
            }
            
            if crash["crashed"]:
                crash["address"] = self._extract_address(output)
                self._print_crash_report(crash)
            
            return crash
        finally:
            self.log.debug = saved_debug
    
    def _print_crash_report(self, crash: Dict) -> None:
        self.log.separator(" CRASH REPORT ")
        if crash.get("signal_name"):
            self.log.crash(f"Signal: {crash['signal_name']} ({crash['signal']})")
        else:
            self.log.crash(f"Exit Code: {crash.get('exit_code')}")
        
        if crash.get("address"):
            print(f"  ├─ Address: {crash['address']}")
            print(f"  └─ Location: ?? ()")
        
        if crash.get("output"):
            print(f"\n  ┌─ Output:")
            lines = crash["output"].decode('utf-8', errors='ignore').split('\n')
            for i, line in enumerate(lines[:8]):
                prefix = "└─" if i == len(lines[:8]) - 1 else "│"
                print(f"  {prefix} {line[:80]}")
            if len(lines) > 8:
                print(f"  │ ... ({len(lines)-8} more lines)")
        self.log.separator()
    
    def interactive(self) -> None:
        self.log.info("Interactive mode (Ctrl+C to exit)")
        try:
            while True:
                rlist, _, _ = select.select([self.master, sys.stdin], [], [])
                if self.master in rlist:
                    data = self._recv_raw(4096)
                    if data:
                        sys.stdout.buffer.write(clean_ansi(data))
                        sys.stdout.flush()
                    else:
                        break
                if sys.stdin in rlist:
                    data = os.read(sys.stdin.fileno(), 1024)
                    if not data:
                        break
                    os.write(self.master, data)
        except KeyboardInterrupt:
            print()
            self.log.info("Interactive mode ended")
    
    def close(self) -> None:
        try:
            self.process.kill()
        except:
            pass
        try:
            os.close(self.master)
        except:
            pass
        self.log.info("Process terminated")


