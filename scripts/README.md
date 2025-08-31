# Scripts Directory

This directory contains utility scripts for repository maintenance and security operations.

## scrub-password-history.sh

**⚠️ DESTRUCTIVE OPERATION** - Helper script for safely removing leaked LETTA_SERVER_PASSWORD from Git history.

**NEVER run this script without first:**
1. Reading the complete guide in `docs/history-scrub.md`
2. Completing all prerequisites listed in that guide
3. Coordinating with all team members

### Usage

```bash
# Make sure you've read docs/history-scrub.md first!
cd /path/to/repository/root
./scripts/scrub-password-history.sh
```

The script will:
- Check prerequisites
- Create backups
- Guide you through safe history rewriting
- Verify the cleanup was successful
- Provide team coordination steps

### Security Note

This script addresses the accidental commit of `LETTA_SERVER_PASSWORD` in commit `1844e70b7f918534896af00e783be7aca596a798`. The password appears in:
- `.env` file
- `Last-session-context.txt` file

Both files are processed to remove the sensitive information while preserving other repository history.