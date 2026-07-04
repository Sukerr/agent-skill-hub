#!/usr/bin/env python3
"""skillhub -- zero-dependency Agent Skill sharing CLI."""

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
from pathlib import Path

HOME = Path.home()
DEFAULT_SOURCE = HOME / "ai-workspace" / "shared-skills"
DEFAULT_MANIFEST_NAME = ".skillhub.json"

SKIP_DIRS = {
    ".git",
    "_public",
    ".archive",
    ".curator_backups",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".cache",
    "node_modules",
}

HOST_ALIASES = {
    "claude": "claude",
    "claude-code": "claude",
    "claude_code": "claude",
    "hermes": "hermes",
    "codex": "codex",
}

HOST_LABELS = {
    "claude": "Claude Code",
    "hermes": "Hermes",
    "codex": "Codex",
}


def resolve_path(path):
    return Path(os.path.expanduser(str(path))).resolve()


def read_text(path):
    try:
        return Path(path).read_text(encoding="utf-8")
    except OSError:
        return ""


def parse_frontmatter(path):
    text = read_text(path)
    match = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return {}, False
    block = match.group(1)
    data = {}
    current_key = None
    current_lines = []
    current_style = None

    def flush_multiline():
        nonlocal current_key, current_lines, current_style
        if current_key:
            sep = "\n" if current_style == "|" else " "
            data[current_key] = sep.join(line.strip() for line in current_lines if line.strip()).strip()
        current_key = None
        current_lines = []
        current_style = None

    for line in block.splitlines():
        if current_key and (not line or line[0] in " \t"):
            current_lines.append(line)
            continue
        flush_multiline()
        if not line or line[0] in " \t#":
            continue
        item = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if not item:
            continue
        key = item.group(1).lower()
        value = item.group(2).strip()
        if key not in ("name", "description", "version"):
            continue
        if value in ("|", ">", "|-", ">-", "|+", ">+"):
            current_key = key
            current_style = value[0]
            current_lines = []
            continue
        if len(value) >= 2 and value[0] in "\"'" and value[-1] == value[0]:
            value = value[1:-1]
        data[key] = value
    flush_multiline()
    has_hermes_metadata = bool(re.search(r"^metadata:\s*$[\s\S]*?^\s+hermes:\s*$", block, re.MULTILINE))
    return data, has_hermes_metadata


def iter_skill_files(source):
    source = resolve_path(source)
    if not source.is_dir():
        return
    seen = set()
    for current, dirs, files in os.walk(source, followlinks=True):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and not d.startswith(".venv"))
        real_current = os.path.realpath(current)
        if real_current in seen:
            dirs[:] = []
            continue
        seen.add(real_current)
        if "SKILL.md" in files:
            yield Path(current) / "SKILL.md"


def nearest_plugin_markers(skill_dir, source):
    found = set()
    current = resolve_path(skill_dir)
    source = resolve_path(source)
    while str(current).startswith(str(source)):
        if (current / ".claude-plugin").exists() or (current / "CLAUDE.md").exists():
            found.add("claude")
        if (current / ".codex-plugin").exists() or (current / ".agents").exists():
            found.add("codex")
        if current == source:
            break
        current = current.parent
    return found


def detect_hosts(skill_md, frontmatter, has_hermes_metadata, source):
    text = read_text(skill_md).lower()
    hosts = set()
    if has_hermes_metadata or any(term in text for term in ("hermes", "gateway", "kanban", "curator", "toolsets")):
        hosts.add("hermes")
    if any(term in text for term in ("claude code", ".claude-plugin", "claude.md")):
        hosts.add("claude")
    if any(term in text for term in ("codex", ".codex-plugin", ".agents/skills")):
        hosts.add("codex")
    hosts.update(nearest_plugin_markers(Path(skill_md).parent, source))
    if not hosts:
        hosts.update(HOST_ALIASES.values())
    return sorted(hosts)


def load_manifest(source, manifest_path=None):
    source = resolve_path(source)
    path = resolve_path(manifest_path) if manifest_path else source / DEFAULT_MANIFEST_NAME
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def normalize_hosts(hosts):
    normalized = []
    for host in hosts or []:
        key = HOST_ALIASES.get(str(host).lower())
        if key and key not in normalized:
            normalized.append(key)
    return normalized


def apply_manifest(skill, manifest):
    config = manifest.get("skills", {}).get(skill["name"], {})
    if not config:
        config = manifest.get("skills", {}).get(skill["dir_name"], {})
    hosts = normalize_hosts(config.get("hosts"))
    if hosts:
        skill["hosts"] = hosts
    if "sync" in config:
        skill["sync"] = config["sync"]
    if "visibility" in config:
        skill["visibility"] = config["visibility"]
    return skill


def scan_skills(source=DEFAULT_SOURCE, manifest_path=None):
    source = resolve_path(source)
    manifest = load_manifest(source, manifest_path)
    skills = []
    for skill_md in iter_skill_files(source) or []:
        frontmatter, has_hermes_metadata = parse_frontmatter(skill_md)
        skill_dir = skill_md.parent
        name = frontmatter.get("name") or skill_dir.name
        skill = {
            "name": name,
            "description": frontmatter.get("description", ""),
            "version": frontmatter.get("version", ""),
            "relative_path": str(skill_md.relative_to(source)),
            "dir_relative_path": str(skill_dir.relative_to(source)),
            "skill_md_path": str(skill_md),
            "dir_path": str(skill_dir),
            "dir_name": skill_dir.name,
            "hosts": detect_hosts(skill_md, frontmatter, has_hermes_metadata, source),
            "sync": manifest.get("default_mode", "link"),
            "visibility": "shared",
            "is_symlink": skill_dir.is_symlink(),
            "symlink_target": os.path.realpath(skill_dir) if skill_dir.is_symlink() else "",
        }
        skills.append(apply_manifest(skill, manifest))
    return sorted(skills, key=lambda item: item["relative_path"].lower())


def normalize_host(host):
    key = HOST_ALIASES.get(str(host).lower())
    if not key:
        raise ValueError(f"Unknown host: {host}")
    return key


def default_target_for(host, project=None):
    host = normalize_host(host)
    if host == "claude":
        return HOME / ".claude" / "skills"
    if host == "hermes":
        return HOME / ".hermes" / "skills"
    project_root = resolve_path(project or Path.cwd())
    return project_root / ".agents" / "skills"


def is_compatible(skill, host):
    host = normalize_host(host)
    return host in skill.get("hosts", [])


def file_hash(path):
    h = hashlib.sha256()
    h.update(Path(path).relative_to(path).as_posix().encode("utf-8"))
    h.update(Path(path).read_bytes())
    return h.hexdigest()


def tree_hash(path):
    path = resolve_path(path)
    if not path.exists():
        return ""
    h = hashlib.sha256()
    if path.is_file():
        return file_hash(path)
    for current, dirs, files in os.walk(path, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and not d.startswith(".venv"))
        for filename in sorted(files):
            full = Path(current) / filename
            if full.is_symlink():
                continue
            rel = full.relative_to(path).as_posix()
            h.update(rel.encode("utf-8"))
            h.update(b"\0")
            h.update(full.read_bytes())
            h.update(b"\0")
    return h.hexdigest()


def status_for_skill(skill, target_root):
    dest = resolve_path(target_root) / skill["name"]
    if not dest.exists() and not dest.is_symlink():
        state = "missing"
    elif dest.is_symlink():
        state = "linked" if os.path.realpath(dest) == os.path.realpath(skill["dir_path"]) else "path-conflict"
    elif dest.is_dir():
        state = "copied-current" if tree_hash(dest) == tree_hash(skill["dir_path"]) else "copied-stale"
    else:
        state = "path-conflict"
    return {
        "name": skill["name"],
        "state": state,
        "target_path": str(dest),
        "source_path": skill["dir_path"],
        "hosts": skill["hosts"],
    }


def collect_status(source=DEFAULT_SOURCE, host="claude", target=None, project=None, manifest_path=None):
    host = normalize_host(host)
    target_root = resolve_path(target or default_target_for(host, project))
    return [
        status_for_skill(skill, target_root)
        for skill in scan_skills(source, manifest_path)
        if is_compatible(skill, host)
    ]


def remove_existing(path):
    path = Path(path)
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def sync_skills(source=DEFAULT_SOURCE, host="claude", target=None, project=None, mode="link", dry_run=False, force=False, manifest_path=None):
    host = normalize_host(host)
    if mode not in ("link", "copy"):
        raise ValueError("mode must be link or copy")
    target_root = resolve_path(target or default_target_for(host, project))
    actions = []
    for skill in scan_skills(source, manifest_path):
        if not is_compatible(skill, host):
            continue
        dest = target_root / skill["name"]
        source_dir = resolve_path(skill["dir_path"])
        existing_state = status_for_skill(skill, target_root)["state"]
        if existing_state in ("linked", "copied-current"):
            actions.append({"name": skill["name"], "action": "skipped-current", "target_path": str(dest)})
            continue
        if dest.exists() or dest.is_symlink():
            if not force:
                actions.append({"name": skill["name"], "action": "conflict", "target_path": str(dest)})
                continue
            if not dry_run:
                remove_existing(dest)
        action = "linked" if mode == "link" else "copied"
        if not dry_run:
            target_root.mkdir(parents=True, exist_ok=True)
            if mode == "link":
                os.symlink(source_dir, dest)
            else:
                shutil.copytree(source_dir, dest, symlinks=True)
        actions.append({"name": skill["name"], "action": action if not dry_run else f"would-{action}", "target_path": str(dest)})
    return actions


def doctor(source=DEFAULT_SOURCE, manifest_path=None):
    source = resolve_path(source)
    skills = scan_skills(source, manifest_path) if source.exists() else []
    names = {}
    duplicate_names = []
    missing_descriptions = []
    for skill in skills:
        names.setdefault(skill["name"], 0)
        names[skill["name"]] += 1
        if not skill["description"]:
            missing_descriptions.append(skill["name"])
    duplicate_names = sorted(name for name, count in names.items() if count > 1)
    return {
        "source": str(source),
        "source_exists": source.is_dir(),
        "skill_count": len(skills),
        "duplicate_names": duplicate_names,
        "missing_descriptions": missing_descriptions,
        "default_targets": {host: str(default_target_for(host)) for host in HOST_LABELS},
    }


def print_table(rows, columns):
    if not rows:
        print("No rows.")
        return
    widths = {key: len(label) for key, label in columns}
    for row in rows:
        for key, _label in columns:
            widths[key] = max(widths[key], len(str(row.get(key, ""))))
    print("  ".join(label.ljust(widths[key]) for key, label in columns))
    print("  ".join("-" * widths[key] for key, _label in columns))
    for row in rows:
        print("  ".join(str(row.get(key, "")).ljust(widths[key]) for key, _label in columns))


def cmd_scan(args):
    skills = scan_skills(args.source, args.manifest)
    if args.json:
        print(json.dumps(skills, ensure_ascii=False, indent=2))
        return 0
    rows = [
        {
            "name": skill["name"],
            "hosts": ",".join(skill["hosts"]),
            "path": skill["dir_relative_path"],
        }
        for skill in skills
    ]
    print_table(rows, [("name", "Name"), ("hosts", "Hosts"), ("path", "Path")])
    return 0


def cmd_status(args):
    rows = collect_status(args.source, args.host, args.target, args.project, args.manifest)
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0
    print_table(rows, [("name", "Name"), ("state", "State"), ("target_path", "Target")])
    return 0


def cmd_link(args):
    rows = sync_skills(args.source, args.host, args.target, args.project, args.mode, args.dry_run, args.force, args.manifest)
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0
    print_table(rows, [("name", "Name"), ("action", "Action"), ("target_path", "Target")])
    return 0


def cmd_doctor(args):
    result = doctor(args.source, args.manifest)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    print(f"Source: {result['source']}")
    print(f"Source exists: {result['source_exists']}")
    print(f"Skills: {result['skill_count']}")
    print(f"Duplicate names: {', '.join(result['duplicate_names']) or 'none'}")
    print(f"Missing descriptions: {', '.join(result['missing_descriptions']) or 'none'}")
    for host, target in result["default_targets"].items():
        print(f"{HOST_LABELS[host]} target: {target}")
    return 0


def build_parser():
    parser = argparse.ArgumentParser(description="Share SKILL.md folders across local agent hosts.")
    parser.add_argument("--source", default=os.environ.get("SKILLHUB_SOURCE", str(DEFAULT_SOURCE)), help="Skill source directory.")
    parser.add_argument("--manifest", default=os.environ.get("SKILLHUB_MANIFEST"), help="Optional .skillhub.json path.")
    sub = parser.add_subparsers(dest="command", required=True)

    scan = sub.add_parser("scan", help="List skills discovered in the source directory.")
    scan.add_argument("--json", action="store_true")
    scan.set_defaults(func=cmd_scan)

    status = sub.add_parser("status", help="Show whether compatible skills exist in a host target.")
    status.add_argument("--host", default="claude", choices=sorted(HOST_ALIASES))
    status.add_argument("--target", help="Override host skill target directory.")
    status.add_argument("--project", help="Project root for Codex .agents/skills.")
    status.add_argument("--json", action="store_true")
    status.set_defaults(func=cmd_status)

    link = sub.add_parser("link", help="Link or copy compatible skills into a host target.")
    link.add_argument("--host", required=True, choices=sorted(HOST_ALIASES))
    link.add_argument("--target", help="Override host skill target directory.")
    link.add_argument("--project", help="Project root for Codex .agents/skills.")
    link.add_argument("--mode", default="link", choices=("link", "copy"))
    link.add_argument("--dry-run", action="store_true")
    link.add_argument("--force", action="store_true")
    link.add_argument("--json", action="store_true")
    link.set_defaults(func=cmd_link)

    doc = sub.add_parser("doctor", help="Check source health and default host targets.")
    doc.add_argument("--json", action="store_true")
    doc.set_defaults(func=cmd_doctor)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
