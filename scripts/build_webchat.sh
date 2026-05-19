#!/bin/bash
# Build webchat frontend and copy to package directory

set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "========================================="
echo "Building Webchat Frontend"
echo "========================================="

# Build webchat
echo ""
echo "[1/2] Building webchat frontend..."
cd "$REPO_ROOT/webchat"
npm ci
npm run build

# Copy webchat build output
echo "[2/2] Copying webchat build output..."
mkdir -p "$REPO_ROOT/src/qwenpaw/webchat"
cp -R "$REPO_ROOT/webchat/dist/." "$REPO_ROOT/src/qwenpaw/webchat/"

echo ""
echo "========================================="
echo "✓ Build complete!"
echo "========================================="
echo ""
echo "Access URL after running 'qwenpaw app':"
echo "  - Webchat: http://127.0.0.1:8088/webchat"
echo ""
