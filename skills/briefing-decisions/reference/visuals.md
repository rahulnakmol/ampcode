# Pictures in a brief

Add a picture only when it replaces words a reader would otherwise struggle with: a before and
after, a timeline, a flow with more than three steps, or a cost comparison. A picture never
carries a fact the text does not state; the approval covers the text.

## Make it

- One self-contained HTML page: inline styles and data, no external scripts or fonts.
- Plain labels in the same words as the brief. No codes, hashes or IDs.
- Readable at phone width. Text contrast at least 4.5 to 1. Do not rely on colour alone.
- A title that says what the picture shows, such as "Where the demo site runs, before and after".

## Share it

| Host | How |
| --- | --- |
| Amp | Publish it as a visual artifact and put its `https://ampcode.com/...` URL in the brief's `picture` field. Link it from the brief text; the checker rejects embedded images, whose alt text is hidden. mission-control's dialog does not show it |
| GitHub | Commit it and use its `https://github.com/...` URL |
| Claude Code, VS Code, Copilot app | Save it next to the brief and open it in a browser or VS Code's built-in browser. Leave `picture` empty unless it has a `github.com` URL |

The checker accepts `picture` only as an `https` URL on `ampcode.com` or `github.com`, so a
look-alike host such as `ampcode.com.example.net` fails.
