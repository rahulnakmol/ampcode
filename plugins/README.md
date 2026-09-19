# Plugins

Store personal Amp plugin source here.

The current plugin, [`amp-custom-mode-dials.ts`](./amp-custom-mode-dials.ts), adds Swift, Weave, and Prime without replacing Amp's built-in Dial modes.

[`advisory-team/`](./advisory-team/) adds Archi, Darci, Revo, and Opsci as modes and consultation tools. Read the [usage guide](../docs/advisory-team.md). Copy the entire directory when installing or publishing; its Markdown files contain the role instructions.

- Use one root `.ts` or `.js` file for a standalone plugin.
- Use `<plugin-name>/index.ts` for a plugin with supporting files or bundled skills.
- Include a static `description` export.
- Custom modes require matching `@amp-agent-mode` metadata comments.
- Discover valid models, efforts, and tool names with `amp plugins show-agent-options --json`.
- Validate all plugins with `make check`.

To publish globally, copy the plugin file or directory to the root of the Amp Personal Plugins repository listed by `amp plugins repositories`, then commit and push that repository.
