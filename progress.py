import argparse
import ast
import os
import re
import sys

BASE_FOLDER = "textures"
README = "README.md"
MAKE_PACK = "make_pack.py"

# Files that exist but aren't finished yet, as paths relative to BASE_FOLDER (without .png).
WIP = {
    "particles",
}

# Groups written on one line in the README, e.g. "- [ ] art, kz"
ONE_LINE = {"art", "font"}

# Things that aren't textures and can't be detected yet.
MANUAL = [
    "Sounds",
    "Music",
]


def load_make_pack_lists():
    """Read the top-level literal assignments from make_pack.py without executing it."""
    with open(MAKE_PACK) as f:
        tree = ast.parse(f.read())
    values = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
            try:
                values[node.targets[0].id] = ast.literal_eval(node.value)
            except ValueError:
                pass
    return values


def build_sections(lists):
    """Return the checklist layout as (name, children) entries.

    A child is either a file path relative to BASE_FOLDER (str) or an atlas
    ("atlas", label, folder, tile names).
    """
    return [
        ("achievement", ["achievement/bg"]),
        ("armor", [f"armor/{n}" for n in ["chain", "cloth", "diamond", "gold", "iron", "power"]]),
        ("art", ["art/kz"]),
        ("environment", [f"environment/{n}" for n in ["clouds", "rain", "snow"]]),
        ("font", [f"font/{n}" for n in lists["fontFiles"]]),
        ("gui", [f"gui/{n}" for n in lists["guiFiles"]]
                + [("atlas", "items.png", "gui/items", list(lists["itemMap"]))]),
        ("item", [f"item/{n}" for n in ["arrows", "boat", "cart", "door", "sign"]]),
        ("misc", [f"misc/{n}" for n in [
            "dial", "foliagecolor", "footprint", "grasscolor", "mapbg", "mapicons",
            "pumpkinblur", "shadow", "vignette", "water", "watercolor",
        ]]),
        ("mob", [f"mob/{n}" for n in lists["mobFiles"]]),
        ("terrain", ["terrain/moon", "terrain/sun"]),
        ("title", [f"title/{n}" for n in ["black", "mclogo", "mojang"]]),
        (None, ["pack.txt", "pack", "particles",
                ("atlas", "terrain.png", "terrain", list(lists["terrainMap"]))]),
    ]


def exists(path):
    if "." not in os.path.basename(path):
        path += ".png"
    return os.path.exists(os.path.join(BASE_FOLDER, path))


def checkbox(done):
    return "[x]" if done else "[ ]"


def render_file(path, indent):
    name = os.path.basename(path)
    done = exists(path) and path not in WIP
    suffix = " (WIP)" if path in WIP and exists(path) else ""
    return f"{indent}- {checkbox(done)} {name}{suffix}"


def render_atlas(label, folder, tiles, indent):
    present = [t for t in tiles if exists(f"{folder}/{t}")]
    done = len(present) == len(tiles)
    status = "" if done else f" (WIP, {len(present)}/{len(tiles)})"
    lines = [f"{indent}- {checkbox(done)} {label}{status}", ""]
    lines.append(f"{indent}  <details><summary>{label} tiles</summary>")
    lines.append("")
    for t in tiles:
        lines.append(f"{indent}  - {checkbox(t in present)} {t}")
    lines.append("")
    lines.append(f"{indent}  </details>")
    lines.append("")
    return lines


def render(sections):
    lines = []
    for name, children in sections:
        indent = ""
        if name is not None:
            if name in ONE_LINE:
                path = children[0]
                lines.append(f"- {checkbox(exists(path))} {name}, {os.path.basename(path)}")
                continue
            lines.append(f"- {name}")
            indent = "  "
        for child in children:
            if isinstance(child, tuple):
                lines.extend(render_atlas(*child[1:], indent))
            else:
                lines.append(render_file(child, indent))
    lines.extend(f"- [ ] {m}" for m in MANUAL)
    return "\n".join(lines)


def find_untracked(sections):
    """List texture files on disk that the checklist doesn't know about."""
    known = set()
    for _, children in sections:
        for child in children:
            if isinstance(child, tuple):
                known.update(f"{child[2]}/{t}.png" for t in child[3])
            else:
                known.add(child if "." in os.path.basename(child) else child + ".png")
    untracked = []
    for root, _, files in os.walk(BASE_FOLDER):
        for f in files:
            rel = os.path.relpath(os.path.join(root, f), BASE_FOLDER).replace(os.sep, "/")
            if rel.endswith(".png") and rel not in known:
                untracked.append(rel)
    return sorted(untracked)


def write_readme(markdown):
    with open(README) as f:
        text = f.read()
    pattern = re.compile(r"(## Progress\n\n).*?(\n\n# )", re.S)
    if not pattern.search(text):
        raise SystemExit("Couldn't find the '## Progress' section in README.md")
    text = pattern.sub(lambda m: m.group(1) + markdown + m.group(2), text, count=1)
    with open(README, "w") as f:
        f.write(text)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--write", action="store_true", help="update README.md in place")
    args = parser.parse_args()

    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    sections = build_sections(load_make_pack_lists())
    markdown = render(sections)

    if args.write:
        write_readme(markdown)
        print(f"Updated {README}")
    else:
        print(markdown)

    untracked = find_untracked(sections)
    if untracked:
        print("\nNot listed in the checklist (add them to make_pack.py?):", file=sys.stderr)
        for path in untracked:
            print(f"  {path}", file=sys.stderr)


if __name__ == "__main__":
    main()
