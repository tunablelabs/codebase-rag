#!/bin/bash

"""
Ubuntu installation script for tree sitter 
Use the below commond to install

# Install Node.js (required for tree-sitter)
sudo apt-get install nodejs npm  # For Ubuntu/Debian

# Make script executable and run
chmod +x scripts/install_tree_sitter.sh
./install_scripts/install_tree_sitter.sh

"""

# Install tree-sitter CLI
npm install -g tree-sitter-cli

# Create tree_sitter_libs directory
mkdir -p tree_sitter_libs
cd tree_sitter_libs

# Clone and build language parsers
for lang in python javascript java; do
    git clone "https://github.com/tree-sitter/tree-sitter-${lang}.git"
    cd "tree-sitter-${lang}"
    npm install
    tree-sitter generate
    gcc -o "parser.so" -shared src/parser.c -I./src -fPIC
    mv parser.so "${lang}.so"
    cd ..
done