#!/usr/bin/env python3
import argparse, os, subprocess, datetime, collections, json
try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

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
    ap.add_argument("--summary-mode", default="none", choices=["none","template","ai","manual"],
                    help="Summary generation mode (default: none)")
    ap.add_argument("--summary-api-key", default="", help="API key for AI mode (or use ANTHROPIC_API_KEY env)")
    ap.add_argument("--summary-dir", default="", help="Directory for manual summaries (default: .commit-summaries)")
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

def get_commit_body(repo, sha):
    """Get the full commit message body (excluding subject)"""
    try:
        # Get commit message body (everything after first line)
        out = sh(["git", "log", "-1", "--pretty=format:%b", sha], cwd=repo)
        return out.strip()
    except Exception:
        return ""

def extract_template_summary(commit_subject, commit_body):
    """Extract summary information from commit message body"""
    if not commit_body:
        return ""

    # Look for structured information in commit body
    lines = commit_body.split("\n")
    summary_parts = []

    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Common patterns in commit messages
        if line.startswith("* ") or line.startswith("- "):
            summary_parts.append(line[2:])
        elif line.startswith("+ "):
            summary_parts.append(line[2:])
        elif len(line) > 20 and not line.startswith("#"):  # Meaningful description
            summary_parts.append(line)

    if summary_parts:
        return "\n\n".join(f"- {part}" if not part.startswith("-") else part
                          for part in summary_parts[:5])  # Limit to 5 items
    return ""

def generate_ai_summary(commit_subject, commit_body, diffstat, patch_preview, api_key):
    """Generate AI summary using Claude API"""
    if not HAS_ANTHROPIC:
        return "⚠ AI summary unavailable: anthropic package not installed (pip install anthropic)"

    if not api_key:
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            return "⚠ AI summary unavailable: No API key provided"

    try:
        client = anthropic.Anthropic(api_key=api_key)

        # Prepare context for AI
        context = f"""Commit Subject: {commit_subject}

Commit Body:
{commit_body if commit_body else "(no additional description)"}

Diffstat:
{diffstat}

Code Changes (preview):
{patch_preview[:2000] if patch_preview else "(no patch preview)"}
"""

        prompt = """You are analyzing a Git commit to create a natural language summary for stakeholders.

Based on the commit information provided, generate a concise summary that explains:
1. What functionality was added/modified/removed (2-3 bullet points)
2. Why the change was made (if inferable)
3. Key highlights that would matter to non-technical stakeholders

Format your response as markdown with bullet points. Be concise but informative. Focus on the "what" and "why" rather than technical implementation details.

Do not include headers - just the bullet points."""

        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=500,
            messages=[
                {"role": "user", "content": context + "\n\n" + prompt}
            ]
        )

        # Extract text from response
        summary = response.content[0].text.strip()
        return summary

    except Exception as e:
        return f"⚠ AI summary generation failed: {str(e)}"

def load_manual_summary(repo, sha, summary_dir):
    """Load manual summary from file"""
    if not summary_dir:
        summary_dir = os.path.join(repo, ".commit-summaries")

    # Try both full SHA and short SHA
    for commit_id in [sha, sha[:7]]:
        summary_path = os.path.join(summary_dir, f"{commit_id}.md")
        if os.path.isfile(summary_path):
            try:
                with open(summary_path, "r", encoding="utf-8") as f:
                    return f.read().strip()
            except Exception:
                pass
    return ""

def generate_summary(repo, commit, diffstat, patch_preview, args):
    """Generate summary based on configured mode (hybrid approach)"""
    sha = commit["sha"]
    subject = commit["subject"]

    # Get commit body
    body = get_commit_body(repo, sha)

    # Try modes in order based on configuration
    mode = args.summary_mode

    if mode == "none":
        return ""

    # Manual mode: try to load from file first
    if mode == "manual":
        manual = load_manual_summary(repo, sha, args.summary_dir)
        if manual:
            return manual
        return "⚠ No manual summary found"

    # Template mode: extract from commit body
    if mode == "template":
        template = extract_template_summary(subject, body)
        if template:
            return template
        # Fall back to showing commit body if structured extraction failed
        if body:
            return body
        return "_No structured information found in commit message_"

    # AI mode: generate using Claude API
    if mode == "ai":
        # Try AI generation
        ai_summary = generate_ai_summary(subject, body, diffstat, patch_preview, args.summary_api_key)
        return ai_summary

    return ""

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

        # Generate summary if enabled
        if args.summary_mode != "none":
            # Get patch preview for AI mode
            patch_preview = ""
            if args.summary_mode == "ai":
                patch_preview = patch_for_commit(repo, c["sha"], args.paths, 500)

            summary = generate_summary(repo, c, stat, patch_preview, args)
            if summary:
                q.append("**Summary:**\n\n")
                q.append(summary + "\n\n")

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
