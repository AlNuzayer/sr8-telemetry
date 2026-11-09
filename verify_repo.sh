#!/usr/bin/env bash
set -euo pipefail

# Run all checks from the repository's root directory.
cd "$(dirname "$0")"

echo "Checking SR8 telemetry repository..."

# Make sure the Python publisher has valid syntax.
python3 -m py_compile publisher.py
echo "[PASS] Python syntax"

# Check that local device credentials are ignored by Git.
for file in \
    certs/private.pem.key \
    certs/device.pem.crt \
    certs/AmazonRootCA1.pem
do
    if ! git check-ignore -q "$file"; then
        echo "[FAIL] Credential file is not ignored: $file"
        exit 1
    fi
done
echo "[PASS] Device credentials are ignored"

# Check that no certificate or private key is tracked.
if git ls-files | grep -Eiq '(^|/)certs/|\.pem$|\.key$|\.crt$|(^|/)\.env$'; then
    echo "[FAIL] Sensitive-looking files are tracked"
    exit 1
fi
echo "[PASS] No sensitive-looking tracked files"

# Also check filenames in the existing Git history.
if git log --all --name-only --pretty=format: |
    grep -Eiq '(^|/)certs/|\.pem$|\.key$|\.crt$|(^|/)\.env$'; then
    echo "[FAIL] Sensitive-looking files found in Git history"
    exit 1
fi
echo "[PASS] No sensitive-looking files in Git history"

# Confirm the remote repository has a main branch.
if git ls-remote --exit-code --heads origin main >/dev/null; then
    echo "[PASS] GitHub main branch is accessible"
else
    echo "[FAIL] Could not find GitHub main branch"
    exit 1
fi

echo
echo "All repository checks passed."
