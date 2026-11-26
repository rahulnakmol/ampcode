# Bicep and ARM templates

Azure Resource Manager has no saved plan. The what-if operation predicts the changes, and the
deployment makes its own plan when it runs. So build the template once, preview that build, and
run what-if again just before the deployment; `verify` must pass on that last what-if. Sources:
[Bicep what-if](https://learn.microsoft.com/en-us/azure/azure-resource-manager/bicep/deploy-what-if),
[What-if REST result](https://learn.microsoft.com/en-us/rest/api/resources/deployments/what-if),
[Deployment modes](https://learn.microsoft.com/en-us/azure/azure-resource-manager/templates/deployment-modes),
[PSRule for Azure](https://azure.github.io/PSRule.Rules.Azure/),
[ACE](https://github.com/TheCloudTheory/arm-estimator).

## Commands

The examples deploy to a resource group. For a subscription, use `az deployment sub` with
`--location`. `<skill>` is the skill's directory. `<plans>` is a folder outside the checkout, one
per change, for example `$HOME/plans/2026-11-22-orders-prod`: what-if results can hold property
values, so they never go into the working tree. `--output json` makes the file JSON whatever the
user's default output format is.
Before the first command, run `mkdir -p <plans>` and
`git -C <plans> rev-parse --is-inside-work-tree`. It must fail ("not a git repository"); if it
succeeds, `<plans>` is inside a checkout (a relative path from a nested root module, or a home
folder kept in git), so choose another folder.

| Step | Command | Notes |
| --- | --- | --- |
| Test | `az bicep lint --file main.bicep`, `az bicep build --file main.bicep --outfile main.json` | Use `main.json` from here on, so every step reads the same build |
| Preview | `az deployment group what-if --resource-group <rg> --template-file main.json --parameters main.parameters.json --no-pretty-print --output json > <plans>/whatif.json` | Keep the default result format (`FullResourcePayloads`). `ResourceIdOnly` shows `Deploy` for every existing resource |
| Policy | `Assert-PSRule -Module PSRule.Rules.Azure -InputPath . -Format File` | Runs in PowerShell. First set `configuration: { AZURE_PARAMETER_FILE_EXPANSION: true }` in `ps-rule.yaml`, and keep `main.parameters.json` linked to `main.json` (same name, or `metadata.template`). Without expansion PSRule checks only the files, not the Azure resources: if its output does not list the template's resources, it is not a policy result. Checkov and Trivy run through `scanning-vulnerabilities`. Azure Policy also evaluates the deployment; a deny stops it |
| Cost | `azure-cost-estimator main.json <subscription-id> <resource-group> --parameters main.parameters.json` | ACE is a community tool, not Microsoft's. It runs what-if and reads the Azure Retail Prices API. Label its number "estimate" |
| Summary | `python3 <skill>/scripts/change_summary.py summarize <plans>/whatif.json --tool bicep` | Record the summary digest for the approval |
| Apply | `az deployment group what-if --resource-group <rg> --template-file main.json --parameters main.parameters.json --no-pretty-print --output json > <plans>/whatif-final.json`, `python3 <skill>/scripts/change_summary.py verify <plans>/whatif-final.json --tool bicep --expect <digest>`, then `az deployment group create --resource-group <rg> --name <deployment-name> --template-file main.json --parameters main.parameters.json` | What-if again just before the deployment, with the same build and parameters, and deploy only if `verify` passes. Never add `--mode Complete` unless the summary was made from a Complete-mode what-if |
| Read back | `az deployment group show --resource-group <rg> --name <deployment-name> --query properties.provisioningState`, then `az deployment group what-if --resource-group <rg> --template-file main.json --parameters main.parameters.json --no-pretty-print --output json > <plans>/after.json` and `python3 <skill>/scripts/change_summary.py summarize <plans>/after.json --tool bicep --drift` | `Succeeded`, and exit 0 (only `NoChange` and `Ignore`) |
| Drift | `az deployment group what-if --resource-group <rg> --template-file main.json --parameters main.parameters.json --no-pretty-print --output json > <plans>/drift.json`, then `python3 <skill>/scripts/change_summary.py summarize <plans>/drift.json --tool bicep --drift` | Use the build and parameters that were last deployed. Exit 2 lists each resource that differs from the template |

## What the summary maps

| What-if change type | Summary action |
| --- | --- |
| Create | create |
| Modify, Deploy | update |
| Delete | delete |
| NoChange | no-op |
| Ignore | ignored (listed) |
| Unsupported, and any `potentialChanges` entry | unknown (listed; `verify` needs `--accept-unknown`) |

What-if has no replace action. A Modify can still disrupt a stateful resource (for example a
change of tier or redundancy). Read the property changes (`delta`) of each Modify on a stateful
type before you approve.

## Rules

- `Delete` appears only in Complete mode. Complete mode deletes every resource in the resource
  group that the template does not name. Treat a Complete-mode deployment as destructive.
- `Ignore` also appears when what-if reaches its limits for nested templates. Read why each
  resource is ignored; do not assume it is unchanged.
- What-if can report a property change that the deployment does not make (noise). Record each
  one you accept as noise, with the reason, in the report.
- The digest covers each resource's full `before` and `after` payload. If a resource has a
  volatile read-only property (one that Azure changes between two reads, such as a timestamp or
  an etag), the what-if just before the deployment can give a different digest from the approved
  one. Then `verify` refuses: show the new summary and ask for a new approval. Never edit the
  what-if file to make it match. Whether real what-if results carry such properties is not
  proven: no two-run what-if against Azure was made for this skill.
- `--confirm-with-what-if` (`-c`) asks at the prompt. It does not bind the approval to a digest;
  do not use it instead of `verify`.
- Protect stateful resources with a `CanNotDelete` resource lock (see
  [environments.md](environments.md)). A deployment stack with deny settings is another option.
