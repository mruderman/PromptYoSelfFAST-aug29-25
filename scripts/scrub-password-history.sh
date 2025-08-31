#!/bin/bash

# Git History Password Scrub Helper Script
# This script helps safely remove leaked LETTA_SERVER_PASSWORD from repository history
# 
# ⚠️  WARNING: This script helps with DESTRUCTIVE operations that rewrite Git history
# ⚠️  Always complete prerequisites in docs/history-scrub.md first

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
LEAKED_PASSWORD="TWIJftq/ufbbxo8w51m/BQ1wBNrZb/JTlmnop"
REPO_URL="https://github.com/mruderman/PromptYoSelfFAST-aug29-25.git"
WORKSPACE_DIR="scrub-workspace.git"
BACKUP_DIR="backup-original.git"

function print_header() {
    echo -e "${BLUE}=================================================${NC}"
    echo -e "${BLUE}  Git History Password Scrub Helper${NC}"
    echo -e "${BLUE}=================================================${NC}"
    echo
}

function print_warning() {
    echo -e "${RED}⚠️  DANGER: DESTRUCTIVE OPERATION AHEAD ⚠️${NC}"
    echo -e "${RED}This will permanently rewrite Git history${NC}"
    echo -e "${RED}All collaborators must re-clone after completion${NC}"
    echo
}

function check_prerequisites() {
    echo -e "${YELLOW}Checking Prerequisites...${NC}"
    
    # Check if git-filter-repo is installed
    if ! command -v git-filter-repo &> /dev/null; then
        echo -e "${RED}❌ git-filter-repo is not installed${NC}"
        echo "Install with: pip install git-filter-repo"
        exit 1
    fi
    echo -e "${GREEN}✅ git-filter-repo is installed${NC}"
    
    # Check if we're in the right directory
    if [[ ! -f ".env" ]] || [[ ! -d ".git" ]]; then
        echo -e "${RED}❌ Must run from repository root containing .env file${NC}"
        exit 1
    fi
    echo -e "${GREEN}✅ Running from repository root${NC}"
    
    # Check if password exists in current files
    if ! grep -q "$LEAKED_PASSWORD" .env; then
        echo -e "${YELLOW}⚠️  Password not found in current .env file${NC}"
        echo "It may have already been removed from working directory"
    else
        echo -e "${RED}🔍 Password found in current .env file${NC}"
    fi
    
    echo
}

function confirm_prerequisites() {
    echo -e "${YELLOW}BEFORE PROCEEDING, CONFIRM YOU HAVE:${NC}"
    echo "1. ✅ Rotated LETTA_SERVER_PASSWORD in Letta server"
    echo "2. ✅ Updated all production/staging environments" 
    echo "3. ✅ Coordinated with all team members"
    echo "4. ✅ Documented all open PRs for recreation"
    echo "5. ✅ Disabled branch protection rules temporarily"
    echo "6. ✅ Scheduled maintenance window"
    echo
    
    read -p "Have you completed ALL prerequisites above? (yes/no): " confirm
    if [[ "$confirm" != "yes" ]]; then
        echo -e "${RED}❌ Please complete prerequisites first. See docs/history-scrub.md${NC}"
        exit 1
    fi
}

function create_backup() {
    echo -e "${YELLOW}Creating full repository backup...${NC}"
    
    if [[ -d "$BACKUP_DIR" ]]; then
        echo -e "${YELLOW}⚠️  Backup directory exists, skipping backup creation${NC}"
        return
    fi
    
    git clone --mirror "$REPO_URL" "$BACKUP_DIR"
    echo -e "${GREEN}✅ Backup created at $BACKUP_DIR${NC}"
    echo
}

function setup_workspace() {
    echo -e "${YELLOW}Setting up clean workspace for history rewrite...${NC}"
    
    if [[ -d "$WORKSPACE_DIR" ]]; then
        echo -e "${YELLOW}⚠️  Workspace exists, removing old workspace${NC}"
        rm -rf "$WORKSPACE_DIR"
    fi
    
    git clone --mirror "$REPO_URL" "$WORKSPACE_DIR"
    echo -e "${GREEN}✅ Workspace created at $WORKSPACE_DIR${NC}"
    echo
}

function approach_a_remove_env_file() {
    echo -e "${YELLOW}Approach A: Removing entire .env file from history...${NC}"
    
    cd "$WORKSPACE_DIR"
    
    echo "Running: git filter-repo --path .env --invert-paths --force"
    git filter-repo --path .env --invert-paths --force
    
    echo -e "${GREEN}✅ .env file removed from all history${NC}"
    cd ..
}

function approach_b_remove_password_lines() {
    echo -e "${YELLOW}Approach B: Removing only password lines from history...${NC}"
    
    # Create the content filter script
    cat > filter-password.py << 'EOF'
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
EOF
    
    chmod +x filter-password.py
    
    cd "$WORKSPACE_DIR"
    
    # Apply content filter using git-filter-repo
    echo "Running git filter-repo with content filter..."
    git filter-repo --blob-callback "
import subprocess
import sys
if filename in [b'.env', b'Last-session-context.txt']:
    result = subprocess.run([sys.executable, '../filter-password.py'], 
                           input=blob.data, capture_output=True, text=True)
    return result.stdout.encode()
return blob.data
" --force
    
    echo -e "${GREEN}✅ Password lines removed from history${NC}"
    cd ..
}

function verify_cleanup() {
    echo -e "${YELLOW}Verifying password removal...${NC}"
    
    cd "$WORKSPACE_DIR"
    
    # Search for leaked password in all history
    if git log --all -p | grep -q "$LEAKED_PASSWORD"; then
        echo -e "${RED}❌ Password still found in history!${NC}"
        echo "Manual review required before pushing"
        exit 1
    fi
    
    echo -e "${GREEN}✅ Password not found in history${NC}"
    
    # Verify repository integrity
    git fsck --full
    echo -e "${GREEN}✅ Repository integrity verified${NC}"
    
    # Show summary of changes
    echo -e "${BLUE}History Summary:${NC}"
    git log --oneline | head -10
    
    cd ..
}

function push_changes() {
    echo -e "${RED}⚠️  FINAL WARNING ⚠️${NC}"
    echo -e "${RED}About to force-push rewritten history to origin${NC}"
    echo -e "${RED}This cannot be undone without restoring from backup${NC}"
    echo
    
    read -p "Proceed with force-push? (type 'FORCE PUSH' to confirm): " confirm
    if [[ "$confirm" != "FORCE PUSH" ]]; then
        echo -e "${YELLOW}❌ Aborted. History rewrite complete but not pushed.${NC}"
        echo "You can manually push later from $WORKSPACE_DIR"
        exit 0
    fi
    
    cd "$WORKSPACE_DIR"
    
    echo -e "${YELLOW}Force-pushing all refs...${NC}"
    git push --force --all
    git push --force --tags
    
    echo -e "${GREEN}✅ History rewrite complete and pushed${NC}"
    cd ..
}

function cleanup_workspace() {
    echo -e "${YELLOW}Cleaning up workspace...${NC}"
    
    read -p "Remove workspace directory $WORKSPACE_DIR? (y/n): " confirm
    if [[ "$confirm" == "y" ]]; then
        rm -rf "$WORKSPACE_DIR"
        echo -e "${GREEN}✅ Workspace cleaned up${NC}"
    fi
    
    echo -e "${BLUE}Backup preserved at: $BACKUP_DIR${NC}"
}

function show_next_steps() {
    echo
    echo -e "${BLUE}=================================================${NC}"
    echo -e "${BLUE}  NEXT STEPS FOR TEAM${NC}"
    echo -e "${BLUE}=================================================${NC}"
    echo
    echo -e "${YELLOW}1. Re-enable branch protection rules${NC}"
    echo -e "${YELLOW}2. Notify all collaborators to re-clone:${NC}"
    echo "   rm -rf PromptYoSelfFAST-aug29-25"
    echo "   git clone https://github.com/mruderman/PromptYoSelfFAST-aug29-25.git"
    echo
    echo -e "${YELLOW}3. Recreate open PRs from documented state${NC}"
    echo -e "${YELLOW}4. Update any automation using old commit SHAs${NC}"
    echo -e "${YELLOW}5. Verify CI/CD pipelines are working${NC}"
    echo
    echo -e "${GREEN}✅ Password leak remediation complete${NC}"
}

# Main execution
function main() {
    print_header
    print_warning
    
    check_prerequisites
    confirm_prerequisites
    
    create_backup
    setup_workspace
    
    echo -e "${BLUE}Choose approach:${NC}"
    echo "A) Remove entire .env file from history (recommended)"
    echo "B) Remove only password lines from files"
    echo
    read -p "Select approach (A/B): " approach
    
    case "$approach" in
        A|a)
            approach_a_remove_env_file
            ;;
        B|b)
            approach_b_remove_password_lines
            ;;
        *)
            echo -e "${RED}❌ Invalid choice${NC}"
            exit 1
            ;;
    esac
    
    verify_cleanup
    push_changes
    cleanup_workspace
    show_next_steps
}

# Run main function if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi