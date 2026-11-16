#!/usr/bin/env python3
"""Check a plain-English decision brief.

  python3 brief_check.py brief.md

Exits 0 and prints "pass" when the brief follows every rule. Otherwise exits 1 and prints each
broken rule as "<rule>: <what to fix>". Standard library only. The rules are in
../reference/template.md. mission-control's lib/brief.ts applies the same rules, except reading
ease, before it shows a design dialog; tests/fixtures/brief-cases.json keeps the two in step.
Whitespace means space, tab and newline only, so both implementations count the same words.
"""

import json
import re
import sys
import unicodedata
from pathlib import Path

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
DETAILS_CLOSE = "</details>"
LIMITS = {"decision": 30, "yes": 40, "no": 40}
LIST_LIMITS = {"risks": 30, "excluded": 20}
KEYS = ("decision", "yes", "no", "risks", "excluded", "picture")
PICTURE = re.compile(r"^https://(ampcode\.com|github\.com)(/[\x21-\x7e]*)?$", re.ASCII)
# Control and format characters (zero-width, bidirectional, tag characters) are invisible or reorder text.
CONTROL = re.compile("[\x00-\x08\x0b-\x1f\x7f-\x9f\u2028\u2029]")
# Raw HTML (tags, comments, <!DOCTYPE, <![CDATA[, <?...?>) and Markdown link reference definitions
# all render as hidden text.
# A reference definition hides text even inside a list item or block quote, with an escaped ],
# or with a label that continues on the next line after a backslash.
HIDDEN = re.compile(r"<(?:[!?]|[A-Za-z/])|^[ \t>*+\-0-9.)]*\[(?:\\[\s\S]|[^\\\]])*\]:", re.M)
# Markdown that renders some of its text invisibly. Links and fences are allowlisted: a link is
# [text](destination) with text and a plain destination (no spaces, parentheses, backslashes or
# quotes) closed at once, so it has no title; a fence line holds only the fence. Images, empty link
# text, GitHub math commands and table rows wider than their header are rejected.
IMAGE = re.compile(r"!\[")
INLINE_LINK = re.compile(r"\]\((?!<?[^\s()<>\\\"']+>?\))")
EMPTY_LINK = re.compile(r"\[[ \t*_~]*\]\(")
FENCE_LABEL = re.compile(r"^[ \t>*+\-0-9.)]*(?:`{3,}(?!`)|~{3,}(?!~))[ \t]*\S", re.M)
MATH = re.compile(r"\$[^$]*\\[A-Za-z]")
TABLE_DELIMITER = re.compile(r"^\|?[ \t]*:?-+:?[ \t]*(?:\|[ \t]*:?-+:?[ \t]*)*\|?[ \t]*$")
CONTAINER = re.compile(r"^[ \t>]*")
MARKER = re.compile(r"^(?:[-*+]|[0-9]+[.)])[ \t]+")
# YAML would read these in a front-matter value as a comment, anchor, alias, tag or block, and
# GitHub's front-matter table would hide words.
YAML_SPECIAL = re.compile(r"^[&*!|>{\[%@`]|[ \t]#")
MAX_CHARS = 20_000
MAX_SUMMARY_WORDS = 150
MAX_SENTENCE_WORDS = 25
MIN_EASE = 50
BANNED = json.loads((Path(__file__).with_name("banned.json")).read_text())["patterns"]
COMPILED = [
    (p["name"], re.compile(p["pattern"], re.M | re.ASCII | (re.I if p["ignoreCase"] else 0)))
    for p in BANNED
]
LIST_ITEM = re.compile(r"^[ \t]*(?:[-*+]|[0-9]+\.)[ \t]+(.*)$")
HEADING = re.compile(r"^## (.+?)[ \t]*$")


class Problem(Exception):
    pass


def words(text):
    return len(re.findall(r"[^ \t\n]+", text))


def collapse(text):
    return " ".join(re.findall(r"[^ \t\n]+", text))


def trim(text):
    return text.strip(" \t")


def unquote(value):
    value = trim(value)
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def front_matter(text):
    """Parse the small YAML subset a brief uses: one-line scalars and lists of one-line items."""
    match = re.match(r"\A---\n(.*?)\n---\n", text, re.S)
    if not match:
        raise Problem("front-matter: the file must start with front matter between two --- lines")
    data, key = {}, None
    for line in match.group(1).split("\n"):
        if not trim(line):
            continue
        item = re.match(r"^[ \t]+-[ \t]+(.*)$", line)
        if item:
            if key is None or not isinstance(data[key], list):
                raise Problem(f"front-matter: list item outside a list: {trim(line)}")
            if YAML_SPECIAL.search(trim(item.group(1))):
                raise Problem(f"front-matter: a '{key}' item starts with a YAML symbol or has ' #'; write plain text")
            data[key].append(unquote(item.group(1)))
            continue
        pair = re.match(r"^([a-z]+):(.*)$", line)
        if not pair:
            raise Problem(f"front-matter: cannot read this line: {trim(line)}")
        key, value = pair.group(1), trim(pair.group(2))
        if YAML_SPECIAL.search(value):
            raise Problem(f"front-matter: '{key}' starts with a YAML symbol or has ' #'; write plain text")
        if key not in KEYS:
            raise Problem(f"front-matter: unknown key '{key}'; allowed: {', '.join(KEYS)}")
        if key in data:
            raise Problem(f"front-matter: '{key}' appears twice")
        data[key] = unquote(value) if value else []
    return data, match.group(0), text[match.end():]


def check_front_matter(data):
    for key, limit in LIMITS.items():
        value = data.get(key)
        if not isinstance(value, str) or not words(value):
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
            if not 1 <= words(i) <= limit:
                raise Problem(f"front-matter: each '{key}' item needs 1 to {limit} words: {i}")
    if "picture" in data and not (isinstance(data["picture"], str) and PICTURE.match(data["picture"])):
        raise Problem("front-matter: 'picture' must be an https URL on ampcode.com or github.com")


def summary(data):
    """The labelled summary of the front matter. Keep in step with lib/brief.ts."""
    lines = [
        f"You are deciding: {data['decision']}",
        f"If you say yes: {data['yes']}",
        f"If you say no: {data['no']}",
        "Risks you accept:",
    ]
    lines += [f"{i}. {r}" for i, r in enumerate(data["risks"], 1)]
    return "\n".join(lines)


def split_body(body):
    """Return (prose, technical record, sections) after checking headings and the record block."""
    start = body.find(DETAILS_OPEN)
    if start < 0:
        raise Problem(f"technical-record: end the file with a {DETAILS_OPEN} block")
    end = body.rstrip(" \t\n")
    if trim(end.split("\n")[-1]) != DETAILS_CLOSE or body.count(DETAILS_OPEN) != 1:
        raise Problem("technical-record: the one technical record block must close with </details> and end the file")
    prose = body[:start]
    record = end[start + len(DETAILS_OPEN): end.rfind(DETAILS_CLOSE)]
    found = [m.group(1) for line in prose.split("\n") if (m := HEADING.match(line))]
    if tuple(found) != HEADINGS:
        missing = [h for h in HEADINGS if h not in found]
        detail = f"missing '{missing[0]}'" if missing else "wrong order or an extra ## heading"
        raise Problem(f"headings: {detail}; use exactly: " + " / ".join(HEADINGS))
    sections, current = {}, None
    for line in prose.split("\n"):
        heading = HEADING.match(line)
        if heading:
            current = heading.group(1)
            sections[current] = []
        elif current:
            sections[current].append(line)
    return prose, record, sections


def check_consistency(data, sections):
    for key, heading in (("risks", "Risks you accept"), ("excluded", "Not included")):
        listed = {collapse(m.group(1)) for line in sections[heading] if (m := LIST_ITEM.match(line))}
        for item in data[key]:
            if collapse(item) not in listed:
                raise Problem(f"consistency: '{item}' from '{key}' must be a list item under '## {heading}'")


def banned(text):
    """Return the names of the banned patterns found in text, in banned.json order."""
    return [name for name, pattern in COMPILED if pattern.search(text)]


# Reading ease and sentences, adapted from evals/planning/readability.py so the skill stands
# alone. Sentence length uses the same steps in lib/brief.ts; reading ease is Python only.
def readable_prose(text):
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    keep = []
    for line in text.split("\n"):
        s = trim(line)
        if not s or s.startswith(("|", "#", "<")):
            continue
        s = re.sub(r"`[^`]*`", "X", s)
        s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)
        s = re.sub(r"^[-0-9. ]+", "", re.sub(r"[*_>]+", "", s))
        keep.append(s if s.endswith((".", "!", "?", ":")) else s + ".")
    return " ".join(keep)


WORD = re.compile(r"[A-Za-z][A-Za-z'-]*|[0-9][0-9,.%]*")


def cells(line):
    s = trim(CONTAINER.sub("", line))
    s = s[1:] if s.startswith("|") else s
    s = s[:-1] if s.endswith("|") and not s.endswith("\\|") else s
    return len(re.split(r"(?<!\\)\|", s))


def hidden_markdown(text):
    """Name the first Markdown construct that hides words, or None. Keep in step with lib/brief.ts."""
    if IMAGE.search(text):
        return "an image"
    if EMPTY_LINK.search(text):
        return "a link with no text"
    if INLINE_LINK.search(text):
        return "a link with a title or an unusual destination"
    if FENCE_LABEL.search(text):
        return "a code fence with a label"
    if MATH.search(text):
        return "a math command"
    lines = text.split("\n")
    for i in range(1, len(lines)):
        header = MARKER.sub("", CONTAINER.sub("", lines[i - 1]))
        delimiter = CONTAINER.sub("", lines[i])
        if ("|" in header or "|" in delimiter) and TABLE_DELIMITER.match(delimiter) and "-" in delimiter:
            width = cells(header)
            for row in lines[i + 1:]:
                if not trim(row):
                    break
                if cells(row) > width:
                    return "a table row wider than its header"
    return None


def sentences(prose):
    return [s for s in re.split(r"(?<=[.!?:])[ \t]+", readable_prose(prose)) if re.search(r"[A-Za-z]", s)]


def syllables(word):
    word = word.lower()
    if len(word) <= 3:
        return 1
    word = re.sub(r"(?:[^laeiouy]es|ed|[^laeiouy]e)$", "", word)
    return max(1, len(re.findall(r"[aeiouy]{1,2}", word)))


def ease(prose):
    found = sentences(prose)
    ws = WORD.findall(" ".join(found))
    if not found or not ws:
        return None
    syl = sum(syllables(w) if w[0].isalpha() else 1 for w in ws)
    return round(206.835 - 1.015 * len(ws) / len(found) - 84.6 * syl / len(ws), 1)


def check(text):
    """Return a list of broken rules; empty when the brief passes."""
    if len(text) > MAX_CHARS:
        return [f"length: {len(text)} characters; limit {MAX_CHARS}"]
    if CONTROL.search(text) or any(unicodedata.category(c) == "Cf" for c in text):
        return ["characters: use plain newlines (no carriage returns, line separators or control characters)"]
    try:
        data, front, body = front_matter(text)
        check_front_matter(data)
        if words(summary(data)) > MAX_SUMMARY_WORDS:
            raise Problem(f"summary: the summary has {words(summary(data))} words; limit {MAX_SUMMARY_WORDS}")
        prose, record, sections = split_body(body)
        check_consistency(data, sections)
        if HIDDEN.search(front + prose + record):
            raise Problem("html: raw HTML, HTML comments and link reference definitions are not allowed, except the technical record block itself")
        found = hidden_markdown(front + prose + record)
        if found:
            raise Problem(f"markdown: {found} can hide words; use no images, link titles, labelled code fences or table rows wider than their header")
    except Problem as problem:
        return [str(problem)]
    problems = []
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
    # Bytes, not read_text: newline translation would hide carriage returns the plugin rejects.
    try:
        text = Path(argv[1]).read_bytes().decode("utf-8")
    except UnicodeDecodeError:
        print("characters: the file is not valid UTF-8")
        return 1
    problems = check(text)
    for problem in problems:
        print(problem)
    if not problems:
        print("pass")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
