Clear: an explicitly approved, single-string typo correction; no clarification or mission needed.

```diff
-<button onclick={retryJob}>Retyr</button>
+<button onclick={retryJob}>Retry</button>
```

**Proposed verification:** Review the eventual diff to confirm only the visible label changed and `onclick={retryJob}` remains untouched. Open the internal preview in its failed-job state and confirm the button displays “Retry”. No localization, permissions, or release checks are needed for this scoped correction.

**Next action:** Apply this exact replacement when file edits are permitted. No source files were edited and no checks were executed.
