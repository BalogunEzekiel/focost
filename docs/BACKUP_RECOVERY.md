# FOCOST Backup & Recovery Baseline

Production backups must be performed outside the application source repository and outside the Super Admin document archive's primary storage.

Minimum controls:
- automated database backups;
- encrypted backup storage;
- separate credentials/access path;
- retention/rotation policy;
- periodic restore test;
- documented Recovery Point Objective (RPO) and Recovery Time Objective (RTO);
- backup integrity verification;
- incident-access procedure;
- no production secrets committed to source control.

The Super Admin document archive may store reference copies of backup reports, restore-test evidence and recovery procedures, but it is not a substitute for independent production backups.
