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

For user workflows, see [Using the skills](../docs/using-skills.md) and [Start a Blueprinting engagement](../docs/blueprinting.md).

Publishing is separate from source integration and requires explicit approval of the destination. Discover the User/Workspace Skills repositories with `amp skills repositories`; preserve existing changes in the selected clone. Copy the complete skill directory, including text helpers, manifests and references, to its root, review the diff, then commit and push only with authorization. Verify the host-selected package after publication; a loaded SKILL.md alone does not prove its companion files arrived. Blueprinting's separate engagement template is not included in its six skill packages.
