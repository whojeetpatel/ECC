#!/usr/bin/env python3
"""Split a transcript into note-taking chunks without losing a single word.

usage: chunk.py TRANSCRIPT [--words 3500] [--prev 5] [--out DIR]

Writes DIR/chunk_001.txt, chunk_002.txt, ... Each file holds the last --prev
lines of the previous chunk (read-only context) plus the chunk itself.
"""
import argparse
import re
from pathlib import Path


def units(text, limit):
    for line in text.splitlines():
        if not line.strip():
            continue
        if len(line.split()) <= limit:
            yield line
        else:  # ponytail: raw ASR blob with no newlines, split on sentences; no speaker/topic awareness
            yield from re.split(r"(?<=[.?!])\s+", line)


def words(lines):
    return sum(len(line.split()) for line in lines)


def chunk(lines, target):
    chunks, cur = [], []
    for line in lines:
        cur.append(line)
        if words(cur) >= target:
            chunks.append(cur)
            cur = []
    if cur:
        if chunks and words(cur) < target // 4:  # no tiny tail chunk
            chunks[-1].extend(cur)
        else:
            chunks.append(cur)
    return chunks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("transcript")
    ap.add_argument("--words", type=int, default=3500)
    ap.add_argument("--prev", type=int, default=5)
    ap.add_argument("--out")
    a = ap.parse_args()

    src = Path(a.transcript)
    text = src.read_text(encoding="utf-8")
    chunks = chunk(list(units(text, a.words)), a.words)
    out = Path(a.out) if a.out else src.with_name(src.stem + "_chunks")
    out.mkdir(parents=True, exist_ok=True)

    prev = []
    for i, c in enumerate(chunks, 1):
        name = f"chunk_{i:03d}.txt"
        (out / name).write_text(
            "PREVIOUS LINES (read-only, do not note again):\n" + "\n".join(prev)
            + "\n\nTRANSCRIPT CHUNK:\n" + "\n".join(c) + "\n",
            encoding="utf-8",
        )
        print(f"{out / name}  {words(c)} words")
        prev = c[-a.prev:]

    # nothing may be dropped or duplicated between transcript and chunks
    assert sum(words(c) for c in chunks) == len(text.split()), "word count mismatch: chunking lost text"
    print(f"{len(chunks)} chunks, {len(text.split())} words total -> {out}")


if __name__ == "__main__":
    main()
