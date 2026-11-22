# Preview fixtures for provisioning

`tests/test_provisioning.py` and `evals/provisioning/` use these files. They hold no credential,
no account key and no connection string; the test scans them for secret patterns (W11.4).
Account, subscription and resource IDs are the documented example values
(`123456789012`, `00000000-0000-0000-0000-000000000001`).

## Real Terraform output (local providers only)

Produced on 22 November 2026 in an Amp orb with Terraform 1.17.2 (`linux_amd64`, the official
release zip, its `SHA256SUMS` file checked with `sha256sum -c` and the HashiCorp signature on
that file checked with `gpg --verify`). The providers were `hashicorp/local` 2.5.3,
`hashicorp/random` 3.7.2 and the built-in `terraform_data`. No cloud provider and no credential
was used. The working folder was a temporary folder under `/tmp`, removed afterwards.

| File | How it was made | Terraform's own line |
| --- | --- | --- |
| `terraform-local-no-changes.json` | Version 1 applied, then planned again unchanged: `terraform plan -out=same.tfplan`, `terraform show -json same.tfplan` | No changes (6 no-op) |
| `terraform-local-plan.json` | Version 2 planned against the version 1 state: `terraform plan -out=change.tfplan`, `terraform show -json change.tfplan` | `Plan: 4 to add, 1 to change, 3 to destroy.` |
| `terraform-local-import.json` | A separate folder with no state and an `import` block, made later on 22 November 2026 for review finding M1: `terraform plan -out=imp.tfplan`, `terraform show -json imp.tfplan` | `Plan: 1 to import, 1 to add, 0 to change, 0 to destroy.` |

The three JSON files were re-indented with `python3 -m json.tool --indent 2`; nothing else changed.

Version 1 of `main.tf` (after the `terraform` block that pins the two providers):

```hcl
resource "terraform_data" "keep_a" { input = "a" }
resource "terraform_data" "keep_b" { input = "b" }
resource "terraform_data" "settings" { input = "v1" }
resource "terraform_data" "old" { input = "retired next" }

resource "local_file" "report" {
  filename = "${path.module}/out/report.txt"
  content  = "report v1\n"
}

resource "random_pet" "name" {
  keepers = { revision = "1" }
  lifecycle { create_before_destroy = true }
}
```

Version 2 changes `settings` to `"v2"` (update in place), `report` to `"report v2\n"`
(replace, delete then create), the `random_pet` keeper to `"2"` (replace, create then delete),
removes `old` (delete) and adds `terraform_data.new` and `local_file.notes` (create).
`keep_a` and `keep_b` stay the same (no-op). By hand: create 2, update 1, replace 2, delete 1,
no-op 2. Terraform's "4 to add" is 2 creates plus 2 replacements; "3 to destroy" is 1 delete
plus 2 replacements.

The import folder's `main.tf` pins only `hashicorp/random` 3.7.2 and holds:

```hcl
import {
  to = random_integer.n
  id = "15,1,50"
}

resource "random_integer" "n" {
  min = 1
  max = 50
}

resource "terraform_data" "marker" { input = "kept" }
```

`random_integer.n` is `["no-op"]` with `importing` set; `terraform_data.marker` is a create. By
hand: import 1, create 1.

## Hand-written samples (not tool output)

Each file below is a **hand-written sample**, written on 22 November 2026 to the documented
schema. No tool produced it and no account was used. It holds every change type the summary
script maps, so a real preview would rarely show all of them at once.

| File | Shape from | What it holds |
| --- | --- | --- |
| `terraform-stateful-sample.json` | Terraform JSON output format, plan and change representations: <https://developer.hashicorp.com/terraform/internals/json-format>. Google Cloud Infrastructure Manager exports a preview as this same Terraform plan JSON: <https://cloud.google.com/infrastructure-manager/docs/export-view-preview-results> | Stateful types on three clouds: `azurerm_mssql_database` replace (delete then create), `google_sql_database_instance` replace (create then delete), `aws_db_instance` delete, `google_storage_bucket` delete; also `azurerm_storage_account` update, `aws_s3_bucket` create, `aws_security_group` delete (not stateful), `google_compute_instance` no-op, a data source read, and one `resource_drift` entry (a tag changed outside Terraform). By hand: create 1, update 1, replace 2, delete 3, no-op 1, read 1; 4 destructive changes to stateful resources |
| `bicep-whatif-sample.json` | Deployments - What If, `WhatIfOperationResult` and the `ChangeType` values: <https://learn.microsoft.com/en-us/rest/api/resources/deployments/what-if>; change types explained: <https://learn.microsoft.com/en-us/azure/azure-resource-manager/bicep/deploy-what-if> | Azure types, one of each change type: Create (storage account), Modify (SQL database), Deploy (web app), Delete (Cosmos DB account, stateful; public IP, not stateful), NoChange (key vault), Ignore (managed disk), Unsupported (app settings, with `unsupportedReason`). It uses the REST shape (`properties.changes`); the script also reads `changes` at the top level. By hand: create 1, update 2, delete 2, no-op 1, ignored 1, unknown 1; 1 destructive change to a stateful resource |
| `cloudformation-changeset-sample.json` | `DescribeChangeSet` output: <https://docs.aws.amazon.com/AWSCloudFormation/latest/APIReference/API_DescribeChangeSet.html>, `ResourceChange`: <https://docs.aws.amazon.com/AWSCloudFormation/latest/APIReference/API_ResourceChange.html>, `ResourceChangeDetail`: <https://docs.aws.amazon.com/AWSCloudFormation/latest/APIReference/API_ResourceChangeDetail.html>, `ResourceTargetDefinition`: <https://docs.aws.amazon.com/AWSCloudFormation/latest/APIReference/API_ResourceTargetDefinition.html> | AWS types: Add (S3 bucket), Modify with Replacement False (Lambda function), Modify with Replacement True (RDS DB instance, policy action `ReplaceAndSnapshot`), Modify with Replacement Conditional (DynamoDB table), Remove (SNS topic, not stateful; S3 bucket with policy action `Retain`). By hand: create 1, update 1, replace 2, delete 2; 3 destructive changes to stateful resources. It has the top-level `ChangeSetId` (ARN) and `Parameters` that the digest binds. Changed on 22 November 2026 after review gate 2 (finding F1): each `Details[].Target` gained `Path`, `BeforeValue`, `AfterValue` and `AttributeChangeType`, the fields that `describe-change-set --include-property-values` returns; the values are hand-written. The counts and the destructive list did not change |
