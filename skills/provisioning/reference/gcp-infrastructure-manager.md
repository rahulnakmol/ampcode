# Google Cloud Infrastructure Manager

Infrastructure Manager runs Terraform for you, in Cloud Build, with a service account and state
that Google keeps. A preview runs `terraform plan`, and its export is a Terraform plan JSON, so
the summary uses the Terraform reader. Infrastructure Manager does not apply a preview: the
apply makes its own plan. So pin the source (a commit, or a Cloud Storage object generation),
the inputs file and the Terraform version, and use the same pins for the preview and the apply.
Sources: [Preview a deployment](https://cloud.google.com/infrastructure-manager/docs/preview-deployment),
[Export and view preview results](https://cloud.google.com/infrastructure-manager/docs/export-view-preview-results),
[`previews create`](https://cloud.google.com/sdk/gcloud/reference/infra-manager/previews/create)
(its synopsis lists `--deployment`, `--service-account`, `--tf-version-constraint`, the source
flags and `--inputs-file`; page updated 27 May 2026),
[`deployments apply`](https://cloud.google.com/sdk/gcloud/reference/infra-manager/deployments/apply),
[`previews export`](https://cloud.google.com/sdk/gcloud/reference/infra-manager/previews/export),
[Deployment Manager deprecation](https://cloud.google.com/deployment-manager/docs/deprecations)
(read 22 November 2026).

## Commands

`<deployment>` is `projects/<project>/locations/<location>/deployments/<id>`. A preview name is
`projects/<project>/locations/<location>/previews/<id>`. Use a new preview ID each time: a
preview ID cannot be created twice. So the Preview, Apply, Read back and Drift steps use four
different names: `<preview>`, `<apply-preview>`, `<after-preview>` and `<drift-preview>`.
`<pins>` stands for the same source and inputs flags in every command: `--service-account=projects/<project>/serviceAccounts/<email>
--git-source-repo=<repo-url> --git-source-directory=<dir> --git-source-ref=<commit-sha>
--inputs-file=<env>.tfvars --tf-version-constraint=<version>`. `<skill>` is the skill's directory.
`<plans>` is a folder outside the checkout, one per change, for example
`$HOME/plans/2026-11-22-orders-prod`: the exported plan holds values in plain text, so it never
goes into the working tree. The export writes the binary plan and its JSON form under the name
you give; `<plans>/preview.json` below means that JSON file (check its name with `ls <plans>`),
and the same goes for `<plans>/apply.json`, `<plans>/after.json` and `<plans>/drift.json`.
Before the first command, run `mkdir -p <plans>` and
`git -C <plans> rev-parse --is-inside-work-tree`. It must fail ("not a git repository"); if it
succeeds, `<plans>` is inside a checkout (a relative path from a nested root module, or a home
folder kept in git), so choose another folder.

| Step | Command | Notes |
| --- | --- | --- |
| Test | `terraform fmt -check -recursive`, `terraform validate`, `terraform test` | Run locally on the same configuration, with a Terraform version that Infrastructure Manager supports |
| Preview | `gcloud infra-manager previews create <preview> --deployment=<deployment> <pins>`, then `gcloud infra-manager previews export <preview> --file=<plans>/preview` | A preview must be `SUCCEEDED` to export |
| Policy | `gcloud beta terraform vet <plans>/preview.json --policy-library=<policy-library-dir>` | Checks the plan JSON against your constraint library. Checkov and Trivy run through `scanning-vulnerabilities`. Organization Policy is also enforced at apply |
| Cost | `infracost breakdown --path <plans>/preview.json` | An estimate from list prices. Label it "estimate" |
| Summary | `python3 <skill>/scripts/change_summary.py summarize <plans>/preview.json --tool infra-manager` | Record the summary digest for the approval |
| Apply | `gcloud infra-manager previews create <apply-preview> --deployment=<deployment> <pins>`, `gcloud infra-manager previews export <apply-preview> --file=<plans>/apply`, `python3 <skill>/scripts/change_summary.py verify <plans>/apply.json --tool infra-manager --expect <digest>`, then `gcloud infra-manager deployments apply <deployment> <pins>` | Just before the apply, preview again with the same pins and a new ID, export it, and apply only if `verify` passes on that new export, as Bicep does. The apply makes its own plan, so a cloud or state change after the approval shows up here as a digest mismatch: then show the new summary and get the new digest approved. Exactly the pins of the verified preview. Never a branch name as `--git-source-ref`: it can move |
| Read back | `gcloud infra-manager deployments describe <deployment> --format="value(state,latestRevision)"`, `gcloud infra-manager previews create <after-preview> --deployment=<deployment> <pins>`, `gcloud infra-manager previews export <after-preview> --file=<plans>/after`, `python3 <skill>/scripts/change_summary.py summarize <plans>/after.json --tool infra-manager --drift` | `ACTIVE`, the new revision, and exit 0 |
| Drift | `gcloud infra-manager previews create <drift-preview> --deployment=<deployment> <pins>`, `gcloud infra-manager resource-drifts list --preview=<drift-preview>`, `gcloud infra-manager previews export <drift-preview> --file=<plans>/drift`, `python3 <skill>/scripts/change_summary.py summarize <plans>/drift.json --tool infra-manager --drift` | Resource drifts are Terraform's `resource_drift`, which the summary lists as changes made outside the tool |

## Rules

- The deployment's service account is the identity that changes resources. Give it only the
  roles the configuration needs, in the target project. People and CI get `roles/config.admin`
  or less, never the service account's roles.
- Keep no secret in the configuration or the inputs file: Infrastructure Manager stores them in
  its Cloud Storage bucket.
- When a preview fails or the apply fails, read the Cloud Build and Terraform logs
  (`gcloud infra-manager revisions describe`), fix the cause and start again from the preview.
- Protect stateful resources with `deletion_protection` where the resource has it, and
  `prevent_destroy` (see [environments.md](environments.md)).

## Deployment Manager: migration only

Google Cloud Deployment Manager reached end of support on 31 March 2026. Google says the service
stops after 30 June 2027. Deployment Manager work is migration only: do not write, extend or
apply a Deployment Manager configuration. Migrate each deployment through the same workflow:

1. Convert the configuration to Terraform with DM Convert, or rewrite it by hand.
2. Import the existing resources into an Infrastructure Manager deployment (or Terraform state).
   The preview after the import must show no create, replace or delete for them.
3. Abandon the Deployment Manager deployment so that it no longer manages the resources, and
   keep them: `gcloud deployment-manager deployments delete <name> --delete-policy=ABANDON`.
   This is an outside effect; it needs the same approval as an apply.
4. Read back: the resources still exist, and a new preview shows no changes.
