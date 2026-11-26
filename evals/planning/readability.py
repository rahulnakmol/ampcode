#!/usr/bin/env python3
"""Flesch reading ease and average sentence length for the prose in Markdown files.

  python3 readability.py intake.md prd.md stakeholder-view.md

Tables, code blocks, headings, and HTML comments are skipped. The syllable count is a heuristic,
so treat small differences as noise.
"""

import re
import sys


def prose(text):
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
    keep = []
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith(("|", "#", "<")):
            continue
        s = re.sub(r"`[^`]*`", "X", s)                  # inline code and IDs count as one word
        s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)   # links keep their text
        s = re.sub(r"[*_>]+", "", s).lstrip("-0123456789. ")
        keep.append(s if s.endswith((".", "!", "?", ":")) else s + ".")
    return " ".join(keep)


def syllables(word):
    word = word.lower()
    if len(word) <= 3:
        return 1
    word = re.sub(r"(?:[^laeiouy]es|ed|[^laeiouy]e)$", "", word)
    return max(1, len(re.findall(r"[aeiouy]{1,2}", word)))


def score(text):
    sentences = [s for s in re.split(r"(?<=[.!?:])\s+", prose(text)) if re.search(r"[A-Za-z]", s)]
    words = re.findall(r"[A-Za-z][A-Za-z'-]*|\d[\d,.%]*", " ".join(sentences))
    if not sentences or not words:
        return None
    syl = sum(syllables(w) if w[0].isalpha() else 1 for w in words)
    asl = len(words) / len(sentences)
    return round(206.835 - 1.015 * asl - 84.6 * syl / len(words), 1), round(asl, 1), len(words)


if __name__ == "__main__":
    failed = False
    for path in sys.argv[1:]:
        result = score(open(path, encoding="utf-8").read())
        if result is None:
            print(f"{path}: no prose")
            continue
        ease, asl, n = result
        ok = ease >= 50 and asl <= 20
        failed |= not ok
        print(f"{'pass' if ok else 'FAIL'}  {path}: reading ease {ease}, {asl} words per sentence, {n} words")
    sys.exit(1 if failed else 0)
