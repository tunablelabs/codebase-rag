#!/usr/bin/env python3
import os
from pathlib import Path
import argparse
import sys


class DirectoryTreeGenerator:
    def __init__(self, ignore_dirs=None, ignore_files=None, max_depth=None):
        self.ignore_dirs = set(
            ignore_dirs or ['.git', '__pycache__', 'node_modules', '.venv'])
        self.ignore_files = set(ignore_files or ['.DS_Store', '.gitignore'])
        self.max_depth = max_depth

    def generate_tree(self, root_path: str) -> str:
        root = Path(root_path)
        tree_str = [f"📁 {root.name}/"]
        self._generate_tree_recursive(root, "", tree_str, 0)
        return "\n".join(tree_str)

    def _generate_tree_recursive(self, path: Path, prefix: str, tree_str: list, depth: int):
        if self.max_depth is not None and depth >= self.max_depth:
            return

        entries = sorted(list(path.iterdir()), key=lambda x: (
            x.is_file(), x.name.lower()))

        for i, entry in enumerate(entries):
            if entry.name in self.ignore_dirs and entry.is_dir():
                continue
            if entry.name in self.ignore_files and entry.is_file():
                continue

            is_last = i == len(entries) - 1
            current_prefix = "└── " if is_last else "├── "
            next_prefix = "    " if is_last else "│   "

            if entry.is_dir():
                tree_str.append(f"{prefix}{current_prefix}📁 {entry.name}/")
                self._generate_tree_recursive(
                    entry, prefix + next_prefix, tree_str, depth + 1)
            else:
                tree_str.append(f"{prefix}{current_prefix}📄 {entry.name}")


def write_output(content: str, output_file: str = None):
    """Write the tree content to either a file or stdout."""
    if output_file:
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Tree structure has been saved to: {output_file}")
        except Exception as e:
            print(f"Error writing to file {output_file}: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(content)


def main():
    parser = argparse.ArgumentParser(
        description="Generate a directory tree structure")
    parser.add_argument("path", nargs="?", default=".",
                        help="Path to generate tree from")
    parser.add_argument("--max-depth", type=int,
                        help="Maximum depth to traverse")
    parser.add_argument("--ignore-dirs", nargs="+",
                        help="Additional directories to ignore")
    parser.add_argument("--ignore-files", nargs="+",
                        help="Additional files to ignore")
    parser.add_argument(
        "-o", "--output", help="Output file path (if not specified, prints to console)")
    args = parser.parse_args()

    additional_ignore_dirs = args.ignore_dirs or []
    additional_ignore_files = args.ignore_files or []

    tree_generator = DirectoryTreeGenerator(
        ignore_dirs=additional_ignore_dirs,
        ignore_files=additional_ignore_files,
        max_depth=args.max_depth
    )

    try:
        tree_str = tree_generator.generate_tree(args.path)
        write_output(tree_str, args.output)
    except Exception as e:
        print(f"Error generating tree: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
