#!/bin/bash

# Velocitas Extension Build Script
set -e

echo "🚀 Building Velocitas Extension..."

# Clean previous build
if [ -d "dist" ]; then
    echo "🧹 Cleaning previous build..."
    rm -rf dist
fi

# Run webpack build
echo "📦 Bundling with webpack..."
npm run build

# Copy static files to dist
echo "📋 Copying static files..."
cp manifest.json dist/
cp popup.html dist/
cp styles.css dist/
cp -r icons dist/ 2>/dev/null || echo "⚠️  Icons directory not found, skipping..."

# Create extension package
echo "📦 Creating extension package..."
cd dist
zip -r ../velocitas-extension.zip .
cd ..

echo "✅ Build complete! Extension package: velocitas-extension.zip"
echo "📁 Built files are in the dist/ directory"
echo ""
echo "To load in Chrome:"
echo "1. Open chrome://extensions/"
echo "2. Enable Developer mode"
echo "3. Click 'Load unpacked'"
echo "4. Select the dist/ directory"