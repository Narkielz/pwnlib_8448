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

        

# =========================
# ROP CLASS - ROP Chain Builder
# =========================

class ROP:
    """
    ROP (Return-Oriented Programming) chain builder.
    Helps construct ROP chains for different architectures.
    
    Example:
        rop = ROP("./binary", arch="amd64")
        rop.call("system", ["/bin/sh"])
        rop.call("exit", [0])
        payload = rop.build(offset=72)
    """
    
    def __init__(self, binary: str = None, arch: str = "amd64", debug: bool = False):
        """
        Initialize ROP builder.
        
        Args:
            binary: Path to binary (for gadget finding)
            arch: Architecture - "amd64", "x86", "arm64"
            debug: Enable debug output
        """
        self.binary = binary
        self.arch = arch.lower()
        self.debug = debug
        self.gadgets = {}
        self.chain = []
        self.stack_padding = []
        
        # Architecture-specific register mappings
        self._init_arch_registers()
        
        # Load gadgets if binary provided
        if binary:
            self._load_gadgets()
    
    def _init_arch_registers(self):
        """Initialize architecture-specific register configurations."""
        if self.arch == "amd64":
            self.registers = {
                "rdi": 0, "rsi": 8, "rdx": 16, "rcx": 24, "r8": 32, "r9": 40,
                "rax": 48, "rbx": 56, "rbp": 64, "rsp": 72
            }
            self.pointer_size = 8
            self.call_instruction = b"\xe8"  # call rel32
            self.ret_instruction = b"\xc3"
            self.pop_instructions = {
                "rdi": b"\x5f", "rsi": b"\x5e", "rdx": b"\x5a", 
                "rcx": b"\x59", "r8": b"\x41\x58", "r9": b"\x41\x59"
            }
            
        elif self.arch == "x86":
            self.registers = {
                "eax": 0, "ebx": 4, "ecx": 8, "edx": 12, 
                "esi": 16, "edi": 20, "ebp": 24, "esp": 28
            }
            self.pointer_size = 4
            self.call_instruction = b"\xe8"
            self.ret_instruction = b"\xc3"
            self.pop_instructions = {
                "eax": b"\x58", "ebx": b"\x5b", "ecx": b"\x59", 
                "edx": b"\x5a", "esi": b"\x5e", "edi": b"\x5f"
            }
            
        elif self.arch == "arm64":
            self.registers = {
                "x0": 0, "x1": 8, "x2": 16, "x3": 24, "x4": 32, "x5": 40,
                "x6": 48, "x7": 56, "x8": 64, "x9": 72, "x10": 80, "x11": 88
            }
            self.pointer_size = 8
            self.call_instruction = b"\x94\x00\x00\x00"  # bl
            self.ret_instruction = b"\xc0\x03\x5f\xd6"   # ret
            
        else:
            raise ValueError(f"Unsupported architecture: {self.arch}")
    
    def _load_gadgets(self):
        """Load ROP gadgets from binary using ROPgadget or manual scan."""
        if not self.binary:
            return
            
        # Try to use ROPgadget if available
        try:
            import subprocess
            result = subprocess.run(
                ["ROPgadget", "--binary", self.binary, "--multibr"],
                capture_output=True, text=True, timeout=10
            )
            
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if ':' in line:
                        addr_str, gadget = line.split(':', 1)
                        addr = int(addr_str.strip(), 16)
                        gadget = gadget.strip()
                        self.gadgets[gadget] = addr
                        
                if self.debug:
                    log_info(f"Loaded {len(self.gadgets)} gadgets from {self.binary}")
                    
        except (subprocess.TimeoutExpired, FileNotFoundError):
            if self.debug:
                log_warn("ROPgadget not found, falling back to manual gadget finding")
            self._find_gadgets_manual()
    
    def _find_gadgets_manual(self):
        """Fallback: Find common gadgets manually."""
        # Common gadget patterns for x64
        if self.arch == "amd64":
            common_gadgets = {
                "pop rdi; ret": 0x4006a3,   # Example - real address needed
                "pop rsi; ret": 0x4006a1,
                "pop rdx; ret": 0x4006a5,
                "pop rax; ret": 0x4006a7,
                "syscall": 0x4006b0,
                "ret": 0x4006a9
            }
            
        elif self.arch == "x86":
            common_gadgets = {
                "pop eax; ret": 0x80482e0,
                "pop ebx; ret": 0x80482e2,
                "pop ecx; ret": 0x80482e4,
                "pop edx; ret": 0x80482e6,
                "int 0x80": 0x80482e8,
                "ret": 0x80482ea
            }
            
        elif self.arch == "arm64":
            common_gadgets = {
                "pop x0; ret": 0x4006a3,
                "pop x1; ret": 0x4006a5,
                "pop x2; ret": 0x4006a7,
                "pop x3; ret": 0x4006a9,
                "ret": 0x4006ab
            }
        
        self.gadgets.update(common_gadgets)
    
    def find_gadget(self, pattern: str) -> Optional[int]:
        """
        Find a gadget by pattern.
        
        Args:
            pattern: Gadget pattern (e.g., "pop rdi; ret")
            
        Returns:
            Address of gadget or None if not found
        """
        return self.gadgets.get(pattern)
    
    def pop(self, register: str, value: int) -> 'ROP':
        """
        Add a pop {register} gadget to chain.
        
        Args:
            register: Register name (rdi, rsi, etc.)
            value: Value to pop into register
            
        Returns:
            Self for chaining
        """
        pop_gadget = f"pop {register}; ret"
        addr = self.find_gadget(pop_gadget)
        
        if addr is None:
            raise ValueError(f"Gadget not found: {pop_gadget}")
        
        self.chain.append(addr)
        self.chain.append(value)
        
        if self.debug:
            log_debug(f"Added pop {register} = 0x{value:x}")
        
        return self
    
    def call(self, function: Union[str, int], args: List[int] = None) -> 'ROP':
        """
        Add a function call to chain.
        
        Args:
            function: Function address or name (if in binary)
            args: List of arguments for the function
            
        Returns:
            Self for chaining
        """
        # Get function address
        if isinstance(function, str):
            # Try to find function in binary
            addr = self._get_function_address(function)
            if addr is None:
                raise ValueError(f"Function not found: {function}")
        else:
            addr = function
        
        # Set up arguments
        if args:
            if self.arch == "amd64":
                # x64 calling convention: rdi, rsi, rdx, rcx, r8, r9
                registers = ["rdi", "rsi", "rdx", "rcx", "r8", "r9"]
                for i, arg in enumerate(args[:6]):
                    self.pop(registers[i], arg)
                    
            elif self.arch == "x86":
                # x86 uses stack for arguments
                # Push arguments in reverse order
                for arg in reversed(args):
                    self.chain.append(arg)  # Will need pop gadget
                    
            elif self.arch == "arm64":
                # ARM64 calling convention: x0-x7
                registers = ["x0", "x1", "x2", "x3", "x4", "x5", "x6", "x7"]
                for i, arg in enumerate(args[:8]):
                    self.pop(registers[i], arg)
        
        # Add function call
        self.chain.append(addr)
        
        if self.debug:
            log_debug(f"Added call to 0x{addr:x}")
        
        return self
    
    def ret(self, value: int = None) -> 'ROP':
        """
        Add return instruction to chain.
        
        Args:
            value: Optional value to return (for gadgets)
            
        Returns:
            Self for chaining
        """
        ret_addr = self.find_gadget("ret")
        if ret_addr is None:
            raise ValueError("Ret gadget not found")
        
        if value is not None:
            self.chain.append(value)
        self.chain.append(ret_addr)
        
        return self
    
    def syscall(self, nr: int, args: List[int] = None) -> 'ROP':
        """
        Add syscall to chain.
        
        Args:
            nr: Syscall number
            args: Syscall arguments
            
        Returns:
            Self for chaining
        """
        if self.arch == "amd64":
            self.pop("rax", nr)
            if args:
                registers = ["rdi", "rsi", "rdx", "r10", "r8", "r9"]
                for i, arg in enumerate(args[:6]):
                    self.pop(registers[i], arg)
                    
            syscall_gadget = self.find_gadget("syscall")
            if syscall_gadget is None:
                raise ValueError("Syscall gadget not found")
            self.chain.append(syscall_gadget)
            
        elif self.arch == "x86":
            self.pop("eax", nr)
            if args:
                registers = ["ebx", "ecx", "edx", "esi", "edi"]
                for i, arg in enumerate(args[:5]):
                    self.pop(registers[i], arg)
                    
            int80_gadget = self.find_gadget("int 0x80")
            if int80_gadget is None:
                raise ValueError("int 0x80 gadget not found")
            self.chain.append(int80_gadget)
            
        return self
    
    def _get_function_address(self, name: str) -> Optional[int]:
        """Get function address from binary."""
        # Try to use objdump if available
        try:
            import subprocess
            result = subprocess.run(
                ["objdump", "-t", self.binary],
                capture_output=True, text=True, timeout=5
            )
            
            for line in result.stdout.split('\n'):
                if name in line and '*' not in line:
                    parts = line.split()
                    if len(parts) >= 5 and parts[3] == 'F':
                        addr = int(parts[0], 16)
                        return addr
                        
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
            
        return None
    
    def padding(self, size: int, value: int = 0) -> 'ROP':
        """
        Add padding bytes to chain.
        
        Args:
            size: Number of bytes to pad
            value: Value to pad with (0 for null bytes)
            
        Returns:
            Self for chaining
        """
        if value == 0:
            self.stack_padding.append(b"\x00" * size)
        else:
            pad_val = p64(value) if self.pointer_size == 8 else p32(value)
            self.stack_padding.append(pad_val * (size // self.pointer_size))
        
        return self
    
    def build(self, offset: int = None) -> bytes:
        """
        Build the ROP chain.
        
        Args:
            offset: Buffer overflow offset (optional)
            
        Returns:
            Complete ROP chain as bytes
        """
        # Build chain
        chain_bytes = b""
        for item in self.chain:
            if isinstance(item, int):
                if self.pointer_size == 8:
                    chain_bytes += p64(item)
                else:
                    chain_bytes += p32(item)
            else:
                chain_bytes += item
        
        # Add padding
        for pad in self.stack_padding:
            chain_bytes += pad
        
        # Add offset if provided
        if offset:
            return b"A" * offset + chain_bytes
        
        return chain_bytes
    
    def show(self) -> None:
        """Display the current ROP chain."""
        log_info(f"ROP Chain ({len(self.chain)} gadgets):")
        log_info(f"Architecture: {self.arch}")
        log_info(f"Pointer size: {self.pointer_size} bytes")
        
        for i, item in enumerate(self.chain):
            if isinstance(item, int):
                log_debug(f"  [{i:3d}] 0x{item:016x}")
            else:
                log_debug(f"  [{i:3d}] {item.hex()}")
        
        if self.stack_padding:
            total_pad = sum(len(p) for p in self.stack_padding)
            log_info(f"Padding: {total_pad} bytes")
    
    def clear(self) -> None:
        """Clear the ROP chain."""
        self.chain = []
        self.stack_padding = []
        
    def save(self, filename: str) -> None:
        """
        Save ROP chain to file.
        
        Args:
            filename: Output filename
        """
        with open(filename, 'wb') as f:
            f.write(self.build())
        log_ok(f"ROP chain saved to {filename}")

