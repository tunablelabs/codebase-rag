#!/bin/bash
set -e
chmod +x cleanup.sh
echo "Deleting existing files in /home/ec2-user/codebase-rag..."
rm -rf /home/ec2-user/codebase-rag/*
echo "Cleanup complete."
