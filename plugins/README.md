# Plugins

Store personal Amp plugin source here.

- Use one root `.ts` or `.js` file for a standalone plugin.
- Use `<plugin-name>/index.ts` for a plugin with supporting files or bundled skills.
- Include a static `description` export.
- Custom modes require matching `@amp-agent-mode` metadata comments.
- Discover valid models, efforts, and tool names with `amp plugins show-agent-options --json`.
- Validate all plugins with `make check`.

To publish globally, copy the plugin file or directory to the root of the Amp Personal Plugins repository listed by `amp plugins repositories`, then commit and push that repository.
