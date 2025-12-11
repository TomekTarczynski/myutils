import argparse
import os
import fnmatch
from pathlib import Path
from typing import Optional, List

from . import nbtext as _nbtext


def load_exclude_patterns(ignore_file: Optional[str]) -> List[str]:
    """
    Load patterns from a .gitignore-like file.
    Empty lines and lines starting with '#' are ignored.
    """
    if ignore_file is None:
        return []

    path = Path(ignore_file)
    if not path.exists():
        raise FileNotFoundError(f"Ignore file not found: {ignore_file}")

    patterns = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("#"):
                continue
            patterns.append(stripped)
    return patterns


def is_excluded(path: Path, root: Path, patterns: List[str]) -> bool:
    """
    Check whether a relative path matches any exclusion pattern.
    Uses fnmatch for glob-style matching.
    """
    if not patterns:
        return False

    rel = str(path.relative_to(root))

    for pat in patterns:
        # Directory-style patterns: "dir/" means exclude anything inside
        if pat.endswith("/"):
            if rel.startswith(pat[:-1]):
                return True

        # Generic glob-style matching
        if fnmatch.fnmatch(rel, pat):
            return True

    return False


def dump_directory(
    root_path: Optional[str],
    out_path: str,
    include_hidden: bool = False,
    max_files: Optional[int] = None,
    max_file_size: Optional[int] = None,
    exclude_file: Optional[str] = None,
    ipynb_as_text: bool = True,
) -> None:
    """
    Dump a directory tree into a single text file with:
      1. Directory structure
      2. File contents

    Enhancements:
    - If root_path is None, use the current directory.
    - Always exclude the output file itself from structure and contents.
    - When ipynb_as_text is True (default), .ipynb files are converted to nbtext format
      before being written to the dump.
    """
    # Use current directory if root_path is not provided
    root = Path(root_path or ".").resolve()
    out_file_path = Path(out_path).resolve()

    patterns = load_exclude_patterns(exclude_file)

    with open(out_path, "w", encoding="utf-8") as out:
        out.write(f"ROOT: {root}\n")
        out.write("DIRECTORY STRUCTURE:\n")

        # ------------------------ STRUCTURE DUMP -------------------------
        for dirpath, dirnames, filenames in os.walk(root):

            dirpath_p = Path(dirpath)

            # Filter hidden
            if not include_hidden:
                dirnames[:] = [d for d in dirnames if not d.startswith(".")]
                filenames = [f for f in filenames if not f.startswith(".")]

            # Filter excluded directories
            dirnames[:] = [
                d for d in dirnames
                if not is_excluded(dirpath_p / d, root, patterns)
            ]

            # Filter excluded files
            filtered_filenames = []
            for f in filenames:
                full_path = (dirpath_p / f).resolve()
                # Always exclude the output file itself
                if full_path == out_file_path:
                    continue
                if is_excluded(full_path, root, patterns):
                    continue
                filtered_filenames.append(f)
            filenames = filtered_filenames

            rel_dir = Path(dirpath).relative_to(root)
            rel_dir_str = "." if str(rel_dir) == "." else str(rel_dir)

            out.write(f"{rel_dir_str}/\n")
            for fname in filenames:
                out.write(f"{rel_dir_str}/{fname}\n")

        out.write("\n")
        out.write("============================================================\n")
        out.write("FILE CONTENTS\n")
        out.write("============================================================\n")

        # ------------------------ CONTENT DUMP -------------------------
        files_written = 0
        stop = False

        for dirpath, dirnames, filenames in os.walk(root):
            if stop:
                break

            dirpath_p = Path(dirpath)

            # Hidden filters
            if not include_hidden:
                dirnames[:] = [d for d in dirnames if not d.startswith(".")]
                filenames = [f for f in filenames if not f.startswith(".")]

            # Exclusion filters for directories
            dirnames[:] = [
                d for d in dirnames
                if not is_excluded(dirpath_p / d, root, patterns)
            ]

            # Exclusion filters for files (incl. output file)
            filtered_filenames = []
            for f in filenames:
                full_path = (dirpath_p / f).resolve()
                # Always exclude the output file itself
                if full_path == out_file_path:
                    continue
                if is_excluded(full_path, root, patterns):
                    continue
                filtered_filenames.append(f)
            filenames = filtered_filenames

            for fname in filenames:
                if stop:
                    break

                full_path = (dirpath_p / fname).resolve()

                # File size check
                try:
                    size = full_path.stat().st_size
                except OSError:
                    continue

                if max_file_size is not None and size > max_file_size:
                    continue

                # File count limit
                if max_files is not None and files_written >= max_files:
                    stop = True
                    break

                files_written += 1

                rel_path = full_path.relative_to(root)

                out.write("\n")
                out.write("------------------------------------------------------------\n")
                out.write(f"FILE: {rel_path}\n")
                out.write("------------------------------------------------------------\n")

                try:
                    # Special handling for .ipynb files
                    if ipynb_as_text and full_path.suffix == ".ipynb":
                        text = _nbtext.notebook_file_to_text(str(full_path))
                        out.write(text)
                        if not text.endswith("\n"):
                            out.write("\n")
                    else:
                        with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                            for line in f:
                                out.write(line)
                except Exception as e:
                    out.write(f"[ERROR] Could not read file: {e}\n")


def _build_arg_parser() -> argparse.ArgumentParser:
    class _HelpFormatter(
        argparse.RawDescriptionHelpFormatter,
        argparse.ArgumentDefaultsHelpFormatter,
    ):
        """Preserve newlines in description/epilog and show defaults."""
        pass

    parser = argparse.ArgumentParser(
        prog="fsdump",
        description=(
            "Dump a directory structure and file contents into a single text file.\n\n"
            "By default, .ipynb files are converted to a human-readable nbtext format "
            "instead of raw JSON. This makes large notebooks easier to inspect and diff "
            "inside the dump."
        ),
        formatter_class=_HelpFormatter,
        epilog=(
            "Examples:\n"
            "  # Basic usage, current directory → dump.txt\n"
            "  fsdump . dump.txt\n\n"
            "  # Include hidden files and use an ignore file\n"
            "  fsdump . dump.txt --include-hidden --exclude-file .fsdumpignore\n\n"
            "  # Keep .ipynb files as raw JSON instead of nbtext\n"
            "  fsdump project/ dump_raw.txt --raw-ipynb\n"
        ),
    )

    parser.add_argument(
        "root_path",
        nargs="?",
        default=".",
        help="Root directory to traverse.",
    )
    parser.add_argument(
        "out_path",
        help="Output text file path.",
    )
    parser.add_argument(
        "--include-hidden",
        action="store_true",
        help="Include hidden files and directories (names starting with '.').",
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=100,
        help="Maximum number of files to include in the CONTENTS section.",
    )
    parser.add_argument(
        "--max-file-size",
        type=int,
        default=10000,
        help="Maximum size (in bytes) of a single file; larger files are skipped.",
    )
    parser.add_argument(
        "--exclude-file",
        type=str,
        default=None,
        help=(
            "Path to a .gitignore-style file with patterns to exclude from both "
            "structure and contents."
        ),
    )
    parser.add_argument(
        "--raw-ipynb",
        action="store_false",
        dest="ipynb_as_text",
        help="Dump .ipynb files as raw JSON instead of nbtext.",
    )

    return parser




def main() -> None:
    parser = _build_arg_parser()
    args = parser.parse_args()

    dump_directory(
        root_path=args.root_path,
        out_path=args.out_path,
        include_hidden=args.include_hidden,
        max_files=args.max_files,
        max_file_size=args.max_file_size,
        exclude_file=args.exclude_file,
        ipynb_as_text=args.ipynb_as_text,
    )