# Git History Scrub Guide: Removing Leaked LETTA_SERVER_PASSWORD

## ⚠️ **CRITICAL WARNING**

**This operation permanently rewrites Git history and requires force-pushing to the default branch and all tags. This is a destructive operation that cannot be easily undone.**

- **All collaborators must re-clone** the repository after this operation
- **All open pull requests will need to be recreated** 
- **Branch protection rules must be temporarily disabled**
- **CI/CD pipelines may break temporarily**

## Prerequisites (Complete BEFORE starting)

### 1. 🔐 **Rotate the LETTA_SERVER_PASSWORD First**
```bash
# Generate new password in Letta server configuration
# Update all production/staging environments with new password
# Verify all services can connect with new password
```

### 2. 📋 **Coordinate with Team**
- [ ] Notify all collaborators of the upcoming history rewrite
- [ ] Document all open PRs that will need to be recreated
- [ ] Schedule a maintenance window
- [ ] Ensure no critical work is in progress

### 3. 🛡️ **Prepare Repository Protection**
- [ ] Temporarily disable branch protection rules on default branch
- [ ] Note current protection settings to restore later
- [ ] Ensure you have admin access to force-push

### 4. 💾 **Create Safety Backups**
```bash
# Create a full backup of the repository
git clone --mirror https://github.com/mruderman/PromptYoSelfFAST-aug29-25.git backup-original.git

# Export all open PRs and issues for reference
# (Manual step - document all open work)
```

## Approach A: Remove .env File from All History (Recommended)

This approach completely removes the `.env` file from all commits, which is the safest option since `.env` files should never be committed anyway.

### Step 1: Install git-filter-repo
```bash
# Install git-filter-repo if not already available
pip install git-filter-repo
# OR: brew install git-filter-repo
# OR: apt-get install git-filter-repo
```

### Step 2: Create Mirror Clone for History Rewrite
```bash
# Clone as mirror to get all refs
git clone --mirror https://github.com/mruderman/PromptYoSelfFAST-aug29-25.git scrub-workspace.git
cd scrub-workspace.git
```

### Step 3: Remove .env File from All History
```bash
# Remove .env file from all commits
git filter-repo --path .env --invert-paths --force

# Verify the file is gone from history
git log --all --oneline -- .env
# (Should return no results)
```

### Step 4: Verify Leaked Password is Gone
```bash
# Search for the leaked password in all history - should return nothing
git log --all -p | grep -i "TWIJftq/ufbbxo8w51m/BQ1wBNrZb/JTlmnop" || echo "Password not found - good!"

# Also check Last-session-context.txt
git log --all -p -- Last-session-context.txt | grep -i "TWIJftq/ufbbxo8w51m/BQ1wBNrZb/JTlmnop" || echo "Password not found in context file - good!"
```

### Step 5: Push Rewritten History
```bash
# Push all rewritten refs (THIS IS THE DESTRUCTIVE STEP)
git push --force --all
git push --force --tags
```

## Approach B: Remove Only Password Lines (More Precise)

If you need to keep the `.env` file structure but only remove the password, this approach removes specific content.

### Step 1: Create Content Filter
Create a script `filter-password.py`:
```python
#!/usr/bin/env python3
import sys
import re

# Read the file content
content = sys.stdin.read()

# Remove lines containing the leaked password
filtered_content = re.sub(
    r'^LETTA_SERVER_PASSWORD=TWIJftq/ufbbxo8w51m/BQ1wBNrZb/JTlmnop$',
    '# LETTA_SERVER_PASSWORD=<removed-from-history>',
    content,
    flags=re.MULTILINE
)

# Also clean up any documentation references
filtered_content = re.sub(
    r'LETTA_SERVER_PASSWORD=TWIJftq/ufbbxo8w51m/BQ1wBNrZb/JTlmnop',
    'LETTA_SERVER_PASSWORD=<scrubbed>',
    filtered_content
)

sys.stdout.write(filtered_content)
```

### Step 2: Apply Content Filter
```bash
# Make the filter executable
chmod +x filter-password.py

# Apply to .env and Last-session-context.txt files
git filter-repo --blob-callback '
if filename in [b".env", b"Last-session-context.txt"]:
    return subprocess.run([sys.executable, "filter-password.py"], 
                         input=blob.data, capture_output=True).stdout
return blob.data
' --force
```

## Post-Cleanup Steps

### 1. Verify Clean History
```bash
# Verify password is completely gone
git log --all -p | grep -i "TWIJftq/ufbbxo8w51m/BQ1wBNrZb/JTlmnop" || echo "✅ Password scrubbed successfully"

# Check that other content is preserved
git log --oneline | head -10
git show --stat HEAD
```

### 2. Update Current Working Directory
```bash
# Return to your working repository
cd /path/to/original/repo

# Add the scrubbed remote and force-update
git remote add scrubbed file:///path/to/scrub-workspace.git
git fetch scrubbed
git reset --hard scrubbed/main  # or whatever your default branch is
```

### 3. Re-enable Repository Protection
- [ ] Restore branch protection rules
- [ ] Update any automation that depends on specific commit SHAs
- [ ] Verify CI/CD pipelines work with new history

### 4. Coordinate Team Migration
```bash
# Send this to all collaborators:
echo "
⚠️  REPOSITORY HISTORY HAS BEEN REWRITTEN ⚠️

Please follow these steps immediately:

1. Backup any local work:
   git stash push -m 'backup-before-history-scrub'

2. Re-clone the repository:
   cd ..
   rm -rf PromptYoSelfFAST-aug29-25
   git clone https://github.com/mruderman/PromptYoSelfFAST-aug29-25.git

3. Recreate any open PRs from your backup:
   git stash pop  # in your new clone
   # Recreate your branch and PR

4. Update any tools that cache commit SHAs
"
```

## Files Affected

The leaked password appears in these locations in the repository history:
- `.env` file (commit `1844e70b7f918534896af00e783be7aca596a798`)
- `Last-session-context.txt` file (same commit)

### Leak Details
- **Password**: `TWIJftq/ufbbxo8w51m/BQ1wBNrZb/JTlmnop`
- **First appearance**: Commit `1844e70b7f918534896af00e783be7aca596a798`
- **Commit message**: "Merge pull request #1 from mruderman/feature/test-suite-reconstruction"
- **Files affected**: 2 files in the repository history

## Recovery Plan

If something goes wrong during the scrub:

1. **Restore from backup**:
   ```bash
   cd backup-original.git
   git push --mirror https://github.com/mruderman/PromptYoSelfFAST-aug29-25.git
   ```

2. **Generate new password immediately**:
   - Rotate LETTA_SERVER_PASSWORD again
   - Update all environments

3. **Re-plan the approach**:
   - Consider alternative history rewrite strategies
   - Consult with security team if available

## Security Notes

- **Time Sensitivity**: Complete this operation as quickly as possible after password rotation
- **Audit Trail**: Document who performed the operation and when
- **Verification**: Multiple team members should verify the password is completely removed
- **Monitoring**: Watch for any attempts to use the old password in logs

## Support Commands

```bash
# Check if git-filter-repo is installed
git filter-repo --version

# Verify current repository state
git remote -v
git branch -a
git status

# Check repository permissions
git config --list | grep "remote\|user"
```

---

**Remember**: This operation is irreversible. Test the commands on a backup repository first if you're uncertain about any step.