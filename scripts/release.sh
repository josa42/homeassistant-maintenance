#!/usr/bin/env bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
print_warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

if [ -z "$1" ]; then
    print_error "Usage: $0 <version>"
    print_error "Example: $0 0.4.0"
    exit 1
fi

VERSION=$1
TAG="v${VERSION}"

if ! [[ $VERSION =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    print_error "Invalid version format. Please use semantic versioning (e.g., 0.4.0)"
    exit 1
fi

print_info "Preparing release ${TAG}..."

if ! git rev-parse --git-dir > /dev/null 2>&1; then
    print_error "Not in a git repository"
    exit 1
fi

if ! git diff-index --quiet HEAD --; then
    print_error "Working directory is not clean. Please commit or stash your changes."
    exit 1
fi

CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "main" ]; then
    print_warn "You are not on the main branch (current: ${CURRENT_BRANCH})"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "Aborted"
        exit 1
    fi
fi

print_info "Pulling latest changes..."
git pull origin "$CURRENT_BRANCH"

MANIFEST_FILE="custom_components/maintenance/manifest.json"
if [ ! -f "$MANIFEST_FILE" ]; then
    print_error "Manifest file not found: $MANIFEST_FILE"
    exit 1
fi

print_info "Updating version in manifest.json..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    sed -i '' "s/\"version\": \"[^\"]*\"/\"version\": \"${VERSION}\"/" "$MANIFEST_FILE"
else
    sed -i "s/\"version\": \"[^\"]*\"/\"version\": \"${VERSION}\"/" "$MANIFEST_FILE"
fi

NEW_VERSION=$(grep -o '"version": "[^"]*"' "$MANIFEST_FILE" | cut -d'"' -f4)
if [ "$NEW_VERSION" != "$VERSION" ]; then
    print_error "Failed to update version in manifest.json"
    exit 1
fi
print_info "manifest.json → ${VERSION}"

# Also bump the frontend CARD_VERSION so browsers pick up a fresh bundle.
INIT_FILE="custom_components/maintenance/__init__.py"
CARD_FILE="custom_components/maintenance/www/maintenance-card.js"
if [ -f "$INIT_FILE" ] && [ -f "$CARD_FILE" ]; then
    print_info "Updating CARD_VERSION in ${INIT_FILE} and ${CARD_FILE}..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s/^CARD_VERSION = \"[^\"]*\"/CARD_VERSION = \"${VERSION}\"/" "$INIT_FILE"
        sed -i '' "s/^const CARD_VERSION = \"[^\"]*\"/const CARD_VERSION = \"${VERSION}\"/" "$CARD_FILE"
    else
        sed -i "s/^CARD_VERSION = \"[^\"]*\"/CARD_VERSION = \"${VERSION}\"/" "$INIT_FILE"
        sed -i "s/^const CARD_VERSION = \"[^\"]*\"/const CARD_VERSION = \"${VERSION}\"/" "$CARD_FILE"
    fi
fi

if [ -f "requirements-test.txt" ] && [ -x "/tmp/maint-venv/bin/python" ]; then
    print_info "Running tests..."
    /tmp/maint-venv/bin/python -m pytest tests/
elif command -v pytest &> /dev/null; then
    print_info "Running tests..."
    pytest tests/
else
    print_warn "pytest not found, skipping tests"
fi

print_info "Committing version bump..."
git add "$MANIFEST_FILE" "$INIT_FILE" "$CARD_FILE" 2>/dev/null || git add "$MANIFEST_FILE"
git commit -m "chore: bump version to ${VERSION}"

print_info "Creating tag ${TAG}..."
git tag -a "$TAG" -m "Release ${TAG}"

print_info "Pushing changes and tag..."
git push origin "$CURRENT_BRANCH"
git push origin "$TAG"

print_info ""
print_info "✓ Release ${TAG} created successfully!"
print_info ""
print_info "Next steps:"
print_info "  1. GitHub Actions will automatically create a release with the zip file"
print_info "  2. Go to https://github.com/josa42/homeassistant-maintenance/releases"
print_info "  3. Edit the release notes if needed"
print_info ""
print_info "The integration zip file will be available for HACS installation"
