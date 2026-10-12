import argparse
import hashlib
import html
import json
import os
import re
from pathlib import Path


def source_path(root, relative):
    path = (root / relative).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError(f"Source must be an existing project file: {relative}")
    return path


def build(project_root, manifest_path, write=True):
    root = Path(project_root).resolve()
    manifest_path = source_path(root, manifest_path)
    directory = manifest_path.parent
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    sections = manifest["sections"]
    if not sections or sections[0]["id"] != "overview":
        raise ValueError("The first section must have id overview.")
    ids = [section["id"] for section in sections]
    if len(set(ids)) != len(ids) or any(
        not re.fullmatch(r"[a-z][a-z0-9-]*", value) for value in ids
    ):
        raise ValueError(
            "Section IDs must be unique lowercase URL-fragment identifiers."
        )

    referenced = set()
    symbols = {}
    coverage = manifest.get("coverage")
    if not coverage:
        raise ValueError("Discover implementation components and record coverage first.")
    for component in coverage:
        path = source_path(root, component["path"])
        if not component.get("symbol", "").strip():
            raise ValueError("Coverage needs an implementation symbol.")
        target = component.get("section")
        reason = component.get("reason", "").strip()
        if bool(target) == bool(reason):
            raise ValueError("Coverage needs either a detail section or exclusion reason.")
        if target:
            detail = next((section for section in sections if section["id"] == target), None)
            if detail is None or target == "overview":
                raise ValueError(f"Coverage needs a module detail section: {target}")
            if not any(source["path"] == component["path"] for source in detail.get("sources", [])):
                raise ValueError(f"Detail section must cite the covered implementation: {target}")
        referenced.add(path)
    for section in sections:
        section.setdefault("notes", [])
        section.setdefault("sources", [])
        section.setdefault("tests", [])
        section.setdefault(
            "flat",
            "\n".join(
                line
                for line in section["mermaid"].splitlines()
                if not line.strip().startswith("subgraph ") and line.strip() != "end"
            ),
        )
        for source in section["sources"]:
            path = source_path(root, source["path"])
            referenced.add(path)
            lines = path.read_text(encoding="utf-8-sig").splitlines()
            start, end = source["start_line"], source["end_line"]
            if not 1 <= start <= end <= len(lines):
                raise ValueError(
                    f"Invalid source line range: {source['path']}:{start}-{end}"
                )
            source["line"] = start
            source["symbol"] = source.get("symbol", path.name)
            source["code"] = "\n".join(
                f"{number + 1:4}  {lines[number]}" for number in range(start - 1, end)
            )
            source["href"] = Path(os.path.relpath(path, directory)).as_posix()
            symbols.setdefault(path, []).append(source["symbol"])
        for relative in section["tests"]:
            referenced.add(source_path(root, relative))

    watched = set(referenced)
    for pattern in manifest.get("watch", []):
        for path in root.glob(pattern):
            resolved = path.resolve()
            if (
                resolved.is_file()
                and resolved.is_relative_to(root)
                and not resolved.is_relative_to(directory)
            ):
                watched.add(resolved)
    template_path = directory / "template.html"
    renderer_path = directory / "assets/mermaid.min.js"
    license_path = directory / "assets/mermaid-LICENSE"
    inputs = watched | {manifest_path, template_path, renderer_path, license_path}
    hashes = {
        path.relative_to(root).as_posix(): hashlib.sha256(
            path.read_text(encoding="utf-8-sig").encode("utf-8")
        ).hexdigest()
        for path in sorted(inputs, key=lambda path: path.relative_to(root).as_posix())
    }
    hashes["_generator"] = hashlib.sha256(
        Path(__file__).read_text(encoding="utf-8-sig").encode("utf-8")
    ).hexdigest()
    revision = hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()
    modules = [
        {
            "path": path.relative_to(root).as_posix(),
            "symbols": sorted(set(symbols.get(path, []))),
        }
        for path in sorted(watched, key=lambda path: path.relative_to(root).as_posix())
    ]
    data = {
        "project": manifest["project"],
        "sections": sections,
        "modules": modules,
        "coverage": coverage,
        "revision": revision,
        "projectHref": Path(os.path.relpath(root, directory)).as_posix(),
    }
    renderer = renderer_path.read_text(encoding="utf-8-sig")
    license_text = license_path.read_text(encoding="utf-8-sig")
    page = template_path.read_text(encoding="utf-8-sig")
    page = page.replace("__PROJECT_NAME__", html.escape(manifest["project"]))
    page = page.replace(
        "__DOCUMENTATION_DATA__",
        json.dumps(data, ensure_ascii=False).replace("<", "\\u003c"),
    )
    page = page.replace(
        "__MERMAID_RENDERER__",
        ("/*\n" + license_text + "\n*/\n" + renderer).replace("</script", "<\\/script"),
    )
    markdown = [
        f"# {manifest['project']} architecture and state machines",
        "",
        "Open [the standalone HTML explorer](index.html) for grouped and flat diagrams.",
        "",
        "Generated source snapshot. Review behavior when source fingerprints change.",
        "",
    ]
    for section in sections:
        markdown.extend(
            [
                f'<a id="{section["id"]}"></a>',
                f"## {section['title']}",
                "",
                f"*{section['kind']}*",
                "",
                section["summary"],
                "",
                "```mermaid",
                section["mermaid"],
                "```",
                "",
            ]
        )
        markdown += [f"- {note}" for note in section["notes"]]
        markdown += [
            f"- [`{source['symbol']}`]({source['href']}#L{source['line']}) in `{source['path']}`."
            for source in section["sources"]
        ]
        markdown.append("")
    outputs = {
        directory / "index.html": page,
        directory / "index.md": "\n".join(markdown),
        directory / "revision.json": json.dumps(
            {"revision": revision, "sources": hashes}, indent=2
        )
        + "\n",
    }
    stale = []
    for path, content in outputs.items():
        if not path.exists() or path.read_text(encoding="utf-8") != content:
            stale.append(path.name)
            if write:
                path.write_text(content, encoding="utf-8", newline="\n")
    return stale


def main():
    parser = argparse.ArgumentParser(
        description="Build source-linked architecture documentation as one offline HTML file."
    )
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--manifest", default="docs/architecture/architecture.json")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    stale = build(args.project_root, args.manifest, write=not args.check)
    if args.check and stale:
        print("Documentation is stale: " + ", ".join(stale))
        print("Review changed behavior and regenerate the documentation.")
        return 1
    print(
        "Documentation matches current source."
        if args.check
        else "Built standalone architecture HTML."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
