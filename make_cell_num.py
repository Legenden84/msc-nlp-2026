#!/usr/bin/env python3
"""Insert '# cell number <n>' as the first line of every Python code cell in a notebook.
<n> is the cell's position among all cells (markdown included).

Usage:
    python3 number_cells.py notebook.ipynb            # writes notebook_numbered.ipynb
    python3 number_cells.py notebook.ipynb -i         # modifies in place
    python3 number_cells.py notebook.ipynb -o out.ipynb
    python3 number_cells.py notebook.ipynb --print    # inserts print("cell number <n>") instead
"""
import argparse
import json
import re
import sys
from pathlib import Path

MARKER_RE = re.compile(r'^(# cell number \d+|print\("cell number \d+"\))\s*$')

# Cell magics whose body is still Python; the marker goes right after the magic line.
PYTHON_CELL_MAGICS = {"time", "timeit", "capture", "prun", "debug"}


def split_lines(source):
    text = "".join(source) if isinstance(source, list) else source
    return text.splitlines(keepends=True)


def number_cell(lines, marker):
    # Drop an existing marker so reruns don't stack markers.
    if lines and MARKER_RE.match(lines[0].rstrip("\n")):
        lines = lines[1:]
    elif len(lines) > 1 and lines[0].startswith("%%") and MARKER_RE.match(lines[1].rstrip("\n")):
        lines = [lines[0]] + lines[2:]

    if lines and lines[0].startswith("%%"):
        magic = lines[0][2:].split()[0] if lines[0][2:].split() else ""
        if magic not in PYTHON_CELL_MAGICS:
            return None  # %%bash, %%html, etc. -> not Python, leave untouched
        first = lines[0] if lines[0].endswith("\n") else lines[0] + "\n"
        return [first, marker + "\n"] + lines[1:]

    return [marker + ("\n" if lines else "")] + lines


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("notebook", type=Path)
    g = p.add_mutually_exclusive_group()
    g.add_argument("-i", "--in-place", action="store_true", help="overwrite the input notebook")
    g.add_argument("-o", "--output", type=Path, help="output path")
    p.add_argument("--print", dest="use_print", action="store_true",
                   help='insert print("cell number <n>") instead of a comment')
    args = p.parse_args()

    if not args.notebook.is_file():
        sys.exit(f"error: {args.notebook} not found")

    with args.notebook.open(encoding="utf-8") as f:
        nb = json.load(f)

    meta = nb.get("metadata", {})
    lang = (meta.get("language_info", {}).get("name")
            or meta.get("kernelspec", {}).get("language")
            or "python")
    if lang.lower() != "python":
        sys.exit(f"error: notebook language is '{lang}', not python")

    numbered = 0
    for n, cell in enumerate(nb.get("cells", []), start=1):
        # Every cell (markdown, raw, code) counts; only Python code cells get the marker.
        if cell.get("cell_type") != "code":
            continue
        marker = f'print("cell number {n}")' if args.use_print else f"# cell number {n}"
        new_lines = number_cell(split_lines(cell.get("source", "")), marker)
        if new_lines is None:
            continue  # %%bash etc.: counted, not marked
        cell["source"] = new_lines
        numbered += 1

    out = args.notebook if args.in_place else (
        args.output or args.notebook.with_name(args.notebook.stem + "_numbered.ipynb"))

    with out.open("w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1, ensure_ascii=False)
        f.write("\n")

    print(f"numbered {numbered} code cells -> {out}")


if __name__ == "__main__":
    main()