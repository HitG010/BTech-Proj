"""Generate short/references.bib from ../references.bib.

Removes the internal retrieval notes and shortens author lists longer than six
names to the first author and "others", so the short paper's references stay
compact. Edit the parent file and rerun: python make_references.py
"""

import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
HEADER = """% Generated from ../references.bib by make_references.py: retrieval notes removed and
% author lists longer than six names shortened to the first author and others.
% Edit the parent file and rerun the script.
% CLM is an author release/blog; no proceedings or arXiv paper is asserted.
"""


def shorten(match):
    names = [n.strip() for n in match.group(2).split(" and ")]
    if len(names) > 6:
        names = [names[0], "others"]
    return f"{match.group(1)}{' and '.join(names)}{match.group(3)}"


def main():
    text = (HERE.parent / "references.bib").read_text()
    entries = re.findall(r"^@\w+\{.*?^\}", text, re.S | re.M)
    out = []
    for entry in entries:
        entry = re.sub(r"\n\s*note = \{.*?\},?(?=\n)", "", entry)
        entry = re.sub(r",(\n\})$", r"\1", entry)
        entry = re.sub(r"(\n\s*author = \{)(.*?)(\},?\n)", shorten, entry, flags=re.S)
        out.append(entry)
    (HERE / "references.bib").write_text(HEADER + "\n" + "\n\n".join(out) + "\n")
    print(f"{len(out)} entries")


if __name__ == "__main__":
    main()
