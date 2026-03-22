#!/bin/bash
# Quick status check for bookmark sync pipeline
# Uses bre CLI for config-driven paths

if ! command -v bre &>/dev/null; then
    echo "bre CLI not found. Run: pip install bookmark-research-engine"
    exit 1
fi

# Use bre status for the main info
bre status
