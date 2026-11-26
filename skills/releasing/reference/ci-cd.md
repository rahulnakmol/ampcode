# CI/CD for promotions

Set these up once per repository. Each change to a repository's settings, rulesets or cloud
trust is an outside effect: show the exact change and get it approved first. The examples use
GitHub Actions; the same ideas apply to other CI systems.

## Required checks on every promoted branch

Protect `dev`, `rolling` and `main` with a branch protection rule or a ruleset:

- require status checks to pass before merging, and name the exact checks (the rolling suite);
- block force pushes and deletion;
- for `rolling` and `main`, limit who can push, so only the release path updates them.

Protect release tags too: a ruleset can target tags (`v*`, `rolling-*`) and block update and
deletion. Sources: [About protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches),
[About rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets).

A required check only helps if it runs on the commit you promote. Read its result for the exact
source commit in the plan, not for the branch name.

## OIDC federation instead of long-lived keys

A workflow can ask GitHub for a short-lived OpenID Connect token and exchange it with the cloud
provider for short-lived credentials. No cloud key is stored as a secret
([OpenID Connect](https://docs.github.com/en/actions/concepts/security/openid-connect)).

```yaml
permissions:
  id-token: write   # lets the job request the OIDC token
  contents: read
```

- Bind the cloud trust to the narrowest subject claim: one repository and one environment
  (`repo:<owner>/<repo>:environment:production`) or one ref, never a whole organization.
- Provider guides: [Microsoft Entra workload identity federation](https://learn.microsoft.com/en-us/entra/workload-id/workload-identity-federation),
  [AWS IAM OIDC identity providers](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_providers_create_oidc.html),
  [Google Cloud workload identity federation](https://cloud.google.com/iam/docs/workload-identity-federation).
- When you find a long-lived cloud key in repository secrets, report it as a finding and plan
  its replacement; do not delete it without approval.

## Pin actions by commit SHA

GitHub's secure-use reference says to pin actions to a full-length commit SHA, taken from the
action's own repository and not a fork; a tag can be moved by whoever controls the action
([Secure use reference](https://docs.github.com/en/actions/reference/security/secure-use)). The
same page now describes a workflow dependency lockfile, which supersedes SHA pinning for
repositories that adopt it.

```yaml
- uses: actions/checkout@<40-character-commit-sha>  # v5.0.0
```

Keep the version in a comment, and let Dependabot propose updates to the pinned SHAs
([Keeping your actions up to date with Dependabot](https://docs.github.com/en/code-security/dependabot/working-with-dependabot/keeping-your-actions-up-to-date-with-dependabot)).

Also:

- Set `permissions` per workflow or job, starting from `contents: read`. Add only what a job needs.
- Do not run untrusted pull request code with secrets (`pull_request_target` with a checkout of
  the pull request head is the common mistake).

## Protected environments for deployments

A deployment job names an environment (`environment: production`). The environment holds the
protection rules and secrets for that target: required reviewers, a wait timer, and which
branches or tags may deploy to it. Its secrets reach a job only after the rules pass
([Deployments and environments](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments)).

- Let only `main` and `v*` tags deploy to production; let `rolling` deploy to the canary.
- Use the environment's required reviewers as the human approval for the deployment, and
  record their approval with the plan digest.
- Use `concurrency` so two deployments to the same environment never run at once.

## Read the result back

After a promotion, check CI on the target ref and the new commit:

```bash
gh run list --branch rolling --limit 5            # find the run for the merge commit
gh run view <run-id> --json conclusion,headSha,url
```

Match `headSha` to the merge commit. Record the run URL and its conclusion
([gh run list](https://cli.github.com/manual/gh_run_list)). If the run has not finished, say
"pending", not "passed".
