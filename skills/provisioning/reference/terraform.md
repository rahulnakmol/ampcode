# Terraform and OpenTofu

Terraform can save a plan to a file and apply exactly that file. That is the exact plan this
skill binds the approval to. OpenTofu takes the same commands with `tofu` instead of
`terraform`. Sources: [JSON output format](https://developer.hashicorp.com/terraform/internals/json-format),
[`terraform plan`](https://developer.hashicorp.com/terraform/cli/commands/plan),
[`terraform apply`](https://developer.hashicorp.com/terraform/cli/commands/apply),
[`terraform test`](https://developer.hashicorp.com/terraform/cli/commands/test).

## Commands

Run them in the root module, with the backend for the target environment. `<skill>` is the
skill's directory. `<plans>` is a folder outside the checkout, one per change, for example
`$HOME/plans/2026-11-22-orders-prod`: the plan file and its JSON hold sensitive values in plain
text, so they never go into the working tree.
Before the first command, run `mkdir -p <plans>` and
`git -C <plans> rev-parse --is-inside-work-tree`. It must fail ("not a git repository"); if it
succeeds, `<plans>` is inside a checkout (a relative path from a nested root module, or a home
folder kept in git), so choose another folder.

| Step | Command | Notes |
| --- | --- | --- |
| Test | `terraform fmt -check -recursive`, `terraform init -input=false`, `terraform validate`, `terraform test` | `terraform test` runs the `*.tftest.hcl` files; it can create real resources, so run it only in a sandbox account |
| Preview | `terraform plan -input=false -lock-timeout=5m -out=<plans>/tfplan`, then `terraform show -json <plans>/tfplan > <plans>/plan.json` | Plan with the variables file for the environment (`-var-file=prod.tfvars`) |
| Policy | `checkov -f <plans>/plan.json --framework terraform_plan`, `conftest test <plans>/plan.json` | Checkov and Trivy run through `scanning-vulnerabilities`; Conftest runs your own OPA rules. HCP Terraform users can add Sentinel or OPA policy sets |
| Cost | `infracost breakdown --path <plans>/plan.json` | An estimate from list prices; usage-based costs need a usage file |
| Summary | `python3 <skill>/scripts/change_summary.py summarize <plans>/plan.json --tool terraform --plan-file <plans>/tfplan` | Prints the plan file's SHA-256 next to the summary digest; record both in the report |
| Apply | `terraform show -json <plans>/tfplan > <plans>/plan.json`, `python3 <skill>/scripts/change_summary.py verify <plans>/plan.json --tool terraform --plan-file <plans>/tfplan --expect <digest>`, then `terraform apply -input=false <plans>/tfplan` | Export and verify again just before the apply. Applies the saved plan only. Terraform refuses a saved plan when the state changed after the plan ("stale"); then preview again |
| Read back | `terraform plan -input=false -detailed-exitcode -out=<plans>/after.tfplan`, `terraform show -json <plans>/after.tfplan > <plans>/after.json`, `python3 <skill>/scripts/change_summary.py summarize <plans>/after.json --tool terraform --drift` | Exit 0 from both means the code and the cloud match |
| Drift | `terraform plan -input=false -detailed-exitcode -out=<plans>/drift.tfplan`, `terraform show -json <plans>/drift.tfplan > <plans>/drift.json`, `python3 <skill>/scripts/change_summary.py summarize <plans>/drift.json --tool terraform --drift` | `-detailed-exitcode` gives 0 (no changes), 1 (error) or 2 (changes). The summary also lists `resource_drift`, the changes made outside Terraform |

## The applied plan is the summarized plan

The summary reads `<plans>/plan.json`; `terraform apply` runs `<plans>/tfplan`. Apply only the
same file that `terraform show -json` produced `<plans>/plan.json` from. Pass that file with
`--plan-file` to `summarize` and to `verify`: its SHA-256 is printed next to the summary digest
and is part of the digest, so `verify` refuses a different plan file. Record the plan file's
SHA-256 next to the summary digest in the approval request and the report. Never re-plan between
`verify` and `apply`.

Without the saved plan file (you have only its JSON), summarize without `--plan-file`. The
summary prints `Plan file: not bound`, its `Next:` line asks for the plan file, and `verify`
refuses it. Label the result "plan file not bound" and do not apply: ask for the plan file, or
preview again with `-out=<plans>/tfplan`. An approval of an unbound summary does not cover an
apply. Then give the Apply commands verbatim from the Apply row, with the bound digest left as
`<digest>`, labelled "not run":

```bash
terraform show -json <plans>/tfplan > <plans>/plan.json
python3 <skill>/scripts/change_summary.py verify <plans>/plan.json --tool terraform --plan-file <plans>/tfplan --expect <digest>
terraform apply -input=false <plans>/tfplan
```

## Rules

- Never run `terraform apply` without a plan file: it makes a new plan. Never use
  `-auto-approve` with a new plan.
- Never use `-lock=false`. Run `terraform force-unlock` only with the owner, after you confirm
  that no other run holds the lock.
- `-target` and `-replace` make a partial or forced plan. Use them only when the owner asks, and
  show them in the summary you ask the owner to approve.
- The plan file and `<plans>/plan.json` hold sensitive values in plain text. The summary
  prints only addresses, types and actions. Never paste the plan file or the JSON into chat or
  the mission file; delete `<plans>` after the apply.
- An `import` block shows as `import` in the summary (or as an update marked "(import)"). An
  import writes state, so it is an outside effect like any other change.
- Protect stateful resources with `lifecycle { prevent_destroy = true }` and the provider's
  deletion protection (see [environments.md](environments.md)).
- A `moved` block changes an address without a change in the cloud. A `removed` block with
  `destroy = false` (the plan action `forget`) shows as unknown in the summary: read it, then
  accept it with `--accept-unknown`.
- Pin the Terraform version (`required_version`) and the provider versions, and commit
  `.terraform.lock.hcl`.

## State

State is remote and locked: see [identity.md](identity.md#remote-locked-state). One state per
environment. Never commit `*.tfstate` or `.terraform/`.
