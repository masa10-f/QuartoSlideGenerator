#!/usr/bin/env python3
import argparse, os, subprocess, datetime, collections

def sh(cmd, cwd=None):
    p = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       text=True)
    if p.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{p.stderr}")
    return p.stdout

def parse_args():
    ap = argparse.ArgumentParser(description="Generate QMD for task slides")
    ap.add_argument("--task", default="", help="Task ID (optional)")
    ap.add_argument("--repo", default=".")
    ap.add_argument("--since", default="")
    ap.add_argument("--until", default="HEAD")
    ap.add_argument("--paths", default="")
    ap.add_argument("--grep", default="")
    ap.add_argument("--include-diff", action="store_true")
    ap.add_argument("--max-patch-lines", type=int, default=600)
    ap.add_argument("--title", default="")
    ap.add_argument("--out", required=True)
    ap.add_argument("--format", default="html", choices=["html","pdf"])
    return ap.parse_args()

def default_since(repo):
    try:
        base = sh(["git","merge-base","origin/main","HEAD"], cwd=repo).strip()
        return base
    except Exception:
        return ""

def commit_list(repo, task_id, since, until, paths, extra_grep):
    args = ["git","log","--date=iso","--pretty=format:%H%x09%h%x09%ad%x09%an%x09%s","--no-merges"]
    if since:
        args.append(f"{since}..{until}")
    else:
        args.append(until)
    # Only add --grep filter if task_id is provided
    if task_id:
        args += ["--regexp-ignore-case","--grep", task_id]
    if extra_grep:
        args += ["--regexp-ignore-case", "--grep", extra_grep]
    if paths:
        args.append("--")
        args += [p for p in paths if p]
    out = sh(args, cwd=repo)
    commits=[]
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts)>=5:
            commits.append({"sha": parts[0], "short": parts[1], "date": parts[2],
                            "author": parts[3], "subject": parts[4]})
    return commits

def files_for_commit(repo, sha, paths):
    args = ["git","show","--name-only","--pretty=format:","--no-renames", sha]
    if paths: args += ["--"] + paths
    out = sh(args, cwd=repo)
    return [l for l in out.splitlines() if l.strip()]

def diffstat_for_commit(repo, sha, paths):
    args = ["git","show","--stat","--oneline", sha]
    if paths: args += ["--"] + paths
    return sh(args, cwd=repo).strip()

def patch_for_commit(repo, sha, paths, limit):
    args = ["git","show","--patch","--unified=3", sha]
    if paths: args += ["--"] + paths
    txt = sh(args, cwd=repo)
    lines = txt.splitlines()
    if limit and len(lines) > limit:
        return "\n".join(lines[:limit] + ["...", "(truncated)"])
    return txt

def top_files(commits_files, topn=10):
    cnt = collections.Counter()
    for files in commits_files:
        cnt.update(f for f in files if f)
    return cnt.most_common(topn)

def fm(title):
    return f"""---
title: "{title}"
format:
  revealjs:
    slide-number: true
    transition: fade
    controls: true
    center: false
    code-overflow: wrap
---
"""

def md(s):  # minimal escape
    return s.replace("<","&lt;").replace(">","&gt;")

def build_qmd(repo, args, commits):
    if args.title:
        title = args.title
    elif args.task:
        title = f"Task Report: {args.task}"
    else:
        title = "Commit Report"

    q = [fm(title)]
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    rng = f"{args.since+'..' if args.since else ''}{args.until}"

    q.append(f"# {md(title)}\n\n")
    if args.task:
        q.append(f"- **Task**: `{md(args.task)}`  \n")
    q.append(f"- **Repo**: `{md(os.path.abspath(repo))}`  \n- **Range**: `{md(rng)}`  \n- **Generated**: {now}\n\n---\n")

    authors = sorted({c["author"] for c in commits})
    commits_files = [files_for_commit(repo, c["sha"], args.paths) for c in commits]
    tops = top_files(commits_files, topn=10)

    q.append("## 概要\n\n")
    q.append(f"- コミット数: **{len(commits)}**  \n")
    q.append(f"- 著者: {', '.join(authors) if authors else '-'}  \n")
    if tops:
        q.append("- よく変更したファイル/パス（Top 10）:\n")
        for path, n in tops:
            q.append(f"  - `{md(path)}` × {n}\n")
    else:
        q.append("- 変更ファイル情報なし\n")
    q.append("\n---\n")

    q.append("## コミット・ハイライト\n\n")
    if not commits:
        q.append("_該当コミットが見つかりません。フィルタ条件を見直してください。_\n\n")
    for c in commits:
        stat = diffstat_for_commit(repo, c["sha"], args.paths)
        q.append(f"### {md(c['short'])} — {md(c['subject'])}\n")
        q.append(f"`{md(c['date'])}` / {md(c['author'])}\n\n")
        q.append("```text\n" + stat + "\n```\n\n")
    q.append("\n---\n")

    if args.include_diff and commits:
        q.append("## 付録：パッチ（抜粋）\n\n")
        for c in commits:
            patch = patch_for_commit(repo, c["sha"], args.paths, args.max_patch_lines)
            q.append(f"### Patch {md(c['short'])} — {md(c['subject'])}\n\n")
            q.append("```diff\n" + patch + "\n```\n\n")
    return "".join(q)

def main():
    a = parse_args()
    repo = os.path.abspath(a.repo)
    if not os.path.isdir(os.path.join(repo, ".git")):
        raise SystemExit(f"Not a git repo: {repo}")
    a.paths = [p for p in (a.paths.split(",") if a.paths else []) if p]
    if not a.since:
        a.since = default_since(repo)
    commits = commit_list(repo, a.task, a.since, a.until, a.paths, a.grep)
    qmd = build_qmd(repo, a, commits)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        f.write(qmd)

if __name__ == "__main__":
    main()
