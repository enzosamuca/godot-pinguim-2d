#!/usr/bin/env python3
"""Standalone Mind kit — stage read-only working context into .mind/_global/.

Offline replacement for a download step: nothing is fetched from
the network or from the MindHub. Everything is taken from this repo.

  .mind/_global/SKILL.md                 the skill to execute (onboard-repo | update-repo)
  .mind/_global/instructions/*           copy of .mind/instructions/*
  .mind/_global/skills/<name>/SKILL.md   copy of every local skill
  .mind/_global/code-graph.{json,md}     produced by mind-code-graph.py (optional)

Usage: python .mind/tools/mind-stage.py [--skill onboard-repo|update-repo] [--no-graph] [repo-root]
"""
import argparse, shutil, subprocess, sys
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("repo", nargs="?", default=".")
ap.add_argument("--skill", choices=["onboard-repo", "update-repo"])
ap.add_argument("--no-graph", action="store_true")
a = ap.parse_args()

root = Path(a.repo).resolve()
mind = root / ".mind"
g = mind / "_global"

skill = a.skill or ("update-repo" if (mind / "context" / "overview.md").exists() else "onboard-repo")
src = mind / "skills" / skill / "SKILL.md"
if not src.exists():
    sys.exit(f"ERROR: {src} not found. Run install.py first.")

if g.exists():
    shutil.rmtree(g)
g.mkdir(parents=True)
shutil.copy2(src, g / "SKILL.md")

if (mind / "instructions").is_dir():
    shutil.copytree(mind / "instructions", g / "instructions")
if (mind / "skills").is_dir():
    for d in (mind / "skills").iterdir():
        if (d / "SKILL.md").exists():
            (g / "skills" / d.name).mkdir(parents=True)
            shutil.copy2(d / "SKILL.md", g / "skills" / d.name / "SKILL.md")

# .gitignore: append (never overwrite) the _global entry
gi = root / ".gitignore"
entry = ".mind/_global/"
text = gi.read_text(encoding="utf-8") if gi.exists() else ""
if entry not in text.splitlines():
    with gi.open("a", encoding="utf-8") as f:
        f.write(("" if text == "" or text.endswith("\n") else "\n") + entry + "\n")
    print(f"Appended {entry} to .gitignore")
subprocess.run(["git", "-C", str(root), "rm", "-r", "--cached", "--quiet", ".mind/_global/"],
               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

print(f"Staged skill: {skill}  ->  {g / 'SKILL.md'}")

if not a.no_graph:
    graph = mind / "tools" / "mind-code-graph.py"
    print("Running code graph analysis (needs pip access for tree-sitter; skipped on failure) ...")
    r = subprocess.run([sys.executable, str(graph), str(root)])
    if r.returncode != 0:
        print("WARNING: code graph failed — the skills fall back to manual extraction (rg).")
print("Stage complete.")
