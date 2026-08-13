#!/usr/bin/env bash
# ============================================================
# CivicLens pre-commit secret scanner
#
# Install once as a real git hook:
#   cp scripts/check-secrets.sh .git/hooks/pre-commit
#   chmod +x .git/hooks/pre-commit
#
# Or run manually before every commit:
#   bash scripts/check-secrets.sh
#
# Exit 0 = clean.  Exit 1 = BLOCKED, do not commit.
# Works in Git Bash / MSYS2 on Windows 11.
# ============================================================

set -uo pipefail

RED='\033[0;31m'; YEL='\033[0;33m'; GRN='\033[0;32m'; NC='\033[0m'
FAIL=0

# Files staged for commit (added/copied/modified/renamed only)
STAGED=$(git diff --cached --name-only --diff-filter=ACMR)

if [ -z "$STAGED" ]; then
  echo -e "${GRN}[check-secrets] nothing staged.${NC}"
  exit 0
fi

echo "[check-secrets] scanning $(echo "$STAGED" | wc -l | tr -d ' ') staged file(s)..."

# ------------------------------------------------------------
# 1. Blocked filenames — these must never be staged at all
# ------------------------------------------------------------
BLOCKED_PATTERNS='(^|/)\.env$|(^|/)\.env\.|\.pem$|\.key$|\.p12$|\.pfx$|credentials.*\.json$|service.?account.*\.json$|\.sqlite3?$|\.db$|id_rsa'

while IFS= read -r f; do
  [ -z "$f" ] && continue
  if echo "$f" | grep -Eq "$BLOCKED_PATTERNS"; then
    if [ "$(basename "$f")" != ".env.example" ]; then
      echo -e "${RED}[BLOCKED FILE]${NC} $f"
      FAIL=1
    fi
  fi
done <<< "$STAGED"

# ------------------------------------------------------------
# 2. Content scan — high-confidence secret patterns
# ------------------------------------------------------------
declare -a RULES=(
  "AWS access key|AKIA[0-9A-Z]{16}"
  "OpenAI/Anthropic-style key|(sk|sk-ant)-[A-Za-z0-9_-]{20,}"
  "GitHub token|gh[pousr]_[A-Za-z0-9]{30,}"
  "Google API key|AIza[0-9A-Za-z_-]{35}"
  "Slack token|xox[baprs]-[0-9A-Za-z-]{10,}"
  "Private key block|-----BEGIN [A-Z ]*PRIVATE KEY-----"
  "JWT literal|eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}"
  "Hardcoded secret assignment|(secret_key|api_key|apikey|access_token|auth_token|client_secret|password)[\"' ]*[:=][\"' ]*[A-Za-z0-9_/+@.-]{12,}"
  "DB URL with credentials|(postgres|postgresql|mysql|mongodb)(\+[a-z]+)?://[^:/@ ]+:[^@ ]+@"
  "Google private_key field|\"private_key\"[[:space:]]*:"
)

for f in $STAGED; do
  # skip binaries, lockfiles, and the template itself
  case "$f" in
    *.png|*.jpg|*.jpeg|*.webp|*.gif|*.ico|*.pdf|*.zip|*.pt|*.pth|*.bin|*.safetensors) continue ;;
    *package-lock.json|*yarn.lock|*poetry.lock) continue ;;
    *.env.example|*check-secrets.sh) continue ;;
  esac
  [ -f "$f" ] || continue

  for rule in "${RULES[@]}"; do
    label="${rule%%|*}"
    regex="${rule#*|}"
    hits=$(grep -nEI "$regex" "$f" 2>/dev/null | head -3)
    if [ -n "$hits" ]; then
      echo -e "${RED}[SECRET?]${NC} $label in ${YEL}$f${NC}"
      echo "$hits" | sed 's/^/          /' | cut -c1-160
      FAIL=1
    fi
  done
done

# ------------------------------------------------------------
# 3. Insecure defaults — warn loudly (does not block)
# ------------------------------------------------------------
for f in $STAGED; do
  [ -f "$f" ] || continue
  case "$f" in *.py|*.ts|*.tsx|*.js|*.jsx) ;; *) continue ;; esac

  grep -nEI 'allow_origins[[:space:]]*=[[:space:]]*\[[[:space:]]*"\*"' "$f" 2>/dev/null \
    | sed "s|^|$(printf "${YEL}[WARN]${NC} wildcard CORS  ")$f:|" | cut -c1-160
  grep -nEI 'DEBUG[[:space:]]*=[[:space:]]*True' "$f" 2>/dev/null \
    | sed "s|^|$(printf "${YEL}[WARN]${NC} DEBUG=True     ")$f:|" | cut -c1-160
  grep -nEI 'except[[:space:]]*:[[:space:]]*pass' "$f" 2>/dev/null \
    | sed "s|^|$(printf "${YEL}[WARN]${NC} silent except  ")$f:|" | cut -c1-160
done

# ------------------------------------------------------------
# 4. Oversized files (>2 MB)
# ------------------------------------------------------------
for f in $STAGED; do
  [ -f "$f" ] || continue
  size=$(wc -c < "$f" 2>/dev/null || echo 0)
  if [ "$size" -gt 2097152 ]; then
    echo -e "${YEL}[WARN]${NC} large file $(( size / 1024 ))KB: $f — should this be gitignored?"
  fi
done

# ------------------------------------------------------------
echo
if [ "$FAIL" -ne 0 ]; then
  echo -e "${RED}=============================================="
  echo -e " COMMIT BLOCKED — potential secrets detected."
  echo -e "==============================================${NC}"
  echo "  1. Remove the value from the file."
  echo "  2. Move it to .env (gitignored)."
  echo "  3. Unstage:  git restore --staged <file>"
  echo "  4. If it was ever pushed: ROTATE THE CREDENTIAL. Rewriting"
  echo "     git history does NOT un-leak a key."
  echo
  echo "  Intentional false positive? Bypass ONLY if you are certain:"
  echo "     git commit --no-verify"
  exit 1
fi

echo -e "${GRN}[check-secrets] clean — safe to commit.${NC}"
exit 0
