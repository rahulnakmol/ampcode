---
name: provisioning
description: "Runs one tool-neutral infrastructure-as-code workflow on Azure, AWS and Google Cloud: choose the tool (Terraform or OpenTofu, Bicep, CloudFormation, Infrastructure Manager), test modules, preview, policy scan, cost estimate, a change summary digest, approval bound to it, apply only that plan, read back and drift check. A standard-library script turns Terraform plans, Bicep what-if results and CloudFormation change sets into one summary with a digest. Each apply is an outside effect; a destructive change to a stateful resource needs its own explicit confirmation. Credentials stay out of the repository and chat; CI uses OIDC federation. Use when asked to provision, change or remove cloud infrastructure, review or apply a plan, what-if or change set, check drift, set up remote state or CI identity for IaC, or migrate from Deployment Manager. Not for designing the system (use architecting), scanning IaC for vulnerabilities alone (use scanning-vulnerabilities), or promoting branches (use releasing)."
---

# Provisioning

Infrastructure changes the same way every time: preview it, summarize it, get the summary
digest approved, apply only that plan, then read the result back. The tool changes; the
workflow does not. `scripts/change_summary.py` turns every tool's preview into one summary.

## When to use it

- **Input:** a confirmed design (from `architecting`: the NFRs, the recovery objectives and the
  stateful resources) or a clear request, and the target environment.
- **Callers:** `missioning` (infrastructure playbook), `delivering`, and `monitoring`, whose
  alerts and dashboards change through this skill.
- **Companions:** `scanning-vulnerabilities` is the IaC policy-scan companion (Checkov, Trivy);
  run it before approval. `releasing` owns the promotion rules for changes to the pipeline itself.
- **Output:** the summary, its digest, the approval record, the commands run and the read-back.

## Outside effects

Each apply, import, state change and deletion is an outside effect. A preview is not.

- Approval binds to the summary digest. Run an apply only when the mission contract
  pre-authorizes that exact effect, or the owner approves the exact plan: its summary digest.
  Outside a contract mission, the owner approves the exact plan digest.
- An apply to a shared or production environment needs a contract clause that pre-authorizes
  applies to that environment by name, or the owner approves that summary digest. A general
  "you may deploy" does not cover it.
- A destructive change to a stateful resource (a delete or a replace) needs its own explicit
  confirmation: the owner confirms that resource and that action by name, or the contract names
  them. An approved digest does not cover it. Ask for each one apart from the digest approval.
- An approval of an earlier digest does not cover a new summary. Summarize again and ask again.
- When you do not know an environment's tier, treat it as production.

Tiers, the stateful types and their protections: [reference/environments.md](reference/environments.md).

## Choose the tool

| Tool | Use it when | Exact plan | Reference |
| --- | --- | --- | --- |
| Terraform or OpenTofu | Several clouds or providers, or the team knows HCL | Saved plan file | [terraform.md](reference/terraform.md) |
| Bicep | Azure only, no state file to run | None: what-if again just before the deploy | [bicep.md](reference/bicep.md) |
| CloudFormation | AWS only, stack-managed state | Change set | [cloudformation.md](reference/cloudformation.md) |
| Infrastructure Manager | Google Cloud, Terraform run by a Google service | None: pin the source and preview again | [gcp-infrastructure-manager.md](reference/gcp-infrastructure-manager.md) |

Keep the tool a repository already uses, unless the owner decides to migrate. Google Cloud
Deployment Manager is migration only: never write or extend Deployment Manager configurations;
move them to Infrastructure Manager or Terraform
([gcp-infrastructure-manager.md](reference/gcp-infrastructure-manager.md#deployment-manager-migration-only)).

## Run a change

`<skill>` is this skill's directory. `<plans>` is a folder outside the checkout, one per change,
for example `$HOME/plans/2026-11-22-orders-prod`. Every plan, what-if or change set file goes there:
it can hold sensitive values, so it never goes into the working tree. Each reference gives the
exact commands for each step.
Before the first command, run `mkdir -p <plans>` and
`git -C <plans> rev-parse --is-inside-work-tree`. It must fail ("not a git repository"); if it
succeeds, `<plans>` is inside a checkout (a relative path from a nested root module, or a home
folder kept in git), so choose another folder.

1. **Check identity and state.** CI uses OIDC federation; Terraform state is remote and locked.
   See [reference/identity.md](reference/identity.md). Stop when either is missing.
2. **Test the modules.** Format, validate and run the tool's tests and linters. Fix failures
   before any preview.
3. **Preview** against the target environment. Save the plan file, the what-if JSON or the
   change set description in `<plans>`.
4. **Policy scan.** Run the IaC scan with `scanning-vulnerabilities` and the tool's policy
   command. A failed rule stops the change, or the owner accepts it by name.
5. **Cost.** Run the cost command. Label the number "estimate" and say which usage it assumed.
6. **Summarize.**

   ```bash
   python3 <skill>/scripts/change_summary.py summarize <plans>/plan.json --tool terraform \
     --plan-file <plans>/tfplan
   ```

   It prints the counts, every change (an import too), the destructive changes to stateful
   resources, the ignored and unknown entries and a `Summary digest:` line. Read every line. Add
   `--stateful <type>` for a type that holds data and is not in the list. For Terraform,
   `--plan-file` adds the saved plan file's SHA-256 to the summary and the digest.

   Without the saved plan file (only its JSON), summarize without `--plan-file`: the summary
   prints `Plan file: not bound`, and `verify` refuses it. Label the result "plan file not
   bound", do not apply from it, and ask for the plan file, or preview again into `<plans>`. An
   approval of an unbound digest does not cover an apply. Then give the reference's Apply
   commands verbatim, with the bound digest left as `<digest>`, labelled "not run".
7. **Ask for approval** unless the contract pre-authorizes this exact effect. Show the summary
   exactly as the script printed it, the policy result and the cost estimate. Ask the owner to reply with the full digest; a
   shortened or paraphrased digest is not an approval. Then ask, one at a time, for each
   destructive change and for the unknown entries. With `missioning`, record the digest approval
   and each destructive confirmation as ledger rows; never infer them from chat.

   If the owner refuses a destructive change, first run step 8's `verify` on the saved plan with
   `--confirm-destructive` for the confirmed changes only, and report its exit 1 as the record that
   the gate refuses. Never pass the refused change. `verify` reads only the local file; record
   its SHA-256 before you discard it.
   Then stop: the plan cannot be applied in part. Delete it
   (`aws cloudformation delete-change-set` for a change set; discard the plan file and its JSON
   for Terraform; discard the what-if or preview files for Bicep and Infrastructure Manager),
   change the code, preview again, then summarize and ask again. Never list the apply commands
   for the refused plan.
8. **Verify** the summary just before the apply, with the same file and options:

   ```bash
   python3 <skill>/scripts/change_summary.py verify <plans>/plan.json --tool terraform \
     --plan-file <plans>/tfplan --expect <digest> \
     [--confirm-destructive <address> ...] [--accept-unknown]
   ```

   Pass `--confirm-destructive` only for a change the owner confirmed by name, and
   `--accept-unknown` only after the owner accepted the unknown entries. Exit 1 means stop.
9. **Apply only that plan.** Run exactly the reference's apply command for the previewed plan.
   Do not add, reorder or improvise. If a command fails, stop and report what changed; a retry
   is a new preview, a new summary and a new approval.
10. **Read back.** After the apply ends, run the reference's Read back commands: the deployment
    status, then a new preview. Where they use `summarize --drift`, it must exit 0. Compare what
    you read with the approved summary.
11. **Check drift** on a schedule with the reference's Drift commands. For Terraform, Bicep and
    Infrastructure Manager, preview the unchanged code and run `summarize --drift`; CloudFormation
    has its own drift detection. Drift means something changed outside the code: report it, and
    do not overwrite it without approval.

## Credentials

Credentials never enter the repository, the mission file or chat. Never ask for a key, a
password, a client secret or a connection string, and never repeat one you see. CI signs in
with OIDC federation and short-lived tokens; a person signs in with their own short-lived login.
Plan files and state can hold secrets: keep them in `<plans>`, out of the repository, and
delete `<plans>` after the apply. Details: [reference/identity.md](reference/identity.md).

## Without a shell

When you have no shell (a read-only subagent or a chat-only host), do not run or simulate
the script, and never write a digest by hand. Give the caller the exact command with their path,
for example:

```bash
python3 /path/to/skills/provisioning/scripts/change_summary.py summarize <plans>/plan.json --tool terraform
```

Label the summary `change_summary.py: not run`. You may read the preview and point to the
deletes and replacements you see, but report that as a manual reading. Never approve or apply.

## Report

Report the tool and environment, the counts, the destructive list, the summary digest (and,
for Terraform, the plan file's SHA-256 next to it), who approved it (or the contract clause),
each destructive confirmation, the policy and cost results, the commands run and each read-back
with its evidence. Label every claim without evidence "not
run", "claimed" or "not proven". Never write "verified", "secure" or "compliant" without the
evidence next to it.

## Common rationalizations

| Excuse | Answer |
| --- | --- |
| "It is only staging." | Staging is shared. It needs the contract clause for staging or the owner's approval of the digest |
| "The owner approved the change yesterday." | Approval covers one digest. Summarize again and compare |
| "The replace is just a rename." | A replace of a stateful resource deletes its data. Ask for its own confirmation |
| "The plan is long; the counts are enough." | Read every line, the destructive list first |
| "Apply will show the plan again anyway." | Apply only the previewed plan. An interactive apply makes a new plan |
| "Drift is noise; apply over it." | Drift is someone's change. Report it and get a decision first |
| "I will put the key in a variable for now." | Credentials never enter the repository, the mission file or chat. Use OIDC or a personal login |
| "Deployment Manager already works here." | It is migration only. Move it to Infrastructure Manager or Terraform |

## Red flags

- An apply with no approved summary digest and no contract clause for that environment.
- `terraform apply` without a saved plan file, `-auto-approve` on a fresh plan, or
  `--confirm-destructive` passed without a confirmation by name.
- A delete or replace of a database, bucket, disk or key, with no backup evidence.
- A local state file, `-lock=false`, or `force-unlock` without the owner.
- A key, secret or connection string in a file, a variable, the mission file or the chat.
- A read-back that says "deployed" but shows no command output.

## Adapt it

- **Stateful types:** add a type to `STATEFUL` in `scripts/change_summary.py` and to
  [reference/environments.md](reference/environments.md) together; a test compares them. For one
  run, use `--stateful <type>`.
- **Environments:** write your tiers, owners and change windows into `environments.md`.
- **Policy and cost tools:** swap the commands in the tool reference; keep the step.
- **Another tool (Pulumi, OpenTofu):** OpenTofu uses the Terraform reader (`tofu show -json`).
  For another tool, add a reader to the script with tests, and a reference with the same five
  steps.

## Check your work

- The summary, its digest and the approval (or the contract clause naming the environment) are
  in the report.
- Each destructive change to a stateful resource has its own confirmation, and backup evidence.
- `verify` passed on the file that was applied, just before the apply.
- The commands run equal the reference's commands for that plan.
- The read-back shows `--drift` exit 0, or explains each remaining change.
- No credential appears in the repository, the mission file, the chat or the report.
