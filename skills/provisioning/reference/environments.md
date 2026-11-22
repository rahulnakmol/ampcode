# Environments and stateful resources

## Tiers

Write your own tiers here. The defaults:

| Tier | Shared | An apply runs when | Notes |
| --- | --- | --- | --- |
| Sandbox | No: one person, short-lived | The contract pre-authorizes that exact effect, or the owner approves the summary digest | Own state and identity. Destroy it after use |
| Development | Yes | The contract pre-authorizes applies to this environment by name, or the owner approves the summary digest | Promoted from code merged to the integration branch |
| Test, staging, pre-production | Yes | As development | Production-like. Masked data only |
| Production | Yes | As development, inside the change window | Destructive changes need backup evidence and a tested restore |

When you do not know an environment's tier, treat it as production. Each environment has its
own state, its own identity and its own variables file. Promote the same code through the tiers
in order; a production apply uses code that ran in the tier before it.

## Stateful resources

A stateful resource holds data that a re-create loses. A delete or a replace of one is a
destructive change: it needs its own explicit confirmation (the owner names the resource and
the action, or the contract does), apart from the digest approval. Before you ask, show:

- a backup or snapshot taken for this change, with its ID and time;
- the last tested restore, against the recovery objectives (RPO and RTO) in the design;
- what happens to the data: migrated, retained or lost.

`scripts/change_summary.py` treats these types as stateful (ARM types match without case). Add
yours with `--stateful <type>` for one run, or to `STATEFUL` in the script and to this list
together.

| Cloud | Terraform types | Bicep and ARM, or CloudFormation types |
| --- | --- | --- |
| Azure | `azurerm_storage_account`, `azurerm_mssql_server`, `azurerm_mssql_database`, `azurerm_postgresql_flexible_server`, `azurerm_mysql_flexible_server`, `azurerm_cosmosdb_account`, `azurerm_key_vault`, `azurerm_managed_disk`, `azurerm_redis_cache`, `azurerm_recovery_services_vault` | `Microsoft.Storage/storageAccounts`, `Microsoft.Sql/servers`, `Microsoft.Sql/servers/databases`, `Microsoft.DBforPostgreSQL/flexibleServers`, `Microsoft.DBforMySQL/flexibleServers`, `Microsoft.DocumentDB/databaseAccounts`, `Microsoft.KeyVault/vaults`, `Microsoft.Compute/disks`, `Microsoft.Cache/redis`, `Microsoft.RecoveryServices/vaults` |
| AWS | `aws_db_instance`, `aws_rds_cluster`, `aws_dynamodb_table`, `aws_s3_bucket`, `aws_efs_file_system`, `aws_ebs_volume`, `aws_kms_key`, `aws_elasticache_replication_group`, `aws_opensearch_domain`, `aws_backup_vault` | `AWS::RDS::DBInstance`, `AWS::RDS::DBCluster`, `AWS::DynamoDB::Table`, `AWS::S3::Bucket`, `AWS::EFS::FileSystem`, `AWS::EC2::Volume`, `AWS::KMS::Key`, `AWS::ElastiCache::ReplicationGroup`, `AWS::OpenSearchService::Domain`, `AWS::Backup::BackupVault` |
| Google Cloud | `google_sql_database_instance`, `google_sql_database`, `google_storage_bucket`, `google_bigquery_dataset`, `google_bigquery_table`, `google_spanner_database`, `google_firestore_database`, `google_compute_disk`, `google_filestore_instance`, `google_kms_crypto_key` | Infrastructure Manager uses the Terraform types |

A key vault or KMS key is in the list because deleting it makes the data it encrypts unreadable.

## Protections

Set these once per stateful resource, so a mistake fails before it deletes data.

| Tool | Protection |
| --- | --- |
| Terraform | `lifecycle { prevent_destroy = true }`, and the provider's own flag: `deletion_protection` (AWS RDS, Google Cloud SQL, BigQuery tables), purge protection on Azure Key Vault |
| Bicep | A `CanNotDelete` resource lock (`Microsoft.Authorization/locks`) on the resource or its resource group; soft delete and purge protection where the service has them |
| CloudFormation | `DeletionPolicy` and `UpdateReplacePolicy` set to `Snapshot` (where supported) or `Retain`; stack termination protection; a stack policy that denies `Update:Replace` and `Update:Delete` |
| Infrastructure Manager | As Terraform |

Removing a protection is itself a change through this workflow, with its own confirmation.
