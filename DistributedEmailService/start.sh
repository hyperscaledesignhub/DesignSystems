#!/bin/bash

# Quick Start Script for Distributed Email System
# Simple wrapper around the full demo script
# Usage: ./start.sh [--skip-cleanup]

cd "$(dirname "$0")"
./scripts/start-demo.sh "$@"