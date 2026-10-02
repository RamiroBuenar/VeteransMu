#!/usr/bin/env python3
"""Regenera update.info compatible con Parcer_MiniUpd.exe / Launcher Fase 1.
Formato: BinaryWriter.Write(XOR99(str)) por cada campo:
  [num_files][total_size][fileDir, fileHash_CRC32, fileSize] x N
- CRC32 IEEE (pol 0xEDB88320) igual que Crc32.cs, hex upper 8 chars.
- Rutas relativas con backslash (como Parser en Windows).
- Excluye version.txt, update.info, .git, .github, tools de Action, Logs, etc.
Uso: python tools/gen_update_info.py [client_dir]
"""
import os
import sys
import binascii

KEY = 99

EXCLUDE_NAMES = {
    "Parcer_MiniUpd.exe", "Parcer_FullUpd.exe",
    "file_parser.exe", "update.info", "version.txt",
    "client.info", "MuError.dmp",
    ".gitattributes", ".gitignore",
}
EXCLUDE_SUFFIXES = (".bak", ".tmp", ".pdb", ".dmp")
EXCLUDE_DIRS = {".git", ".github", "Logs", "ScreenShots", "tools"}


def xor_encrypt(s: str) -> str:
    return "".join(chr(ord(c) ^ KEY) for c in s)


def write_net_string(buf: bytearray, s: str):
    data = s.encode("utf-8")
    n = len(data)
    # 7-bit encoded int (igual que .NET BinaryWriter)
    while n >= 0x80:
        buf.append((n & 0x7F) | 0x80)
        n >>= 7
    buf.append(n & 0x7F)
    buf.extend(data)


def should_skip(rel: str) -> bool:
    parts = rel.replace("/", "\\").split("\\")
    if any(p in EXCLUDE_DIRS for p in parts[:-1]) or parts[0] in EXCLUDE_DIRS:
        return True
    name = parts[-1]
    if name in EXCLUDE_NAMES:
        return True
    lname = name.lower()
    if lname.endswith(EXCLUDE_SUFFIXES):
        return True
    return False


def collect(root: str):
    files = []
    total = 0
    for dirpath, dirnames, filenames in os.walk(root):
        # no entrar a excluidos (modifica in-place)
        dirnames[:] = sorted([d for d in dirnames if d not in EXCLUDE_DIRS])
        for fn in sorted(filenames):
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, root)
            # normaliza a backslash como el Parser
            rel = rel.replace("/", "\\")
            if should_skip(rel):
                continue
            size = os.path.getsize(full)
            with open(full, "rb") as f:
                data = f.read()
            crc = "%08X" % (binascii.crc32(data) & 0xFFFFFFFF)
            files.append((rel, crc, size))
            total += size
    return files, total


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    files, total = collect(root)
    buf = bytearray()
    write_net_string(buf, xor_encrypt(str(len(files))))
    write_net_string(buf, xor_encrypt(str(total)))
    for rel, crc, size in files:
        write_net_string(buf, xor_encrypt(rel))
        write_net_string(buf, xor_encrypt(crc))
        write_net_string(buf, xor_encrypt(str(size)))
    out = os.path.join(root, "update.info")
    with open(out, "wb") as f:
        f.write(buf)
    print(f"files={len(files)} total={total} -> {out}")


if __name__ == "__main__":
    main()
