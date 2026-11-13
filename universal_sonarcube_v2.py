#!/usr/bin/env python3
r"""Universal SonarQube configuration generator (v2.0).

This script inspects a local project and creates sonar-project.properties.
It does NOT install/run a scanner, generate test coverage, or upload analysis.

Examples (Windows PowerShell):
    python .\universal_sonarcube.py
    python .\universal_sonarcube.py "D:\devops\demo_game" --force
    python .\universal_sonarcube.py . --project-key demo-game --force
    python .\universal_sonarcube.py . --sources "src,app,routes" --tests "tests" --force

Python 3.10+; standard library only.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Iterable

VERSION = "2.0"
DEFAULT_OUTPUT = "sonar-project.properties"
DEFAULT_MAX_FILES = 150_000

# Directories that should not be traversed when counting project source files.
PRUNE_DIRS = {
    ".git", ".svn", ".hg", ".idea", ".vscode", ".vs",
    ".venv", "venv", "env", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", ".tox", "node_modules",
    "bower_components", "vendor", "bin", "obj",
    "dist", "build", "target", "coverage", "htmlcov",
    ".next", ".nuxt", ".angular", ".terraform", ".scannerwork",
    ".sonar", ".gradle", "out", "artifacts", "test-results",
}

THIRD_PARTY_ANCESTORS = {
    "vendor", "node_modules", "bower_components", "third_party",
    "third-party", "external", "jspm_packages",
}

SOURCE_DIR_NAMES = {
    "src", "source", "app", "lib", "pages", "components", "scripts",
    "cmd", "internal", "routes", "controllers", "models", "services",
    "modules", "static", "assets", "templates", "public",
}
TEST_DIR_NAMES = {"test", "tests", "__tests__", "spec", "specs", "androidtest"}

EXTENSION_LANGUAGES = {
    ".java": "Java", ".py": "Python", ".cs": "C#", ".fs": "F#",
    ".vb": "Visual Basic", ".js": "JavaScript", ".jsx": "JavaScript",
    ".mjs": "JavaScript", ".cjs": "JavaScript", ".ts": "TypeScript",
    ".tsx": "TypeScript", ".mts": "TypeScript", ".cts": "TypeScript",
    ".php": "PHP", ".go": "Go", ".rb": "Ruby", ".rs": "Rust",
    ".kt": "Kotlin", ".kts": "Kotlin", ".swift": "Swift",
    ".scala": "Scala", ".sc": "Scala", ".c": "C", ".h": "C/C++",
    ".cc": "C++", ".cpp": "C++", ".cxx": "C++", ".hpp": "C++",
    ".hh": "C++", ".html": "HTML", ".htm": "HTML", ".css": "CSS",
    ".scss": "CSS", ".sass": "CSS", ".less": "CSS", ".vue": "Vue",
    ".svelte": "Svelte", ".xml": "XML", ".yaml": "YAML",
    ".yml": "YAML", ".sql": "SQL", ".dart": "Dart",
    ".ex": "Elixir", ".exs": "Elixir", ".erl": "Erlang",
    ".hrl": "Erlang", ".m": "Objective-C", ".mm": "Objective-C++",
}

MARKER_LANGUAGES = {
    "pom.xml": "Java", "build.gradle": "Java", "build.gradle.kts": "Kotlin",
    "settings.gradle": "Java", "settings.gradle.kts": "Kotlin",
    "requirements.txt": "Python", "pyproject.toml": "Python",
    "Pipfile": "Python", "setup.py": "Python", "setup.cfg": "Python",
    "tsconfig.json": "TypeScript",
    "composer.json": "PHP", "go.mod": "Go", "Cargo.toml": "Rust",
    "Gemfile": "Ruby", "Package.swift": "Swift", "mix.exs": "Elixir",
}

# These patterns are intentionally conservative: exclude common generated or
# dependency content, not ordinary project directories named "static" or "lib".
DEFAULT_EXCLUSIONS = [
    "**/.git/**", "**/.svn/**", "**/.hg/**",
    "**/node_modules/**", "**/bower_components/**", "**/vendor/**",
    "**/.venv/**", "**/venv/**", "**/__pycache__/**",
    "**/.pytest_cache/**", "**/.mypy_cache/**", "**/.ruff_cache/**",
    "**/bin/**", "**/obj/**", "**/dist/**", "**/build/**", "**/target/**",
    "**/coverage/**", "**/htmlcov/**", "**/.next/**", "**/.nuxt/**",
    "**/.angular/**", "**/.terraform/**", "**/.scannerwork/**",
    "**/out/**", "**/artifacts/**", "**/test-results/**",
    "**/*.min.js", "**/*.min.css",
]


def rel_posix(path: Path, root: Path) -> str:
    """Return a project-relative path with forward slashes (also on Windows)."""
    try:
        value = path.relative_to(root).as_posix()
    except ValueError:
        value = path.as_posix()
    return "." if value in {"", "."} else value


def walk_project(root: Path, max_files: int) -> tuple[list[Path], bool]:
    """Walk without descending into generated/dependency folders."""
    files: list[Path] = []
    truncated = False
    prune_lower = {name.lower() for name in PRUNE_DIRS}
    for current, dirs, filenames in os.walk(root, topdown=True, followlinks=False):
        dirs[:] = [
            name for name in dirs
            if name.lower() not in prune_lower and not (Path(current) / name).is_symlink()
        ]
        for filename in filenames:
            path = Path(current) / filename
            files.append(path)
            if len(files) >= max_files:
                truncated = True
                return files, truncated
    return files, truncated


def detect_project_type(root: Path, files: list[Path]) -> str:
    names = {p.name.lower() for p in files}
    suffixes = {p.suffix.lower() for p in files}
    if any(suffix in suffixes for suffix in {".sln", ".csproj", ".vbproj", ".fsproj"}):
        return "dotnet"
    if "settings.gradle" in names or "settings.gradle.kts" in names:
        return "gradle"
    if "build.gradle" in names or "build.gradle.kts" in names or "gradlew" in names:
        return "gradle"
    if "pom.xml" in names or "mvnw" in names:
        return "maven"
    return "cli"


def detect_languages(files: list[Path]) -> tuple[set[str], Counter[str]]:
    languages: set[str] = set()
    counts: Counter[str] = Counter()
    names = {p.name for p in files}
    for marker, language in MARKER_LANGUAGES.items():
        if marker in names:
            if "/" in language:
                languages.update(language.split("/"))
            else:
                languages.add(language)
    for path in files:
        language = EXTENSION_LANGUAGES.get(path.suffix.lower())
        if language:
            languages.add(language)
            counts[language] += 1
    # Refine package.json detection based on actual source extensions.
    if "package.json" in names:
        if counts["TypeScript"]:
            languages.add("TypeScript")
        if counts["JavaScript"]:
            languages.add("JavaScript")
    return languages, counts


def is_under_third_party(path_parts: tuple[str, ...]) -> bool:
    lower = [part.lower() for part in path_parts]
    if any(part in THIRD_PARTY_ANCESTORS for part in lower):
        return True
    # Raphael is commonly checked in alongside legacy static assets. Its own
    # development/test tree is not the application's test suite.
    return any(lower[index:index + 2] == ["static", "raphael"]
               for index in range(max(0, len(lower) - 1)))


def detect_repository_exclusions(root: Path, files: list[Path]) -> list[str]:
    """Add a narrow exclusion when a known vendored tree is actually present."""
    extra: list[str] = []
    for file in files:
        parts = tuple(part.lower() for part in file.relative_to(root).parts)
        if any(parts[index:index + 2] == ("static", "raphael")
               for index in range(max(0, len(parts) - 1))):
            extra.append("**/static/raphael/**")
            break
    return extra


def looks_like_test_file(path: Path) -> bool:
    name = path.name.lower()
    stem = path.stem.lower()
    suffix = path.suffix.lower()
    if suffix in {".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".mts", ".cts"}:
        return bool(re.search(r"(?:^test\.|\.test\.|\.spec\.|\.test$|\.spec$)", name))
    if suffix == ".py":
        return stem.startswith("test_") or stem.endswith("_test")
    if suffix in {".java", ".kt", ".kts", ".scala"}:
        return stem.endswith("test") or stem.endswith("tests") or stem.startswith("test")
    if suffix == ".php":
        return stem.endswith("test") or stem.endswith("tests")
    if suffix == ".go":
        return name.endswith("_test.go")
    if suffix in {".cs", ".fs", ".vb"}:
        return stem.endswith("test") or stem.endswith("tests")
    if suffix in {".rb", ".rs", ".swift", ".dart"}:
        return stem.startswith("test_") or stem.endswith("_test") or stem.endswith("test")
    return False


def detect_test_dirs(root: Path, files: list[Path]) -> list[str]:
    """Only classify test-named folders when they contain credible test files.

    Known Gradle/Maven test layouts are accepted as structural evidence. A
    directory merely named "test" (e.g. a bundled library's dev/test folder)
    is not enough on its own.
    """
    by_dir: dict[str, list[Path]] = {}
    for file in files:
        rel = Path(rel_posix(file, root))
        if rel == Path("."):
            continue
        parts = rel.parts
        if is_under_third_party(parts):
            continue
        for index, part in enumerate(parts[:-1]):
            if part.lower() not in TEST_DIR_NAMES:
                continue
            candidate_parts = parts[: index + 1]
            candidate = PurePosixPath(*candidate_parts).as_posix()
            by_dir.setdefault(candidate, []).append(file)
    accepted: set[str] = set()
    for candidate, descendants in by_dir.items():
        parts = PurePosixPath(candidate).parts
        canonical = any(
            len(parts) >= 2 and parts[index].lower() == "src"
            and parts[index + 1].lower() in {"test", "androidtest"}
            for index in range(len(parts) - 1)
        ) or any(part.lower() == "androidtest" for part in parts)
        has_named_tests = any(looks_like_test_file(p) for p in descendants)
        if canonical or has_named_tests:
            accepted.add(candidate)
    # Keep only outermost test roots; this avoids duplicate nested entries.
    result: list[str] = []
    for candidate in sorted(accepted, key=lambda s: (s.count("/"), s)):
        if not any(parent == "." or candidate.startswith(parent + "/") for parent in result):
            result.append(candidate)
    return result


def has_code_below(directory: Path, files: list[Path]) -> bool:
    prefix = directory
    return any(
        p.suffix.lower() in EXTENSION_LANGUAGES
        and (p == prefix or prefix in p.parents)
        for p in files
    )


def is_ancestor_dir(parent: str, child: str) -> bool:
    if parent == ".":
        return True
    return child == parent or child.startswith(parent.rstrip("/") + "/")


def find_source_dirs(root: Path, files: list[Path], project_type: str,
                     test_dirs: list[str]) -> tuple[list[str], bool]:
    """Infer safe CLI source roots; return (paths, used_root_fallback)."""
    if project_type in {"maven", "gradle", "dotnet"}:
        return [], False  # Native scanners own the project scope.

    tests_lower = {p.lower() for p in TEST_DIR_NAMES}
    candidates: set[str] = set()
    names = {p.name.lower() for p in files}
    has_composer = "composer.json" in names
    has_artisan = (root / "artisan").is_file()

    # Strong framework convention: Laravel-like PHP applications.
    if has_composer and has_artisan:
        for name in ("app", "routes", "database"):
            folder = root / name
            if folder.is_dir() and has_code_below(folder, files):
                candidates.add(name)

    # Use conventional source roots only when they contain actual source files.
    for file in files:
        rel = file.relative_to(root)
        parts = rel.parts[:-1]
        for index, part in enumerate(parts):
            normalized = part.lower()
            if normalized not in SOURCE_DIR_NAMES:
                continue
            if normalized in tests_lower or is_under_third_party(parts[: index + 1]):
                continue
            candidate = PurePosixPath(*parts[: index + 1]).as_posix()
            # Do not pick a source path which is itself inside a detected test tree.
            if any(is_ancestor_dir(test_root, candidate) for test_root in test_dirs):
                continue
            candidates.add(candidate)

    # Prefer conventional source roots if found. Collapse descendants under a
    # selected parent, such as src/components -> src.
    candidate_list = sorted(candidates, key=lambda s: (s.count("/"), s))
    selected: list[str] = []
    for candidate in candidate_list:
        if not any(is_ancestor_dir(parent, candidate) for parent in selected):
            selected.append(candidate)

    # Root-level code is explicitly listed when named roots exist, so it is not
    # necessary to widen the whole analysis scope to ".".
    root_files = [
        rel_posix(p, root) for p in files
        if p.parent == root and p.suffix.lower() in EXTENSION_LANGUAGES
    ]
    selected.extend(sorted(root_files))

    if selected:
        return deduplicate_paths(selected), False

    # Last-resort fallback: use the project root, but do not guess a test scope.
    return ["."], True


def deduplicate_paths(paths: Iterable[str]) -> list[str]:
    result: list[str] = []
    for item in paths:
        normalized = item.replace("\\", "/").strip().strip("/") or "."
        if normalized not in result:
            result.append(normalized)
    return result


def detect_coverage_reports(root: Path, languages: set[str]) -> dict[str, list[str]]:
    """Set coverage properties only for reports that already exist."""
    candidates: dict[str, tuple[str, ...]] = {
        "Python": ("coverage.xml", "coverage/coverage.xml", "reports/coverage.xml"),
        "JavaScript": ("coverage/lcov.info", "lcov.info"),
        "TypeScript": ("coverage/lcov.info", "lcov.info"),
        "PHP": ("coverage/clover.xml", "clover.xml"),
        "Java": ("target/site/jacoco/jacoco.xml", "build/reports/jacoco/test/jacocoTestReport.xml"),
        "Kotlin": ("target/site/jacoco/jacoco.xml", "build/reports/jacoco/test/jacocoTestReport.xml"),
        "Go": ("coverage.out", "coverage/coverage.out"),
        "Dart": ("coverage/lcov.info",),
    }
    properties: dict[str, list[str]] = {}
    keys = {
        "Python": "sonar.python.coverage.reportPaths",
        "JavaScript": "sonar.javascript.lcov.reportPaths",
        "TypeScript": "sonar.javascript.lcov.reportPaths",
        "PHP": "sonar.php.coverage.reportPaths",
        "Java": "sonar.coverage.jacoco.xmlReportPaths",
        "Kotlin": "sonar.coverage.jacoco.xmlReportPaths",
        "Go": "sonar.go.coverage.reportPaths",
        "Dart": "sonar.dart.lcov.reportPaths",
    }
    for language in sorted(languages):
        key = keys.get(language)
        if not key:
            continue
        found = [rel for rel in candidates.get(language, ()) if (root / rel).is_file()]
        if found:
            properties.setdefault(key, [])
            for report in found:
                if report not in properties[key]:
                    properties[key].append(report)
    return properties


def safe_project_key(value: str) -> str:
    key = re.sub(r"[^A-Za-z0-9_.:-]", "_", value.strip())
    return (key or "sonar-project")[:400]


def escape_property(value: str) -> str:
    # Escape Java .properties syntax characters that would alter the key/value.
    return value.replace("\\", "\\\\").replace("\n", " ").replace("\r", " ").replace(":", "\\:").replace("=", "\\=")


def parse_csv_paths(value: str | None, root: Path, label: str) -> list[str] | None:
    if value is None:
        return None
    items = deduplicate_paths(part.strip() for part in value.split(",") if part.strip())
    if not items:
        raise ValueError(f"--{label} was provided but contains no paths")
    for item in items:
        if "*" in item or "?" in item:
            raise ValueError(f"--{label} accepts directories/files, not wildcard patterns: {item}")
        if not (root / item).exists():
            raise ValueError(f"--{label} path does not exist inside the project: {item}")
    return items


def build_properties(root: Path, project_key: str, project_name: str,
                     languages: set[str], project_type: str,
                     source_dirs: list[str], test_dirs: list[str],
                     root_fallback: bool, coverage: dict[str, list[str]],
                     extra_exclusions: list[str]) -> str:
    lines = [
        f"# Generated by universal_sonarcube.py v{VERSION}",
        "# Review this file before analysis. It does not install/run a scanner.",
        "# Paths are relative to this file; sonar.sources/sonar.tests do not accept wildcards.",
        "",
        f"sonar.projectKey={escape_property(project_key)}",
        f"sonar.projectName={escape_property(project_name)}",
        "sonar.sourceEncoding=UTF-8",
        "",
        "# Detected languages are informational; SonarQube selects analyzers from file types.",
        "# Detected: " + (", ".join(sorted(languages)) if languages else "Unknown"),
    ]

    if project_type == "dotnet":
        lines.extend([
            "",
            "# IMPORTANT: .NET project detected.",
            "# SonarScanner for .NET does not support sonar.sources / sonar.tests.",
            "# This file is NOT the .NET scanner's configuration mechanism; move exclusions",
            "# to the .NET scanner/build configuration if needed.",
            "# Use SonarScanner for .NET: begin -> dotnet build/test -> end.",
        ])
    elif project_type in {"maven", "gradle"}:
        integration = "Maven" if project_type == "maven" else "Gradle"
        lines.extend([
            "",
            f"# {integration} build detected: prefer the SonarScanner for {integration}.",
            "# Its build integration derives source/test scope from the build model.",
            "# sonar.sources and sonar.tests are intentionally omitted to avoid overriding it.",
            "# A native build scanner may require the project key to be configured in the build",
            "# or passed on its command line; this CLI properties file may not be consumed by it.",
            "# Move sonar.exclusions into the native build scanner configuration if needed.",
        ])
        if project_type == "gradle" and ("Java" in languages or "Kotlin" in languages):
            lines.append("# Java bytecode compilation is required for Java/Android project analysis.")
    else:
        if source_dirs:
            lines.extend(["", "# Main source scope (auto-detected; verify it matches your application code).",
                          "sonar.sources=" + ",".join(source_dirs)])
        if test_dirs:
            lines.extend(["", "# Test scope (only high-confidence, non-overlapping test roots).",
                          "sonar.tests=" + ",".join(test_dirs)])
        elif root_fallback:
            lines.extend([
                "",
                "# REVIEW REQUIRED: no confident source root was found; sonar.sources is project root.",
                "# Test folders were not auto-classified because this could overlap the root scope.",
                "# Narrow --sources and --tests manually when your repository has dedicated folders.",
            ])

    exclusions = deduplicate_paths(DEFAULT_EXCLUSIONS + extra_exclusions)
    lines.extend([
        "",
        "# Common dependency/generated/minified content exclusions.",
        "sonar.exclusions=" + ",".join(exclusions),
    ])

    if coverage:
        lines.extend(["", "# Coverage properties: emitted only for report files found during generation."])
        for key, paths in sorted(coverage.items()):
            lines.append(f"{key}=" + ",".join(paths))
    else:
        lines.extend([
            "",
            "# No recognized coverage report was found. Generate test coverage first, then set the",
            "# language-specific property documented by SonarQube; do not point it to a missing file.",
        ])

    if "Java" in languages or "Kotlin" in languages:
        lines.extend([
            "",
            "# Java/Kotlin note: Java analysis needs compiled bytecode. Maven/Gradle scanners",
            "# obtain build information from the build; for SonarScanner CLI, configure valid",
            "# sonar.java.binaries paths after compilation (do not guess a path here).",
        ])
    if "PHP" in languages:
        lines.extend([
            "",
            "# PHP coverage, when available, must be Clover XML via sonar.php.coverage.reportPaths.",
        ])
    if "Python" in languages:
        lines.extend([
            "",
            "# Python coverage, when available, must be Cobertura-compatible XML via",
            "# sonar.python.coverage.reportPaths.",
        ])

    lines.extend([
        "",
        "# SECURITY: do not store sonar.token or passwords in this file.",
        "# Use SONAR_TOKEN as an environment variable / CI secret where supported.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Detect project structure and generate a safer SonarQube properties file."
    )
    parser.add_argument("project", nargs="?", default=".", help="Project directory (default: current directory).")
    parser.add_argument("--force", action="store_true", help="Overwrite the output file if it exists.")
    parser.add_argument("--project-key", help="Override the generated SonarQube project key.")
    parser.add_argument("--project-name", help="Override the generated SonarQube project name.")
    parser.add_argument("--sources", help="Manually set comma-separated source directories/files (overrides detection).")
    parser.add_argument("--tests", help="Manually set comma-separated test directories/files (overrides detection).")
    parser.add_argument("--exclude", action="append", default=[], help="Additional sonar.exclusions pattern; may be repeated.")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help=f"Output file name/path (default: {DEFAULT_OUTPUT}).")
    parser.add_argument("--max-files", type=int, default=DEFAULT_MAX_FILES, help="Maximum files to inspect.")
    parser.add_argument("--dry-run", action="store_true", help="Print the generated file without writing it.")
    args = parser.parse_args()

    root = Path(args.project).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        print(f"[ERROR] Project directory does not exist: {root}")
        return 2
    if args.max_files < 1:
        print("[ERROR] --max-files must be greater than zero.")
        return 2

    output = Path(args.output)
    if not output.is_absolute():
        output = root / output
    if output.exists() and not args.force and not args.dry_run:
        print(f"[STOP] {output.name} already exists.")
        print("No file was overwritten. Review it, or rerun with --force.")
        return 1

    print(f"\nSonarQube config generator v{VERSION}")
    print(f"Scanning project: {root}")
    files, truncated = walk_project(root, args.max_files)
    if not files:
        print("[ERROR] No project files found.")
        return 2
    if truncated:
        print(f"[WARN] Scan limit ({args.max_files}) reached; detection may be incomplete.")

    languages, counts = detect_languages(files)
    project_type = detect_project_type(root, files)
    detected_tests = detect_test_dirs(root, files)
    detected_sources, root_fallback = find_source_dirs(root, files, project_type, detected_tests)

    try:
        source_override = parse_csv_paths(args.sources, root, "sources")
        test_override = parse_csv_paths(args.tests, root, "tests")
    except ValueError as exc:
        print(f"[ERROR] {exc}")
        return 2

    if project_type in {"maven", "gradle", "dotnet"} and (source_override or test_override):
        print(f"[WARN] {project_type.upper()} integration normally owns source/test scope; manual paths may not be supported.")
    sources = source_override if source_override is not None else detected_sources
    tests = test_override if test_override is not None else detected_tests

    # Do not emit a test scope that overlaps the source roots.
    if project_type == "cli" and test_override is None:
        safe_tests = [
            test for test in tests
            if not any(is_ancestor_dir(source, test) for source in sources)
        ]
        tests = safe_tests
    if project_type in {"maven", "gradle", "dotnet"} and test_override is None:
        tests = []

    project_key = safe_project_key(args.project_key or root.name)
    project_name = args.project_name or root.name
    coverage = detect_coverage_reports(root, languages)
    repository_exclusions = detect_repository_exclusions(root, files)
    content = build_properties(
        root, project_key, project_name, languages, project_type,
        sources, tests, root_fallback and source_override is None,
        coverage, args.exclude + repository_exclusions,
    )

    print("\n========== DETECTION SUMMARY ==========")
    print(f"Project       : {root.name}")
    print(f"Scanner style  : {project_type.upper() if project_type != 'cli' else 'SONARSCANNER CLI'}")
    print(f"Files inspected: {len(files)}")
    print("Languages      : " + (", ".join(sorted(languages)) if languages else "Unknown"))
    if counts:
        print("\nLanguage file counts:")
        for language, count in counts.most_common():
            print(f"  {language:<18} {count}")
    print("\nSource paths:")
    for path in sources or ["(derived by native build scanner)"]:
        print(f"  - {path}")
    print("Test paths:")
    for path in tests or ["(not set automatically)"]:
        print(f"  - {path}")
    if detected_tests and project_type in {"maven", "gradle"}:
        print("Detected test-layout folders (the native build scanner will classify them):")
        for path in detected_tests:
            print(f"  - {path}")
    if detected_tests and project_type == "cli" and not tests:
        print("[WARN] Test-like folders were found but overlap the source scope; review manually.")
    if repository_exclusions:
        print("Repository-specific exclusions:")
        for pattern in repository_exclusions:
            print(f"  - {pattern}")
    if root_fallback and project_type == "cli" and source_override is None:
        print("[WARN] Root fallback selected. Review scope carefully; use --sources/--tests to narrow it.")
    if project_type == "dotnet":
        print("[INFO] Use SonarScanner for .NET begin/build/end; this properties file is not its config.")
    elif project_type == "maven":
        print("[INFO] Prefer SonarScanner for Maven; its project model supplies source/test scope.")
    elif project_type == "gradle":
        print("[INFO] Prefer SonarScanner for Gradle; compile the project before Java/Android analysis.")
    if coverage:
        print("Coverage reports:")
        for key, paths in sorted(coverage.items()):
            print(f"  - {key}: {', '.join(paths)}")
    else:
        print("Coverage reports : Not detected (no coverage property added)")

    if args.dry_run:
        print("\n========== GENERATED FILE (DRY RUN) ==========")
        print(content)
        print("[DRY RUN] No file written.")
        return 0

    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
    except OSError as exc:
        print(f"[ERROR] Could not write configuration: {exc}")
        return 2

    print(f"\n[SUCCESS] Generated: {output}")
    print("Next: choose the scanner that matches the build system, review the scope, then run analysis.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
