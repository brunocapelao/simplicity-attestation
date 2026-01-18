#!/usr/bin/env python3
"""
Script to rename SAP to SAS across the entire codebase.
This includes:
- Python files (classes, functions, variables)
- Documentation (markdown files)
- Configuration files
- File names
"""

import os
import re
from pathlib import Path
from typing import List, Tuple


def get_all_files(root_dir: str, extensions: List[str]) -> List[Path]:
    """Get all files with specified extensions."""
    files = []
    for ext in extensions:
        files.extend(Path(root_dir).rglob(f"*{ext}"))
    return files


def rename_in_file(file_path: Path) -> Tuple[int, int]:
    """
    Rename SAP to SAS in a file.
    Returns (number of replacements, number of lines changed).
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"❌ Error reading {file_path}: {e}")
        return 0, 0

    original_content = content
    replacements = 0

    # Define replacement patterns
    patterns = [
        # Exact matches (case-sensitive)
        (r'\bSAP\b', 'SAS'),  # Class names, constants
        (r'\bSapConfig\b', 'SasConfig'),  # PascalCase
        (r'\bSAPConfig\b', 'SASConfig'),  # ALL CAPS class

        # String literals (in quotes)
        (r'"SAP"', '"SAS"'),  # Double quotes
        (r"'SAP'", "'SAS'"),  # Single quotes

        # Tags and protocol identifiers
        (r'b"SAP"', 'b"SAS"'),  # Byte strings
        (r"b'SAP'", "b'SAS'"),

        # URLs and paths
        (r'/sap/', '/sas/'),
        (r'_sap_', '_sas_'),
        (r'-sap-', '-sas-'),
        (r'\.sap\.', '.sas.'),

        # Module and package names
        (r'from sdk\.protocols\.sap import', 'from sdk.protocols.sas import'),
        (r'import sdk\.protocols\.sap', 'import sdk.protocols.sas'),
        (r'from sdk\.sap import', 'from sdk.sas import'),
        (r'import sdk\.sap', 'import sdk.sas'),

        # Environment variables
        (r'\bSAP_', 'SAS_'),

        # Comments and docstrings (case-insensitive for natural language)
        (r'SAP SDK', 'SAS SDK'),
        (r'SAP Protocol', 'SAS Protocol'),
        (r'SAP protocol', 'SAS protocol'),
        (r'the SAP', 'the SAS'),
        (r'The SAP', 'The SAS'),

        # Markdown headers and links
        (r'# SAP', '# SAS'),
        (r'## SAP', '## SAS'),
        (r'### SAP', '### SAS'),
        (r'\[SAP\]', '[SAS]'),
        (r'\(SAP\)', '(SAS)'),

        # File extensions and names
        (r'sap\.py', 'sas.py'),
        (r'test_sap', 'test_sas'),
    ]

    # Apply all patterns
    for pattern, replacement in patterns:
        new_content, count = re.subn(pattern, replacement, content)
        if count > 0:
            replacements += count
            content = new_content

    # Special case: "Simplicity Attestation Protocol" should stay as is
    # but the acronym should be SAS
    content = re.sub(
        r'Simplicity Attestation Protocol \(SAP\)',
        'Simplicity Attestation System (SAS)',
        content
    )
    content = re.sub(
        r'Simplicity Attestation Protocol\s*\(SAS\)',
        'Simplicity Attestation System (SAS)',
        content
    )

    # Don't modify if no changes
    if content == original_content:
        return 0, 0

    # Write back
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        lines_changed = len([i for i, (a, b) in enumerate(zip(
            original_content.split('\n'),
            content.split('\n')
        )) if a != b])
        return replacements, lines_changed
    except Exception as e:
        print(f"❌ Error writing {file_path}: {e}")
        return 0, 0


def rename_files(root_dir: str):
    """Rename files and directories containing 'sap' in their names."""
    renamed = []

    # Get all paths that contain 'sap'
    for root, dirs, files in os.walk(root_dir, topdown=False):
        # Rename files first
        for name in files:
            if 'sap' in name.lower():
                old_path = Path(root) / name
                new_name = name.replace('sap', 'sas').replace('SAP', 'SAS')
                new_path = Path(root) / new_name

                if old_path != new_path:
                    try:
                        old_path.rename(new_path)
                        renamed.append((str(old_path), str(new_path)))
                        print(f"✅ Renamed file: {name} → {new_name}")
                    except Exception as e:
                        print(f"❌ Error renaming {old_path}: {e}")

        # Rename directories
        for name in dirs:
            if 'sap' in name.lower():
                old_path = Path(root) / name
                new_name = name.replace('sap', 'sas').replace('SAP', 'SAS')
                new_path = Path(root) / new_name

                if old_path != new_path:
                    try:
                        old_path.rename(new_path)
                        renamed.append((str(old_path), str(new_path)))
                        print(f"✅ Renamed directory: {name} → {new_name}")
                    except Exception as e:
                        print(f"❌ Error renaming {old_path}: {e}")

    return renamed


def main():
    """Main execution."""
    print("=" * 70)
    print("SAP → SAS RENAME SCRIPT")
    print("=" * 70)
    print()

    # Get repository root
    script_dir = Path(__file__).parent
    print(f"📁 Working directory: {script_dir}")
    print()

    # Step 1: Rename content in files
    print("STEP 1: Renaming content in files...")
    print("-" * 70)

    extensions = ['.py', '.md', '.rst', '.txt', '.yaml', '.yml', '.json', '.sh']
    files = get_all_files(str(script_dir), extensions)

    total_replacements = 0
    total_lines_changed = 0
    files_modified = 0

    for file_path in files:
        # Skip this script itself
        if file_path.name == 'rename_sap_to_sas.py':
            continue

        replacements, lines_changed = rename_in_file(file_path)
        if replacements > 0:
            files_modified += 1
            total_replacements += replacements
            total_lines_changed += lines_changed
            print(f"✅ {file_path.relative_to(script_dir)}: "
                  f"{replacements} replacements, {lines_changed} lines changed")

    print()
    print(f"📊 Summary:")
    print(f"   - Files modified: {files_modified}")
    print(f"   - Total replacements: {total_replacements}")
    print(f"   - Total lines changed: {total_lines_changed}")
    print()

    # Step 2: Rename files and directories
    print("STEP 2: Renaming files and directories...")
    print("-" * 70)

    renamed_items = rename_files(str(script_dir))

    print()
    print(f"📊 Summary:")
    print(f"   - Items renamed: {len(renamed_items)}")
    print()

    # Final summary
    print("=" * 70)
    print("✅ RENAME COMPLETE!")
    print("=" * 70)
    print()
    print("Next steps:")
    print("1. Review changes: git diff")
    print("2. Run tests: pytest tests/")
    print("3. Commit changes: git add . && git commit -m 'Rename SAP to SAS'")
    print()


if __name__ == '__main__':
    main()
