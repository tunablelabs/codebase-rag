"""
Windows installation script for tree sitter 
Use the below commond to install

# Run as administrator
Set-ExecutionPolicy RemoteSigned
./install_scripts/install_tree_sitter.ps1
"""
# Install tree-sitter CLI
npm install -g tree-sitter-cli

# Create directory
New-Item -ItemType Directory -Force -Path "tree_sitter_libs"
Set-Location "tree_sitter_libs"

# Clone and build parsers
$languages = @("python")
foreach ($lang in $languages) {
    git clone "https://github.com/tree-sitter/tree-sitter-$lang"
    Set-Location "tree-sitter-$lang"
    npm install
    tree-sitter generate
    gcc -o "$lang.so" -shared src/parser.c -I./src
    Set-Location ..
}