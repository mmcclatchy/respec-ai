# TestPyPI Publishing Guide

Complete guide for publishing respec-ai to TestPyPI for testing and to PyPI for production.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Account Setup](#account-setup)
3. [API Token Configuration](#api-token-configuration)
4. [Building the Package](#building-the-package)
5. [Publishing to TestPyPI](#publishing-to-testpypi)
6. [Testing the Installation](#testing-the-installation)
7. [Publishing to Production PyPI](#publishing-to-production-pypi)
8. [Version Management](#version-management)
9. [Troubleshooting](#troubleshooting)

---

## Prerequisites

**Required Tools:**
- **uv** - Python package manager ([Install](https://docs.astral.sh/uv/getting-started/installation/))
- **Python 3.13+** - Required by respec-ai
- **Git** - For version control and tagging

**Required Access:**
- Write access to the respec-ai repository
- Maintainer access to PyPI/TestPyPI projects (if publishing)

**Verify Prerequisites:**
```bash
# Check uv
uv --version
# Should show: uv 0.x.x or higher

# Check Python
python --version
# Should show: Python 3.13.x or higher

# Check git
git --version
```

---

## Account Setup

### 1. Create TestPyPI Account

TestPyPI is a separate instance of PyPI for testing package uploads.

1. Go to <https://test.pypi.org/account/register/>
2. Create an account (use a different email than your main PyPI account if desired)
3. Verify your email address
4. Enable 2FA (Two-Factor Authentication) - **Required for API tokens**

### 2. Create PyPI Account (Production)

1. Go to <https://pypi.org/account/register/>
2. Create an account
3. Verify your email address
4. Enable 2FA (Two-Factor Authentication) - **Required for API tokens**

**Important:** TestPyPI and PyPI are completely separate - you need accounts on both.

---

## API Token Configuration

API tokens provide secure authentication for package uploads.

### Option 1: Environment Variables (Recommended)

**For TestPyPI:**
```bash
# Generate token at: https://test.pypi.org/manage/account/token/
# Scope: "Entire account" or "Project: respec-ai"

# Add to your shell profile (~/.zshrc or ~/.bashrc):
export TEST_PYPI_TOKEN='pypi-...'

# Reload shell configuration
source ~/.zshrc  # or ~/.bashrc
```

**For Production PyPI:**
```bash
# Generate token at: https://pypi.org/manage/account/token/
# Scope: "Entire account" or "Project: respec-ai"

# Add to your shell profile:
export PYPI_TOKEN='pypi-...'

# Reload shell configuration
source ~/.zshrc  # or ~/.bashrc
```

**Verify tokens are set:**
```bash
echo $TEST_PYPI_TOKEN  # Should show: pypi-...
echo $PYPI_TOKEN       # Should show: pypi-...
```

---

### Option 2: .pypirc Configuration File

Create `~/.pypirc` with restricted permissions:

```bash
# Create the file
cat > ~/.pypirc << 'EOF'
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-YOUR-PRODUCTION-TOKEN-HERE

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-YOUR-TESTPYPI-TOKEN-HERE
EOF

# Restrict permissions (important for security)
chmod 600 ~/.pypirc
```

**Security Note:** Never commit `.pypirc` to version control!

---

## Building the Package

Before publishing, build the distribution files.

### 1. Prepare the Repository

```bash
# Navigate to repository
cd ~/coding/projects/respec-ai

# Ensure you're on main branch with latest changes
git checkout main
git pull origin main

# Verify working directory is clean
git status
# Should show: "working tree clean"
```

### 2. Update Version Number

Edit `/pyproject.toml`:

```toml
[project]
name = "respec-ai"
version = "0.2.0"  # Update this version number
```

**Version Numbering:**
- **Major.Minor.Patch** (e.g., `0.2.0`)
- **Major** - Breaking changes
- **Minor** - New features, backward compatible
- **Patch** - Bug fixes, backward compatible

For development builds, use `.devN` suffix: `0.2.0.dev1`

### 3. Build the Package

```bash
# Build distribution files
uv build

# Expected output:
# Building sdist: respec-0.2.0.tar.gz
# Building wheel: reRESPEC_AI-0.2.0-py3-none-any.whl
```

**Verify build artifacts:**
```bash
ls -lh dist/
# Should show:
# respec-0.2.0.tar.gz       (source distribution)
# reRESPEC_AI-0.2.0-py3-none-any.whl  (wheel)
```

### 4. Clean Build (If Needed)

If you need to rebuild from scratch:

```bash
# Remove old dist files
rm -rf dist/

# Rebuild
uv build
```

---

## Publishing to TestPyPI

Always test with TestPyPI before publishing to production PyPI.

### 1. Publish to TestPyPI

**Using environment variable:**
```bash
uv publish --token $TEST_PYPI_TOKEN \
  --publish-url https://test.pypi.org/legacy/
```

**Using .pypirc:**
```bash
uv publish --repository testpypi
```

**Expected output:**
```text
Uploading respec-0.2.0.tar.gz
Uploading reRESPEC_AI-0.2.0-py3-none-any.whl
✓ Successfully uploaded respec-ai 0.2.0 to TestPyPI
```

### 2. Verify Upload

1. Visit <https://test.pypi.org/project/respec-ai/>
2. Verify version appears
3. Check that description, links, and metadata are correct

---

## Testing the Installation

Before publishing to production, thoroughly test the TestPyPI package.

### 1. Create Test Environment

```bash
# Create a new test directory
mkdir -p ~/test-respec-ai
cd ~/test-respec-ai

# Create a new uv project
uv init test-project
cd test-project
```

### 2. Install from TestPyPI

```bash
# Install respec-ai from TestPyPI
uv add --index https://test.pypi.org/simple/ respec-ai

# Verify installation
respec-ai --version
# Should show: respec-ai 0.2.0
```

**Note:** TestPyPI may not have all dependencies. If you get dependency errors:

```bash
# Install dependencies from production PyPI, respec-ai from TestPyPI
uv add --index https://test.pypi.org/simple/ \
  --default-index https://pypi.org/simple/ \
  respec-ai
```

### 3. Test All Commands

```bash
# Test help
respec-ai --help

# Test init command
respec-ai init --platform markdown
# Verify: Creates .claude/commands/, .claude/agents/, .respec-ai/

# Test status
respec-ai status
# Verify: Shows correct configuration

# Test validate
respec-ai validate
# Verify: All checks pass

# Test platform change
respec-ai platform linear
respec-ai platform github
respec-ai platform markdown

# Test regenerate
respec-ai regenerate

# Test MCP registration
respec-ai register-mcp --force
```

### 4. Test MCP Server Integration

```bash
# Start Claude Code
claude

# Check MCP server appears
/mcp list
# Should show "respec-ai" with 29+ tools
```

### 5. End-to-End Workflow Test

```bash
# In Claude Code, test complete workflow:
/respec-plan test-feature
/respec-roadmap test-project
/respec-spec test-spec
```

**Verification Checklist:**
- [ ] Package installs without errors
- [ ] All CLI commands execute successfully
- [ ] MCP server registers correctly
- [ ] Project initialization creates all files
- [ ] Commands are available in Claude Code
- [ ] Full workflow completes successfully

---

## Publishing to Production PyPI

Only publish to production after thorough TestPyPI testing.

### 1. Pre-Publication Checklist

**Code:**
- [ ] All tests passing (`uv run pytest`)
- [ ] MyPy type checking passes (`uv run mypy src/`)
- [ ] Linting passes (`uv run ruff check src/`)
- [ ] Git working tree is clean

**Version:**
- [ ] Version number updated in `pyproject.toml`
- [ ] CHANGELOG.md updated with new version
- [ ] README.md accurate and up-to-date

**Testing:**
- [ ] TestPyPI package tested successfully
- [ ] MCP integration verified
- [ ] All CLI commands tested
- [ ] Documentation reviewed

### 2. Create Git Tag

```bash
# Tag the release
git tag -a v0.2.0 -m "Release version 0.2.0"

# Push tag to remote
git push origin v0.2.0

# Verify tag
git tag -l
```

### 3. Publish to Production PyPI

**Using environment variable:**
```bash
uv publish --token $PYPI_TOKEN
```

**Using .pypirc:**
```bash
uv publish --repository pypi
```

**Expected output:**
```text
Uploading respec-0.2.0.tar.gz
Uploading reRESPEC_AI-0.2.0-py3-none-any.whl
✓ Successfully uploaded respec-ai 0.2.0 to PyPI
```

### 4. Verify Production Upload

1. Visit <https://pypi.org/project/respec-ai/>
2. Verify version appears
3. Check all metadata is correct
4. Test installation from production:

```bash
# In a fresh environment
uv add respec-ai
respec-ai --version
```

### 5. Create GitHub Release

1. Go to <https://github.com/mmcclatchy/respec-ai/releases>
2. Click "Draft a new release"
3. Select tag: `v0.2.0`
4. Title: `v0.2.0`
5. Description: Copy from CHANGELOG.md
6. Attach build artifacts (optional): `dist/respec-0.2.0.tar.gz`, `dist/reRESPEC_AI-0.2.0-py3-none-any.whl`
7. Click "Publish release"

---

## Version Management

### Version Workflow

**Development:**
1. Work on features in feature branches
2. Merge to main when ready
3. Update version in `pyproject.toml`
4. Test on TestPyPI
5. Publish to production PyPI
6. Tag release in Git

**Version Numbering:**
- `0.2.0` - First PyPI release
- `0.2.1` - Bug fixes
- `0.3.0` - Remove deprecated code
- `0.4.0` - Add multi-IDE support
- `1.0.0` - Production-ready stable release

### CHANGELOG.md Format

```markdown
# Changelog

## [0.2.0] - 2025-01-XX

### Added
- New features and functionality

### Changed
- Modifications to existing features

### Deprecated
- Features marked for removal

### Removed
- Deleted features

### Fixed
- Bug fixes

### Security
- Security patches
```

---

## Troubleshooting

### Build Errors

**Problem:** `uv build` fails

**Solution:**
```bash
# Check pyproject.toml syntax
cat pyproject.toml | python3 -m json.tool  # Should error if invalid

# Ensure all dependencies are installed
uv sync

# Clean and rebuild
rm -rf dist/ build/ *.egg-info
uv build
```

---

### Upload Errors

**Problem:** `403 Forbidden` when uploading

**Causes:**
1. Invalid API token
2. Wrong repository URL
3. Version already exists
4. Insufficient permissions

**Solution:**
```bash
# Verify token is set
echo $TEST_PYPI_TOKEN

# Check repository URL
# TestPyPI: https://test.pypi.org/legacy/
# PyPI: https://upload.pypi.org/legacy/

# For version conflicts, bump version in pyproject.toml
```

---

### Version Conflicts

**Problem:** Version already exists on PyPI

**Solution:**
```bash
# Once published, versions cannot be re-uploaded
# You must increment the version number

# Edit pyproject.toml:
version = "0.2.1"  # Increment patch version

# Rebuild and republish
rm -rf dist/
uv build
uv publish --token $PYPI_TOKEN
```

---

### Installation from TestPyPI Fails

**Problem:** Dependencies not found

**TestPyPI has incomplete package index. Solution:**
```bash
# Use PyPI for dependencies, TestPyPI for respec-ai
uv add --index https://test.pypi.org/simple/ \
  --default-index https://pypi.org/simple/ \
  respec-ai
```

---

### Token Authentication Fails

**Problem:** Token rejected during upload

**Solution:**
```bash
# Verify token format (should start with "pypi-")
echo $TEST_PYPI_TOKEN

# Check token hasn't expired (regenerate if needed)
# TestPyPI: https://test.pypi.org/manage/account/token/
# PyPI: https://pypi.org/manage/account/token/

# Verify 2FA is enabled on your account
```

---

## Best Practices

### Security

1. **Never commit tokens to Git**
   - Add `.pypirc` to `.gitignore`
   - Use environment variables or secure secrets storage
   - Rotate tokens periodically

2. **Use project-scoped tokens**
   - Create tokens for specific projects, not entire account
   - Limits damage if token is compromised

3. **Enable 2FA**
   - Required for API token creation
   - Adds security layer to your account

### Testing

1. **Always test on TestPyPI first**
   - Catch issues before production
   - Verify metadata and description rendering

2. **Test in clean environment**
   - Use fresh virtual environment
   - Ensures all dependencies are correctly specified

3. **Test complete workflows**
   - Don't just verify package installs
   - Test actual usage scenarios

### Version Control

1. **Tag releases in Git**
   - Provides clear version history
   - Enables easy rollback if needed

2. **Maintain CHANGELOG.md**
   - Documents changes for users
   - Required for GitHub releases

3. **Use semantic versioning**
   - Communicates nature of changes
   - Helps users understand upgrade impact

---

## Quick Reference

### Common Commands

```bash
# Build package
uv build

# Publish to TestPyPI
uv publish --token $TEST_PYPI_TOKEN --publish-url https://test.pypi.org/legacy/

# Publish to PyPI
uv publish --token $PYPI_TOKEN

# Install from TestPyPI
uv add --index https://test.pypi.org/simple/ respec-ai

# Install from PyPI
uv add respec-ai

# Create git tag
git tag -a v0.2.0 -m "Release v0.2.0"
git push origin v0.2.0
```

### Important URLs

- **TestPyPI:** <https://test.pypi.org/>
- **PyPI:** <https://pypi.org/>
- **respec-ai on TestPyPI:** <https://test.pypi.org/project/respec-ai/>
- **respec-ai on PyPI:** <https://pypi.org/project/respec-ai/>
- **GitHub Repository:** <https://github.com/mmcclatchy/respec-ai>
- **GitHub Releases:** <https://github.com/mmcclatchy/respec-ai/releases>
