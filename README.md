# pwnlib_8448

> Lightweight Python library for binary exploitation, CTFs, and exploit development.

[![Python Version](https://img.shields.io/badge/python-3.7+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20Windows-lightgrey.svg)]()
[![Vercel](https://img.shields.io/badge/Vercel-Deployed-black?logo=vercel)](https://pwnlib-8448.vercel.app)

---

## 📑 Table of Contents

- [Installation](#-installation)
- [Quick Start](#-quick-start)
- [Logging System](#-logging-system)
- [Packing / Unpacking](#-packing--unpacking)
- [Cyclic Patterns](#-cyclic-patterns)
- [Hexdump](#-hexdump)
- [Shellcode Encoding](#-shellcode-encoding)
- [Process (Local)](#-process-local)
- [Remote (Network)](#-remote-network)
- [Crash Detection](#-crash-detection)
- [Complete Examples](#-complete-examples)
- [API Reference](#-api-reference)
- [Common Bad Bytes](#-common-bad-bytes)
- [Connect](#-connect)

---

## 📦 Installation

### From GitHub (recommended)

```bash
pip install git+https://github.com/Narkielz/pwnlib_8448.git
```

### From GitLab (fallback)

```bash
pip install git+https://gitlab.com/Narkiel/pwnlib_8448.git
```

### Local development

```bash
git clone https://github.com/Narkielz/pwnlib_8448.git
cd pwnlib_8448
pip install -e .
```

---

## 🚀 Quick Start

```python
from pwnlib_8448 import Process, encode_shellcode, hexdump

p = Process("./vuln")

sc = b"\x90\x90\x90\xcc"
encoded, status, msg = encode_shellcode(sc, "amd64", "linux", bad_bytes=[0x00])

print(status, msg)
print(hexdump(encoded))

p.sendline(encoded)
p.interactive()
```

---

## 🎨 Logging System

| Function | Color | Description |
|----------|------|-------------|
| log_info | Blue | Informational messages |
| log_ok | Green | Success messages |
| log_warn | Yellow | Warning messages |
| log_error | Red | Error messages |
| log_send | Cyan | Sent data with hexdump |
| log_recv | Magenta | Received data with hexdump |

---

## 📦 Packing / Unpacking

| Function | Size | Description |
|----------|------|-------------|
| p8/u8 | 1B | pack/unpack 8-bit |
| p16/u16 | 2B | pack/unpack 16-bit |
| p32/u32 | 4B | pack/unpack 32-bit |
| p64/u64 | 8B | pack/unpack 64-bit |

---

## 🔁 Cyclic Patterns

```python
from pwnlib_8448 import pattern_create, pattern_offset

pattern = pattern_create(500)
offset = pattern_offset(0x6161616c, arch=64)
```

---

## 🛡️ Hexdump

```python
from pwnlib_8448 import hexdump
print(hexdump(b"Hello\x00World"))
```

---

## 🔐 Shellcode Encoding

```python
from pwnlib_8448 import encode_shellcode

encoded, status, msg = encode_shellcode(
    b"\x90\x90\xcc",
    arch="amd64",
    os="linux",
    bad_bytes=[0x00]
)
```

---

## 🖥️ Process (Local)

```python
from pwnlib_8448 import Process

p = Process("./vuln", debug=True)
p.sendline(b"AAAA")
p.interactive()
```

---

## 🌐 Remote (Network)

```python
from pwnlib_8448 import Remote

r = Remote("example.com", 1337)
r.sendline(b"AAAA")
r.interactive()
```

---

## 💥 Crash Detection

```python
crash = p.debug_crash(b"A"*100)
if crash["crashed"]:
    print(crash["address"])
```

---

## 💣 Complete Examples

See full docs for exploitation scenarios (buffer overflow, ROP, shellcode injection, remote exploits).

---

## 📚 API Reference

Core:
- set_debug()
- hexdump()
- pattern_create()
- pattern_offset()
- encode_shellcode()

---

## ⚠️ Common Bad Bytes

```python
BAD_NULL = [0x00]
BAD_NEWLINE = [0x00, 0x0a]
BAD_CTF = [0x00, 0x0a, 0x0d, 0x20, 0x09]
```

---

## 📡 Connect

[![GitHub](https://img.shields.io/badge/GitHub-Narkielz-181717?style=flat-square&logo=github)](https://github.com/Narkielz)
[![Twitter](https://img.shields.io/badge/Twitter-@narkiel_8448-1DA1F2?style=flat-square&logo=twitter)](https://twitter.com/narkiel_8448)
[![YouTube](https://img.shields.io/badge/YouTube-Narkielz_8448-FF0000?style=flat-square&logo=youtube)](https://youtube.com/@narkielz_8448)
[![GitLab](https://img.shields.io/badge/GitLab-narkiel-FC6D26?style=flat-square&logo=gitlab)](https://gitlab.com/narkiel)
[![Email](https://img.shields.io/badge/Email-narkiel.8448@gmail.com-D14836?style=flat-square&logo=gmail&logoColor=white)](mailto:narkiel.8448@gmail.com)

---
