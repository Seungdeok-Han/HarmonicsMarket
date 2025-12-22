#!/usr/bin/env python3
"""Render PlantUML .puml files in diagrams/ to SVG using plantuml.com server.
This uses the PlantUML URL encoding (deflate + custom base64) and GET /plantuml/svg/<encoded>.
Writes output to diagrams/<name>.svg and verifies it contains an <svg> tag.
"""
import os
import sys
import zlib
import urllib.request

PLANTUML_SERVER = "https://www.plantuml.com/plantuml/svg/"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIAGRAMS_DIR = os.path.join(ROOT, 'diagrams')


def encode_plantuml(text: bytes) -> str:
    # raw deflate (no zlib header)
    compobj = zlib.compressobj(level=9, wbits=-15)
    raw = compobj.compress(text) + compobj.flush()

    # PlantUML custom base64 alphabet
    def encode6bit(b):
        if 0 <= b <= 9:
            return chr(ord('0') + b)
        if 10 <= b <= 35:
            return chr(ord('A') + b - 10)
        if 36 <= b <= 61:
            return chr(ord('a') + b - 36)
        if b == 62:
            return '-'
        if b == 63:
            return '_'
        raise ValueError(b)

    res = []
    cur = 0
    bits = 0
    for byte in raw:
        cur = (cur << 8) | byte
        bits += 8
        while bits >= 6:
            bits -= 6
            val = (cur >> bits) & 0x3F
            res.append(encode6bit(val))
    if bits > 0:
        val = (cur << (6 - bits)) & 0x3F
        res.append(encode6bit(val))
    return ''.join(res)


def download_svg(encoded: str, outpath: str) -> bool:
    url = PLANTUML_SERVER + encoded
    print(f"GET {url}")
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            data = resp.read()
            if b"<svg" in data[:2000]:
                with open(outpath, 'wb') as f:
                    f.write(data)
                print(f"Wrote {outpath} ({len(data)} bytes)")
                return True
            else:
                print(f"Downloaded content for {outpath} does not look like SVG; first 400 bytes:\n{data[:400]!r}\n")
                # Save for debugging
                with open(outpath + '.bad', 'wb') as f:
                    f.write(data)
                return False
    except Exception as e:
        print(f"Failed to download {url}: {e}")
        return False


def main():
    puml_files = []
    if len(sys.argv) > 1:
        for p in sys.argv[1:]:
            puml_files.append(p)
    else:
        if not os.path.isdir(DIAGRAMS_DIR):
            print(f"Diagrams directory not found: {DIAGRAMS_DIR}")
            return 3
        for name in os.listdir(DIAGRAMS_DIR):
            if name.endswith('.puml'):
                puml_files.append(os.path.join(DIAGRAMS_DIR, name))
    if not puml_files:
        print("No .puml files found to render.")
        return 1
    ok = True
    for p in puml_files:
        print(f"Rendering {p}")
        with open(p, 'rb') as f:
            txt = f.read()
        enc = encode_plantuml(txt)
        base = os.path.splitext(os.path.basename(p))[0]
        out = os.path.join(DIAGRAMS_DIR, base + '.svg')
        success = download_svg(enc, out)
        if not success:
            ok = False
    return 0 if ok else 2


if __name__ == '__main__':
    sys.exit(main())
