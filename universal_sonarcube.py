
#!/usr/bin/env python3
"""
Universal SonarQube Configuration Generator

Detects project languages and generates sonar-project.properties.

Usage:
    python universal_sonarcube.py
    python universal_sonarcube.py "D:/devops/demo_game"
    python universal_sonarcube.py "D:/devops/demo_game" --force
"""

import argparse
import re
import sys
from pathlib import Path
from collections import Counter


# --------------------------------------------------
# 1. LANGUAGE DETECTION
# --------------------------------------------------

LANGUAGES = {
    ".java": "Java",
    ".py": "Python",
    ".cs": "C#",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".mjs": "JavaScript",
    ".cjs": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".php": "PHP",
    ".go": "Go",
    ".rs": "Rust",
    ".rb": "Ruby",
    ".kt": "Kotlin",
    ".kts": "Kotlin",
    ".scala": "Scala",
    ".sc": "Scala",
    ".swift": "Swift",
    ".c": "C",
    ".h": "C/C++",
    ".cpp": "C++",
    ".cc": "C++",
    ".cxx": "C++",
    ".hpp": "C++",
    ".hh": "C++",
    ".hxx": "C++",
    ".m": "Objective-C",
    ".mm": "Objective-C++",
    ".dart": "Dart",
    ".vue": "Vue",
    ".svelte": "Svelte",
    ".html": "HTML",
    ".css": "CSS",
    ".scss": "CSS",
    ".less": "CSS",
}

IGNORE_DIRS = {
    ".git", ".svn", ".hg",
    ".venv", "venv", "env",
    "node_modules",
    "__pycache__",
    ".idea", ".vscode",
    "bin", "obj",
    "dist", "build",
    "target",
    "vendor",
    "coverage",
    ".next", ".nuxt",
    ".angular",
    ".terraform",
    ".pytest_cache",
    ".mypy_cache",
    ".gradle",
}

TEST_DIR_NAMES = {
    "test", "tests", "testing",
    "__tests__", "spec", "specs",
}

SOURCE_DIR_NAMES = {
    "src", "app", "lib", "source",
    "sources", "code",
}


# --------------------------------------------------
# 2. PROJECT SCANNER
# --------------------------------------------------

def scan_project(root):

    language_counts = Counter()
    source_files = []
    directories_with_code = set()

    for current, dirs, files in __import__("os").walk(root):

        dirs[:] = [
            d for d in dirs
            if d.lower() not in IGNORE_DIRS
            and not d.startswith(".")
        ]

        current_path = Path(current)

        for filename in files:

            file_path = current_path / filename
            extension = file_path.suffix.lower()

            if extension in LANGUAGES:

                language_counts[LANGUAGES[extension]] += 1
                source_files.append(file_path)

                directories_with_code.add(
                    file_path.parent
                )

    return language_counts, source_files, directories_with_code


# --------------------------------------------------
# 3. DETECT SOURCE DIRECTORIES
# --------------------------------------------------

def is_inside(path, parent):

    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def detect_directories(root, source_files):

    source_roots = []
    test_roots = []

    # Detect conventional source and test directories.

    for directory in root.rglob("*"):

        if not directory.is_dir():
            continue

        relative = directory.relative_to(root)

        if any(part.lower() in IGNORE_DIRS
               or part.startswith(".")
               for part in relative.parts):
            continue

        if directory.name.lower() in TEST_DIR_NAMES:

            if any(is_inside(f, directory)
                   for f in source_files):
                test_roots.append(directory)

        elif directory.name.lower() in SOURCE_DIR_NAMES:

            if any(is_inside(f, directory)
                   for f in source_files):
                source_roots.append(directory)

    # Prefer conventional source directories.

    if source_roots:
        source_roots = [
            p for p in source_roots
            if not any(
                p != other and is_inside(p, other)
                for other in source_roots
            )
        ]

    else:
        # Fall back to directories containing code.
        source_roots = sorted(
            {
                f.parent for f in source_files
                if f.parent != root
                and not any(
                    part.lower() in TEST_DIR_NAMES
                    for part in f.relative_to(root).parts
                )
            },
            key=lambda p: len(p.parts)
        )

        # Remove nested duplicate directories.
        source_roots = [
            p for p in source_roots
            if not any(
                p != other and is_inside(p, other)
                for other in source_roots
            )
        ]

    # If source files exist directly in root,
    # use root and exclude test/generated directories.
    if any(f.parent == root for f in source_files):
        source_roots = [root]

    if not source_roots:
        source_roots = [root]

    return source_roots, test_roots


# --------------------------------------------------
# 4. DETECT COVERAGE REPORTS
# --------------------------------------------------

def find_coverage(root):

    coverage = {}

    candidates = {
        "Python": [
            ("coverage.xml",
             "sonar.python.coverage.reportPaths"),
        ],

        "JavaScript": [
            ("coverage/lcov.info",
             "sonar.javascript.lcov.reportPaths"),
        ],

        "TypeScript": [
            ("coverage/lcov.info",
             "sonar.javascript.lcov.reportPaths"),
        ],

        "Java": [
            ("target/site/jacoco/jacoco.xml",
             "sonar.coverage.jacoco.xmlReportPaths"),
        ],

        "C#": [
            ("coverage.opencover.xml",
             "sonar.cs.opencover.reportsPaths"),
        ],
    }

    for language, reports in candidates.items():

        for filename, property_name in reports:

            report = root / filename

            if report.is_file():
                coverage[property_name] = filename

    return coverage


# --------------------------------------------------
# 5. GENERATE SONARQUBE PROPERTIES
# --------------------------------------------------

def generate_properties(
    root,
    project_key=None,
    project_name=None
):

    languages, files, _ = scan_project(root)

    if not files:
        raise RuntimeError(
            "No supported source-code files detected."
        )

    source_roots, test_roots = detect_directories(
        root, files
    )

    project_name = project_name or root.name

    project_key = project_key or re.sub(
        r"[^A-Za-z0-9_.:-]",
        "_",
        project_name
    )

    def relative_paths(paths):
        return ",".join(
            p.relative_to(root).as_posix()
            if p != root else "."
            for p in paths
        )

    properties = [
        "# Automatically generated by universal_sonarcube.py",
        "",
        "# Project information",
        f"sonar.projectKey={project_key}",
        f"sonar.projectName={project_name}",
        "sonar.sourceEncoding=UTF-8",
        "",
        "# Source directories",
        f"sonar.sources={relative_paths(source_roots)}",
    ]

    # Avoid source/test overlap when root is the source.
    if test_roots and root not in source_roots:
        properties.extend([
            "",
            "# Test directories",
            f"sonar.tests={relative_paths(test_roots)}",
        ])

    properties.extend([
        "",
        "# Exclude generated and dependency folders",
        "sonar.exclusions=" + ",".join([
            "**/.git/**",
            "**/.venv/**",
            "**/venv/**",
            "**/node_modules/**",
            "**/bin/**",
            "**/obj/**",
            "**/dist/**",
            "**/build/**",
            "**/target/**",
            "**/vendor/**",
            "**/coverage/**",
            "**/__pycache__/**",
            "**/.next/**",
            "**/.terraform/**",
        ]),
    ])

    # Language-specific settings where reports exist.
    coverage = find_coverage(root)

    if coverage:
        properties.extend([
            "",
            "# Detected coverage reports",
        ])

        for key, value in coverage.items():
            properties.append(f"{key}={value}")

    return "\n".join(properties) + "\n", languages, files, source_roots, test_roots


# --------------------------------------------------
# 6. MAIN
# --------------------------------------------------

def main():

    parser = argparse.ArgumentParser(
        description="Universal SonarQube properties generator"
    )

    parser.add_argument(
        "project",
        nargs="?",
        default=".",
        help="Project directory to scan"
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing properties file"
    )

    parser.add_argument(
        "--key",
        help="Custom SonarQube project key"
    )

    parser.add_argument(
        "--name",
        help="Custom SonarQube project name"
    )

    args = parser.parse_args()

    root = Path(args.project).resolve()

    if not root.is_dir():
        print(f"ERROR: Project directory not found: {root}")
        sys.exit(1)

    output = root / "sonar-project.properties"

    print("\n==========================================")
    print(" UNIVERSAL SONARQUBE CONFIGURATION TOOL")
    print("==========================================")

    print(f"\nProject: {root}")

    try:

        content, languages, files, sources, tests = (
            generate_properties(
                root,
                args.key,
                args.name
            )
        )

        print("\nDetected languages:")

        for language, count in languages.most_common():
            print(f"  {language}: {count} files")

        print(f"\nTotal source files: {len(files)}")

        print("\nSource directories:")

        for directory in sources:
            print(f"  {directory.relative_to(root) if directory != root else '.'}")

        print("\nTest directories:")

        for directory in tests:
            print(f"  {directory.relative_to(root)}")

        if output.exists() and not args.force:

            print("\nWARNING: sonar-project.properties already exists.")
            print("Existing file was NOT overwritten.")
            print("Use --force to regenerate it.")

            sys.exit(0)

        output.write_text(
            content,
            encoding="utf-8"
        )

        print("\nSUCCESS!")
        print(f"Generated: {output}")

        print("\nNext step:")
        print("1. Review sonar-project.properties")
        print("2. Configure your SonarQube token")
        print("3. Run the appropriate SonarQube scanner")
        print("4. Check your Quality Gate")

    except Exception as error:

        print(f"\nERROR: {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()



