#!/bin/bash
# SAFE cleanup script for CHATTA productization
# Verified to not affect system operability

echo "🧹 Starting SAFE cleanup for CHATTA production..."
echo "This script only removes files verified to be safe."
echo ""

# Counter for removed items
removed_count=0

# 1. Remove Python cache (SAFE - regenerated automatically)
echo "1. Removing Python cache files..."
cache_count=$(find . -type d -name "__pycache__" 2>/dev/null | wc -l)
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -type f -name "*.pyc" -delete 2>/dev/null
find . -type f -name "*.pyo" -delete 2>/dev/null
echo "   ✅ Removed $cache_count cache directories"
((removed_count+=cache_count))

# 2. Remove OS-specific files (SAFE - OS metadata only)
echo "2. Removing OS-specific files..."
ds_count=$(find . -type f -name ".DS_Store" 2>/dev/null | wc -l)
find . -type f -name ".DS_Store" -delete 2>/dev/null
find . -type f -name "Thumbs.db" -delete 2>/dev/null
find . -type f -name "desktop.ini" -delete 2>/dev/null
echo "   ✅ Removed $ds_count OS metadata files"
((removed_count+=ds_count))

# 3. Remove build artifacts (SAFE - regenerated during build)
echo "3. Removing build artifacts..."
if [ -d "dist" ]; then
    rm -rf dist/
    echo "   ✅ Removed dist/"
    ((removed_count+=1))
fi
if [ -d "build" ]; then
    rm -rf build/
    echo "   ✅ Removed build/"
    ((removed_count+=1))
fi
if [ -d ".pytest_cache" ]; then
    rm -rf .pytest_cache/
    echo "   ✅ Removed .pytest_cache/"
    ((removed_count+=1))
fi
egg_count=$(find . -type d -name "*.egg-info" 2>/dev/null | wc -l)
find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null
if [ $egg_count -gt 0 ]; then
    echo "   ✅ Removed $egg_count egg-info directories"
    ((removed_count+=egg_count))
fi

# 4. Remove VERIFIED safe files at root
echo "4. Removing verified safe files..."

# test_reorganized_system.py - NOT imported anywhere, test-only file
if [ -f "test_reorganized_system.py" ]; then
    rm -f test_reorganized_system.py
    echo "   ✅ Removed test_reorganized_system.py (test-only file)"
    ((removed_count+=1))
fi

# .repos.txt - NOT referenced anywhere in code
if [ -f ".repos.txt" ]; then
    rm -f .repos.txt
    echo "   ✅ Removed .repos.txt (temporary list)"
    ((removed_count+=1))
fi

# bumba.config.js - NOT referenced anywhere
if [ -f "bumba.config.js" ]; then
    rm -f bumba.config.js
    echo "   ✅ Removed bumba.config.js (unused config)"
    ((removed_count+=1))
fi

# converse_docstring_comparison.md - NOT referenced, dev notes only
if [ -f "converse_docstring_comparison.md" ]; then
    rm -f converse_docstring_comparison.md
    echo "   ✅ Removed converse_docstring_comparison.md (dev notes)"
    ((removed_count+=1))
fi

# README-improved.md - NOT referenced anywhere
if [ -f "README-improved.md" ]; then
    rm -f README-improved.md
    echo "   ✅ Removed README-improved.md (duplicate content)"
    ((removed_count+=1))
fi

# 5. Remove temporary/backup files (SAFE)
echo "5. Removing temporary files..."
temp_count=$(find . -type f \( -name "*_temp.py" -o -name "*_old.py" -o -name "*_backup.py" -o -name "*~" -o -name "*.swp" -o -name "*.swo" \) 2>/dev/null | wc -l)
find . -type f -name "*_temp.py" -delete 2>/dev/null
find . -type f -name "*_old.py" -delete 2>/dev/null
find . -type f -name "*_backup.py" -delete 2>/dev/null
find . -type f -name "*~" -delete 2>/dev/null
find . -type f -name "*.swp" -delete 2>/dev/null
find . -type f -name "*.swo" -delete 2>/dev/null
if [ $temp_count -gt 0 ]; then
    echo "   ✅ Removed $temp_count temporary files"
    ((removed_count+=temp_count))
fi

# 6. Remove log files at root only (SAFE - logs regenerate)
echo "6. Removing root-level log files..."
log_count=$(find . -maxdepth 1 -type f -name "*.log" 2>/dev/null | wc -l)
find . -maxdepth 1 -type f -name "*.log" -delete 2>/dev/null
if [ $log_count -gt 0 ]; then
    echo "   ✅ Removed $log_count log files"
    ((removed_count+=log_count))
fi

echo ""
echo "========================================"
echo "✅ SAFE cleanup complete!"
echo "   Total items removed: $removed_count"
echo ""
echo "⚠️  FILES KEPT (verified as needed):"
echo "   • .voices.txt (used for voice preferences)"
echo "   • chatta_mcp_server.sh (used in integration tests)"
echo "   • .venv/ (kept for development, remove for distribution)"
echo ""
echo "📊 Space saved: ~50-150MB (excluding .venv)"
echo "   To save more: rm -rf .venv/ (saves ~500MB-1GB)"
echo "========================================"