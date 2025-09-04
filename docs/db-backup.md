promptyoself DB backup and protection

This document explains how to protect `promptyoself.db` locally and in production.

1. Purpose

The repository intentionally keeps `promptyoself.db` out of version control. The file contains runtime state that accumulates and must be backed up and protected.

2. Local developer guidance

- The repo `.gitignore` includes `*.db` and an explicit `promptyoself.db` entry. Keep it that way.
- To avoid accidental commits, install the sample hook:

  cp hooks/pre-commit.sample .git/hooks/pre-commit
  chmod +x .git/hooks/pre-commit

3. Backups

- Use `scripts/backup_db.sh` for local backups. Example:

  KEEP=14 GPG_RECIPIENT="your@email" scripts/backup_db.sh

- The script copies the DB to `backups/db/` and optionally encrypts with GPG.

4. Production recommendations

- Use an automated scheduled backup with encryption and offsite storage (object storage, SFTP, etc.).
- Use artifact naming with timestamps and environment tags (prod/test).
- Rotate backups and test restores regularly.
- Restrict access to the DB file on the host (chmod 600) and limit which accounts can read it.

5. Restore

- To restore a backup, copy or decrypt the desired file into the repo root as `promptyoself.db` and ensure permissions are `chmod 600`.

6. Security

- Prefer public-key encryption for backups (GPG recipients) or store backups in encrypted cloud buckets.
- Never commit the DB to the git repository or store it in shared source control.
