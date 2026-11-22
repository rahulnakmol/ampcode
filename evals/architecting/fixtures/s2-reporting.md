# Confirmed brief: finance reporting off SQL Server reports

Confirmed by the finance director, Tomás Ruiz, on 14 November 2026.

## Intent

Finance runs 25 SQL Server Reporting Services reports against the production ERP database.
Month-end reports slow the ERP for everyone and take up to 20 minutes. Finance wants
self-service dashboards with the same numbers, without loading the ERP.

## Behaviour

- Revenue, margin and days sales outstanding (DSO) must match the current reports to the cent
  for closed months.
- Dashboards show data no older than the previous hour during month end.
- Regional managers see only their region.

## Facts

- ERP database: SQL Server 2019, about 400 GB, growing about 60 GB a year.
- 80 report users; up to 30 at the same time at month end.
- The company already licenses Power BI and has a Microsoft Fabric trial capacity.
- One data engineer; the ERP vendor allows read access to a replica, not schema changes.

## Not decided

- Fabric, Azure Databricks or a reporting replica with Power BI.
- How many years of history to load.
