#!/usr/bin/env python3
"""Check a plain-English decision brief.

  python3 brief_check.py brief.md

Exits 0 and prints "pass" when the brief follows every rule. Otherwise exits 1 and prints each
broken rule as "<rule>: <what to fix>". Standard library only. The rules are in
../reference/template.md; mission-control's lib/brief.ts applies the same ones (except reading
ease and sentence length) before it shows a design dialog.
"""

import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

HEADINGS = (
    "You are deciding",
    "If you say yes",
    "If you say no",
    "What changes",
    "What done looks like",
    "What we checked and what we did not",
    "Risks you accept",
    "Not included",
    "How to undo it",
    "Words you may not know",
)
DETAILS_OPEN = "<details><summary>Technical record</summary>"
LIMITS = {"decision": 30, "yes": 40, "no": 40}
LIST_LIMITS = {"risks": 30, "excluded": 20}
KEYS = ("decision", "yes", "no", "risks", "excluded", "picture")
PICTURE_HOSTS = ("ampcode.com", "github.com")
MAX_CHARS = 20_000
MAX_SUMMARY_WORDS = 150
MAX_SENTENCE_WORDS = 25
MIN_EASE = 50
BANNED = json.loads((Path(__file__).with_name("banned.json")).read_text())["patterns"]
COMPILED = [
    (p["name"], re.compile(p["pattern"], re.M | re.ASCII | (re.I if p["ignoreCase"] else 0)))
    for p in BANNED
]
LIST_ITEM = re.compile(r"^\s*(?:[-*+]|[0-9]+\.)\s+(.*)$")


class Problem(Exception):
    pass


def words(text):
    return len(text.split())


def collapse(text):
    return " ".join(text.split())


def unquote(value):
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def front_matter(text):
    """Parse the small YAML subset a brief uses: one-line scalars and lists of one-line items."""
    match = re.match(r"\A---\n(.*?)\n---\n", text, re.S)
    if not match:
        raise Problem("front-matter: the file must start with front matter between two --- lines")
    data, key = {}, None
    for line in match.group(1).splitlines():
        if not line.strip():
            continue
        item = re.match(r"^\s+-\s+(.*)$", line)
        if item:
            if key is None or not isinstance(data[key], list):
                raise Problem(f"front-matter: list item outside a list: {line.strip()}")
            data[key].append(unquote(item.group(1)))
            continue
        pair = re.match(r"^([a-z]+):(.*)$", line)
        if not pair:
            raise Problem(f"front-matter: cannot read this line: {line.strip()}")
        key, value = pair.group(1), pair.group(2).strip()
        if key not in KEYS:
            raise Problem(f"front-matter: unknown key '{key}'; allowed: {', '.join(KEYS)}")
        if key in data:
            raise Problem(f"front-matter: '{key}' appears twice")
        data[key] = unquote(value) if value else []
    return data, text[match.end():]


def check_front_matter(data):
    for key, limit in LIMITS.items():
        value = data.get(key)
        if not isinstance(value, str) or not value:
            raise Problem(f"front-matter: '{key}' is required and must be one line of text")
        if words(value) > limit:
            raise Problem(f"front-matter: '{key}' has {words(value)} words; limit {limit}")
    for key, limit in LIST_LIMITS.items():
        items = data.get(key)
        if not isinstance(items, list) or not 1 <= len(items) <= 6:
            raise Problem(f"front-matter: '{key}' must list 1 to 6 items")
        if len({collapse(i) for i in items}) != len(items):
            raise Problem(f"front-matter: '{key}' items must be unique")
        for i in items:
            if not i or words(i) > limit:
                raise Problem(f"front-matter: each '{key}' item needs 1 to {limit} words: {i}")
    if "picture" in data:
        url = urlparse(data["picture"]) if isinstance(data["picture"], str) else None
        if not url or url.scheme != "https" or url.hostname not in PICTURE_HOSTS:
            raise Problem("front-matter: 'picture' must be an https URL on ampcode.com or github.com")


def summary(data):
    """The collapsed summary mission-control shows. Keep in step with lib/brief.ts."""
    lines = [
        f"You are deciding: {data['decision']}",
        f"If you say yes: {data['yes']}",
        f"If you say no: {data['no']}",
        "Risks you accept:",
    ]
    lines += [f"{i}. {r}" for i, r in enumerate(data["risks"], 1)]
    return "\n".join(lines)


def split_body(body):
    """Return (prose, sections) and check the headings and the closing technical record."""
    start = body.find(DETAILS_OPEN)
    if start < 0:
        raise Problem(f"technical-record: end the file with a {DETAILS_OPEN} block")
    if body.rstrip().splitlines()[-1].strip() != "</details>" or body.count(DETAILS_OPEN) != 1:
        raise Problem("technical-record: the one technical record block must close with </details> and end the file")
    prose = body[:start]
    found = re.findall(r"^## (.+?)[ \t]*$", prose, re.M)
    if tuple(found) != HEADINGS:
        missing = [h for h in HEADINGS if h not in found]
        detail = f"missing '{missing[0]}'" if missing else "wrong order or an extra ## heading"
        raise Problem(f"headings: {detail}; use exactly: " + " / ".join(HEADINGS))
    sections, current = {}, None
    for line in prose.splitlines():
        heading = re.match(r"^## (.+?)[ \t]*$", line)
        if heading:
            current = heading.group(1)
            sections[current] = []
        elif current:
            sections[current].append(line)
    return prose, sections


def check_consistency(data, sections):
    for key, heading in (("risks", "Risks you accept"), ("excluded", "Not included")):
        listed = {collapse(m.group(1)) for line in sections[heading] if (m := LIST_ITEM.match(line))}
        for item in data[key]:
            if collapse(item) not in listed:
                raise Problem(f"consistency: '{item}' from '{key}' must be a list item under '## {heading}'")


def check_html(prose):
    if re.search(r"<(?:!--|[A-Za-z/])", prose):
        raise Problem("html: raw HTML and HTML comments are not allowed before the technical record")


def banned(text):
    """Return the names of the banned patterns found in text, in banned.json order."""
    return [name for name, pattern in COMPILED if pattern.search(text)]


# Reading ease, copied from evals/planning/readability.py so the skill stands alone.
def readable_prose(text):
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
    keep = []
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith(("|", "#", "<")):
            continue
        s = re.sub(r"`[^`]*`", "X", s)
        s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)
        s = re.sub(r"[*_>]+", "", s).lstrip("-0123456789. ")
        keep.append(s if s.endswith((".", "!", "?", ":")) else s + ".")
    return " ".join(keep)


def syllables(word):
    word = word.lower()
    if len(word) <= 3:
        return 1
    word = re.sub(r"(?:[^laeiouy]es|ed|[^laeiouy]e)$", "", word)
    return max(1, len(re.findall(r"[aeiouy]{1,2}", word)))


WORD = re.compile(r"[A-Za-z][A-Za-z'-]*|\d[\d,.%]*")


def sentences(prose):
    return [s for s in re.split(r"(?<=[.!?:])\s+", readable_prose(prose)) if re.search(r"[A-Za-z]", s)]


def ease(prose):
    found = sentences(prose)
    ws = WORD.findall(" ".join(found))
    if not found or not ws:
        return None
    syl = sum(syllables(w) if w[0].isalpha() else 1 for w in ws)
    return round(206.835 - 1.015 * len(ws) / len(found) - 84.6 * syl / len(ws), 1)


def check(text):
    """Return a list of broken rules; empty when the brief passes."""
    problems = []
    if len(text) > MAX_CHARS:
        problems.append(f"length: {len(text)} characters; limit {MAX_CHARS}")
    try:
        data, body = front_matter(text)
        check_front_matter(data)
        if words(summary(data)) > MAX_SUMMARY_WORDS:
            raise Problem(f"summary: the collapsed summary has {words(summary(data))} words; limit {MAX_SUMMARY_WORDS}")
        prose, sections = split_body(body)
        check_consistency(data, sections)
        check_html(prose)
    except Problem as problem:
        return problems + [str(problem)]
    front = text[: len(text) - len(body)]
    for part, where in ((front, "front matter"), (prose, "prose")):
        for name in banned(part):
            problems.append(f"banned: {name} pattern in the {where}; move codes to the technical record")
    long = [s for s in sentences(prose) if len(WORD.findall(s)) > MAX_SENTENCE_WORDS]
    if long:
        problems.append(f"sentence-length: {len(long)} sentence(s) over {MAX_SENTENCE_WORDS} words, first: {long[0][:80]}")
    score = ease(prose)
    if score is None or score < MIN_EASE:
        problems.append(f"reading-ease: {score}; minimum {MIN_EASE}")
    return problems


def main(argv):
    if len(argv) != 2:
        print(__doc__.strip().splitlines()[2].strip(), file=sys.stderr)
        return 2
    problems = check(Path(argv[1]).read_text(encoding="utf-8"))
    for problem in problems:
        print(problem)
    if not problems:
        print("pass")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
