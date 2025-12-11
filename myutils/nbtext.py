import argparse
import nbformat
from nbformat.v4 import new_notebook, new_code_cell, new_markdown_cell


DEFAULT_CODE_SEP = "### --- CODE CELL --- ###"
DEFAULT_MD_SEP = "### --- MARKDOWN CELL --- ###"


def _notebook_to_text_lines(
    nb: nbformat.NotebookNode,
    code_separator: str,
    markdown_separator: str,
) -> list[str]:
    out_lines: list[str] = []

    for cell in nb.cells:
        if cell.cell_type == "code":
            if code_separator:
                out_lines.append(code_separator)

            code_lines = []
            for line in cell.source.splitlines():
                if not line.strip().startswith("# In["):
                    code_lines.append(line)
            out_lines.extend(code_lines)
            out_lines.append("")

        elif cell.cell_type == "markdown":
            if markdown_separator:
                out_lines.append(markdown_separator)

            out_lines.extend(cell.source.splitlines())
            out_lines.append("")

    return out_lines


def notebook_file_to_text(
    ipynb_path: str,
    code_separator: str = DEFAULT_CODE_SEP,
    markdown_separator: str = DEFAULT_MD_SEP,
) -> str:
    """
    Convert a .ipynb file to its nbtext textual representation and return it as a string.
    """
    nb = nbformat.read(ipynb_path, as_version=4)
    out_lines = _notebook_to_text_lines(
        nb=nb,
        code_separator=code_separator,
        markdown_separator=markdown_separator,
    )
    return "\n".join(out_lines)


def notebook_to_text(
    ipynb_path: str,
    txt_path: str,
    code_separator: str = DEFAULT_CODE_SEP,
    markdown_separator: str = DEFAULT_MD_SEP,
) -> None:
    """
    Convert a .ipynb file to a text file on disk.
    """
    text = notebook_file_to_text(
        ipynb_path=ipynb_path,
        code_separator=code_separator,
        markdown_separator=markdown_separator,
    )

    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(text)


def text_to_notebook(
    txt_path: str,
    ipynb_path: str,
    code_separator: str = DEFAULT_CODE_SEP,
    markdown_separator: str = DEFAULT_MD_SEP,
) -> None:
    with open(txt_path, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()

    nb = new_notebook(cells=[])
    current_type = None
    buffer = []

    def flush_buffer():
        nonlocal buffer, current_type
        if not buffer:
            return

        cell_type = current_type or "markdown"
        source = "\n".join(buffer).rstrip()

        if not source.strip():
            buffer = []
            return

        if cell_type == "code":
            nb.cells.append(new_code_cell(source=source))
        else:
            nb.cells.append(new_markdown_cell(source=source))

        buffer = []

    for line in lines:
        if code_separator and line == code_separator:
            flush_buffer()
            current_type = "code"
            continue

        if markdown_separator and line == markdown_separator:
            flush_buffer()
            current_type = "markdown"
            continue

        buffer.append(line)

    flush_buffer()

    with open(ipynb_path, "w", encoding="utf-8") as f:
        nbformat.write(nb, f)


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="nbtext",
        description=(
            "Convert between Jupyter notebooks (.ipynb) and a deterministic text format.\n\n"
            "The text format uses cell separators so that notebooks can be diffed, "
            "reviewed and version-controlled like regular text files."
        ),
        formatter_class=lambda *args, **kwargs: argparse.ArgumentDefaultsHelpFormatter(
            *args,
            **kwargs,
        ),
        epilog=(
            "Examples:\n"
            "  # Convert notebook → text\n"
            "  nbtext to-text notebook.ipynb notebook.txt\n\n"
            "  # Convert text → notebook\n"
            "  nbtext to-notebook notebook.txt notebook.ipynb\n\n"
            "  # Use custom separators\n"
            '  nbtext to-text in.ipynb out.txt '
            '--code-separator "### CODE ###" --markdown-separator "### MD ###"\n'
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # ------------------- to-text -------------------
    to_text = subparsers.add_parser(
        "to-text",
        help="Convert a Jupyter notebook (.ipynb) to a text file.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    to_text.add_argument("ipynb_path", help="Path to input .ipynb file.")
    to_text.add_argument("txt_path", help="Path to output text file.")
    to_text.add_argument(
        "--code-separator",
        default=DEFAULT_CODE_SEP,
        help="Separator line inserted before each code cell.",
    )
    to_text.add_argument(
        "--markdown-separator",
        default=DEFAULT_MD_SEP,
        help="Separator line inserted before each markdown cell.",
    )

    # ------------------- to-notebook -------------------
    to_nb = subparsers.add_parser(
        "to-notebook",
        help="Convert a text file back to a Jupyter notebook (.ipynb).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    to_nb.add_argument("txt_path", help="Path to input text file.")
    to_nb.add_argument("ipynb_path", help="Path to output .ipynb notebook.")
    to_nb.add_argument(
        "--code-separator",
        default=DEFAULT_CODE_SEP,
        help="Separator line that marks the start of a code cell.",
    )
    to_nb.add_argument(
        "--markdown-separator",
        default=DEFAULT_MD_SEP,
        help="Separator line that marks the start of a markdown cell.",
    )

    return parser


def main() -> None:
    parser = _build_arg_parser()
    args = parser.parse_args()

    if args.command == "to-text":
        notebook_to_text(
            ipynb_path=args.ipynb_path,
            txt_path=args.txt_path,
            code_separator=args.code_separator,
            markdown_separator=args.markdown_separator,
        )
    elif args.command == "to-notebook":
        text_to_notebook(
            txt_path=args.txt_path,
            ipynb_path=args.ipynb_path,
            code_separator=args.code_separator,
            markdown_separator=args.markdown_separator,
        )