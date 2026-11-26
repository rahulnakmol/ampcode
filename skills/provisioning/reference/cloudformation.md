# CloudFormation

A change set is CloudFormation's exact plan: executing it makes only the changes it lists. Make
the change set, summarize its description, get the digest approved, check that the change set is
still available, then execute that change set by its ARN. Sources:
[Change sets](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-updating-stacks-changesets.html),
[`DescribeChangeSet`](https://docs.aws.amazon.com/AWSCloudFormation/latest/APIReference/API_DescribeChangeSet.html),
[`ResourceChange`](https://docs.aws.amazon.com/AWSCloudFormation/latest/APIReference/API_ResourceChange.html),
[Drift detection](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-stack-drift.html),
[`estimate-template-cost`](https://docs.aws.amazon.com/cli/latest/reference/cloudformation/estimate-template-cost.html),
[CloudFormation Guard](https://docs.aws.amazon.com/cfn-guard/latest/ug/what-is-guard.html).

## Commands

`<stack>` is the stack name and `<name>` the change set name. `<change-set-arn>` is the change
set's ARN (`ChangeSetId`), which the summary prints as `Change set:`. A change set deleted and
made again under the same name gets a new ARN, so after the summary, address the change set by
its ARN only. `<skill>` is the skill's directory.
`<plans>` is a folder outside the checkout, one per change, for example
`$HOME/plans/2026-11-22-orders-prod`: a change set description can hold parameter and property
values, so it never goes into the working tree.
Before the first command, run `mkdir -p <plans>` and
`git -C <plans> rev-parse --is-inside-work-tree`. It must fail ("not a git repository"); if it
succeeds, `<plans>` is inside a checkout (a relative path from a nested root module, or a home
folder kept in git), so choose another folder.

| Step | Command | Notes |
| --- | --- | --- |
| Test | `cfn-lint template.yaml`, `aws cloudformation validate-template --template-body file://template.yaml` | `taskcat` can test a template in a sandbox account |
| Preview | `aws cloudformation create-change-set --stack-name <stack> --change-set-name <name> --template-body file://template.yaml --parameters file://parameters.json`, `aws cloudformation wait change-set-create-complete --stack-name <stack> --change-set-name <name>`, `aws cloudformation describe-change-set --stack-name <stack> --change-set-name <name> --include-property-values --output json > <plans>/changeset.json` | Add `--change-set-type CREATE` for a new stack, `--capabilities CAPABILITY_NAMED_IAM` when the template makes named IAM resources, and `--include-nested-stacks` for nested stacks |
| Policy | `cfn-guard validate --data template.yaml --rules rules/` | Checkov and Trivy run through `scanning-vulnerabilities`. CloudFormation Hooks can enforce the same rules in the account |
| Cost | `aws cloudformation estimate-template-cost --template-body file://template.yaml --parameters file://parameters.json` | Returns an AWS Pricing Calculator link. Label the number "estimate" |
| Summary | `python3 <skill>/scripts/change_summary.py summarize <plans>/changeset.json --tool cloudformation` | The digest binds the changes with their before and after values, the change set ARN and its `Parameters`. Record the digest and the ARN for the approval |
| Apply | `aws cloudformation describe-change-set --change-set-name <change-set-arn> --include-property-values --output json > <plans>/changeset-final.json`, `python3 <skill>/scripts/change_summary.py verify <plans>/changeset-final.json --tool cloudformation --expect <digest>`, `aws cloudformation execute-change-set --change-set-name <change-set-arn>`, then `aws cloudformation wait stack-update-complete --stack-name <stack>` | Run it only when `ExecutionStatus` in the verified description is `AVAILABLE`. For a new stack, wait with `stack-create-complete` |
| Read back | `aws cloudformation describe-stacks --stack-name <stack> --query "Stacks[0].StackStatus"`, `aws cloudformation describe-stack-events --stack-name <stack> --max-items 20` | `UPDATE_COMPLETE` (or `CREATE_COMPLETE`) and no failed event; then run the Drift commands |
| Drift | `aws cloudformation detect-stack-drift --stack-name <stack>`, `aws cloudformation describe-stack-drift-detection-status --stack-drift-detection-id <id>`, `aws cloudformation describe-stack-resource-drifts --stack-name <stack> --stack-resource-drift-status-filters MODIFIED DELETED` | `IN_SYNC` means no drift. A standard change set compares templates, not the live resources, so `summarize --drift` on it is not the drift check here |

## What the summary maps

| Change set action | Summary action |
| --- | --- |
| Add | create |
| Modify, Replacement `False` | update |
| Modify, Replacement `True` or `Conditional` | replace |
| Remove | delete |
| Import | import |
| Dynamic, SyncWithActual, Modify without Replacement, a nested change set | unknown (listed; `verify` needs `--accept-unknown`) |

The summary shows each `PolicyAction` (for example `Retain` or `ReplaceAndSnapshot`). It still
lists a retained resource as destructive: the stack lets go of it, so confirm it by name.

## Rules

- `Conditional` means the replacement depends on a value known only at execution. Treat it as
  a replace.
- A nested stack has its own change set. Describe and summarize each one; the parent's summary
  lists it as unknown until you do.
- `describe-change-set` can return more than one page (`NextToken`). The script refuses a
  partial description: join the pages first.
- Protect stateful resources with `DeletionPolicy` and `UpdateReplacePolicy` set to `Snapshot`
  or `Retain`, and turn on stack termination protection (see [environments.md](environments.md)).
- Delete a change set you will not execute:
  `aws cloudformation delete-change-set --change-set-name <change-set-arn>`.
