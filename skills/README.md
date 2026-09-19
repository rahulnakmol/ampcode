# Skills

Store source skills as `skills/<skill-name>/SKILL.md`.

Each `SKILL.md` starts with YAML frontmatter containing:

```yaml
---
name: reviewing-changes
description: Reviews code changes for correctness and risk. Use when asked to review a diff or pull request.
---
```

Requirements:

- The name is a lowercase gerund with hyphens and matches the parent directory.
- The description says both what the skill does and when to use it.
- Keep the main instructions under 500 lines; put detailed material in `reference/`.
- Put executable helpers in `scripts/` and explain when to run them.
- Inline simple MCP configuration in frontmatter and always restrict it with `includeTools`.
- Run `make check` before publication.

To publish globally, copy the complete skill directory to the root of the Amp Personal Skills repository listed by `amp skills repositories`, then commit and push that repository.
