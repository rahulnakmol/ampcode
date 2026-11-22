# Security review scope: partner payroll file drop

Requested by: Lena Fischer, finance systems owner. Revision reviewed: `payroll-drop` repository
at `9e41c07`, as described below (the repository itself is not provided).

## What the system does

Three payroll partners upload one CSV file each month to our SFTP server. Each file lists the
employees of one client company: full name, employee number, gross salary, bank account number
(IBAN) and tax ID. An import job on our side moves each new file into the payroll database and
emails a summary to the client's finance contact.

## Parts

| Part | Where | Notes |
| --- | --- | --- |
| SFTP server | Public internet, port 22 | One account per partner, SSH key login, password login disabled |
| Upload folder | Disk on the SFTP server | Files stay until the import job moves them |
| Import job | Internal network, runs hourly | Reads the upload folder over an internal share, validates columns, writes rows |
| Payroll database | Internal network | Employees, salaries, bank accounts; finance staff read it through reports |
| Summary email | Our mail relay to the client's finance contact | Row count, total gross pay, list of rejected rows with the reason |

## Known facts

- Partners' public keys were exchanged by email in 2024; no rotation is scheduled.
- The import job logs each rejected row, including the row's content, to a shared log server.
- Lena Fischer owns the payroll risk register. Security findings go to the tracker with IDs
  like `SEC-123`; none has been filed for this system.
- There is no test of the import job's column validation.
- The SFTP server's patch level is not known.
