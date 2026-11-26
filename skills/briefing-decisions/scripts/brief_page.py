#!/usr/bin/env python3
"""Render a checked decision brief as one readable HTML page for the approver.

    python3 brief_page.py brief.md [brief.html]

Refuses a brief that fails brief_check.py, so the page always shows the checked text and
nothing else. Writes brief.html next to the brief unless another path is given, and prints
its path. The page is self-contained (no scripts, fonts or network) and names the brief's
sha256, so the approver and the ledger can tie it to the reviewed revision. Standard library only.
"""

import hashlib
import html
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import brief_check  # noqa: E402

INLINE = re.compile(r"`([^`]+)`|\*\*(.+?)\*\*|\[([^\]]+)\]\(([^)\s]+)\)")
LIST = re.compile(r"^(\s*)([-*]|\d+\.)\s+(.*)$")

STYLE = """
:root{color-scheme:light dark}
body{margin:0;padding:24px 16px;font:15px/1.6 var(--font-sans,system-ui,sans-serif);
 color:var(--foreground,CanvasText);background:var(--background,Canvas)}
main{max-width:68ch}
h1{font-size:20px;font-weight:500;margin:0 0 4px;text-wrap:balance}
h2{font-size:15px;font-weight:500;margin:28px 0 6px;padding-top:16px;border-top:1px solid var(--border,#8884)}
h3{font-size:15px;font-weight:500;margin:16px 0 4px}
p,li{text-wrap:pretty}
.muted,summary,footer{color:var(--muted-foreground,GrayText);font-size:13px}
.summary{margin:16px 0 8px;padding:12px 16px;border-radius:8px;box-shadow:0 0 0 1px var(--border,#8884)}
.summary dt{color:var(--muted-foreground,GrayText);font-size:13px;margin-top:8px}
.summary dt:first-child{margin-top:0}
.summary dd{margin:0}
table{border-collapse:collapse;margin:8px 0}
th,td{text-align:left;padding:4px 12px 4px 0;border-bottom:1px solid var(--border,#8884);vertical-align:top}
code{font-family:var(--font-mono,ui-monospace,monospace);font-size:13px;overflow-wrap:anywhere}
a{color:var(--link,LinkText)}
details{margin-top:28px}
footer{margin-top:24px}
"""


def inline(text):
    out, at = [], 0
    for m in INLINE.finditer(text):
        out.append(html.escape(text[at:m.start()]))
        code, bold, label, url = m.groups()
        if code is not None:
            out.append(f"<code>{html.escape(code)}</code>")
        elif bold is not None:
            out.append(f"<strong>{html.escape(bold)}</strong>")
        elif "`" in label:  # a code span inside the label: show the Markdown, URL included
            out.append(html.escape(m.group(0)))
        elif url.startswith(("https://", "http://", "mailto:")):
            out.append(f'<a href="{html.escape(url)}">{html.escape(label)}</a>')
        else:
            out.append(f"{html.escape(label)} (<code>{html.escape(url)}</code>)")
        at = m.end()
    return "".join(out) + html.escape(text[at:])


def blocks(markdown):
    """Render the Markdown a brief uses: headings, paragraphs, lists, tables and plain fences."""
    out, para, stack = [], [], []

    def flush():
        if para:
            out.append(f"<p>{inline(' '.join(para))}</p>")
            para.clear()

    def close(depth=0):
        while len(stack) > depth:
            out.append(f"</li></{stack.pop()[1]}>")

    lines, i = markdown.split("\n"), 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("```"):
            flush(), close()
            fence = re.match(r"`+", line).group(0)
            end = next((j for j in range(i + 1, len(lines)) if lines[j].startswith(fence)), None)
            if end is None:
                raise brief_check.Problem("markdown: a code fence is not closed; close it so the sections show")
            out.append(f"<pre><code>{html.escape(chr(10).join(lines[i + 1:end]))}</code></pre>")
            i = end + 1
            continue
        heading = re.match(r"^(#{2,3}) (.+)$", line)
        item = LIST.match(line)
        if heading:
            flush(), close()
            level = len(heading.group(1))
            out.append(f"<h{level}>{inline(heading.group(2).strip())}</h{level}>")
        elif line.startswith("|"):
            flush(), close()
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append(re.split(r"(?<!\\)\|", lines[i].strip().strip("|")))
                i += 1
            body = [r for r in rows[1:] if not all(re.fullmatch(r":?-{3,}:?", c.strip()) for c in r)]
            out.append("<table><thead><tr>" + "".join(f"<th>{inline(c.strip())}</th>" for c in rows[0])
                       + "</tr></thead><tbody>" + "".join(
                           "<tr>" + "".join(f"<td>{inline(c.strip())}</td>" for c in r) + "</tr>" for r in body)
                       + "</tbody></table>")
            continue
        elif item:
            flush()
            depth = len(item.group(1)) // 2 + 1
            tag = "ol" if item.group(2)[0].isdigit() else "ul"
            if len(stack) > depth:
                close(depth)
            if len(stack) == depth:
                out.append("</li><li>")
            else:
                while len(stack) < depth:
                    stack.append((depth, tag))
                    out.append(f"<{tag}><li>")
            out.append(inline(item.group(3)))
        elif not line.strip():
            flush()
            if not (i + 1 < len(lines) and LIST.match(lines[i + 1])):
                close()
        elif stack:
            out.append(" " + inline(line.strip()))
        else:
            para.append(line.strip())
        i += 1
    flush(), close()
    return "\n".join(out)


def render(text, digest):
    data, _, body = brief_check.front_matter(text)
    prose, record, _ = brief_check.split_body(body)
    risks = "".join(f"<li>{inline(r)}</li>" for r in data["risks"])
    title = inline(data["decision"])
    picture = (f'<dt>Picture</dt><dd><a href="{html.escape(data["picture"])}">{html.escape(data["picture"])}</a></dd>\n'
               if data.get("picture") else "")
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(data['decision'])}</title><style>{STYLE}</style></head>
<body><main>
<p class="muted">Decision for your approval</p>
<h1>{title}</h1>
<dl class="summary">
<dt>If you say yes</dt><dd>{inline(data['yes'])}</dd>
<dt>If you say no</dt><dd>{inline(data['no'])}</dd>
<dt>Risks you accept</dt><dd><ol>{risks}</ol></dd>
{picture}</dl>
<p class="muted">Read the page, then answer in the approval dialog: approve, or say what to change.</p>
{blocks(prose)}
<details><summary>Technical record</summary>
{blocks(record.strip())}
</details>
<footer>Made from the checked brief, sha256 <code>{digest}</code>. The approval covers this text.</footer>
</main></body></html>
"""


def main(argv):
    if len(argv) not in (2, 3):
        print(__doc__.strip().splitlines()[2].strip(), file=sys.stderr)
        return 2
    source = Path(argv[1])
    raw = source.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        print("characters: the file is not valid UTF-8")
        return 1
    problems = brief_check.check(text)
    if problems:
        print("refused: the brief does not pass brief_check.py; fix it first")
        for problem in problems:
            print(problem)
        return 1
    try:
        page = render(text, hashlib.sha256(raw).hexdigest())
    except brief_check.Problem as problem:
        print(f"refused: {problem}")
        return 1
    target = Path(argv[2]) if len(argv) == 3 else source.with_suffix(".html")
    target.write_text(page, encoding="utf-8")
    print(target)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
