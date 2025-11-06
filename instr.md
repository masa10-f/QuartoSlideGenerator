了解です。
**「タスク単位で git の変更を集約 → Quarto（reveal.js）でスライド化」**する **Skill 専用リポジトリ**を自作し、**Claude（Claude Code / claude.ai）**から読み込んで使えるようにするための**手順書**をまとめました。
（※「Codex」側には標準の *SKILL.md* 互換はありませんが、同リポジトリのスクリプトを直接実行させれば同様の自動化が可能です。）

---

## 0. 何を作るか（完成像）

* リポジトリ直下に **`.claude/skills/quarto-task-slides/`** という **Skill フォルダ**を置く

  * 中に **`SKILL.md`**（Skill本体の説明＋手順）と、**スクリプト一式**を格納
  * Claude Code ではプロジェクト内のこの Skill を**自動検出**して利用できます。([Claude Docs][1])
* スキルの役割

  1. 「`TASK-123` の作業をスライドに」などの依頼を受けたら
  2. `git log` / `git show` から **タスク関連コミット**を収集・集計
  3. **Quarto** の `.qmd` を自動生成 → **reveal.js スライド（HTML/PDF）**を出力

> Claude 側で Skills を使うには**設定で Skills/Code Execution を有効化**し、（claude.ai の場合は）**ZIP でアップロード**する運用も選べます。([Claude Help Center][2])

---

## 1. 前提（WSL/Ubuntu 想定）

### 必須ツールの導入

```bash
# WSL の導入（未導入なら）
# 参考: Microsoft 公式（概要と基本操作）→ wsl --install
# https://learn.microsoft.com/windows/wsl/install
# WSL を起動して以降は Linux 側で作業
sudo apt-get update
sudo apt-get install -y git python3 python3-venv curl

# Quarto（公式の手順を推奨）
# https://quarto.org/docs/get-started/
# 例: .deb を取得して dpkg -i で導入 or tarball で導入
# https://quarto.org/docs/download/
# インストール後の確認:
quarto --version

# PDF も出力する場合（LaTeX/TinyTeX）
quarto install tinytex
# (TinyTeXアップデートは `quarto update tinytex`)
```

参考：Quarto の「Get Started」「Download」「TinyTeX（PDF エンジン）」ドキュメント。([Quarto][3])
WSL の基本は Microsoft Docs を参照。([Microsoft Learn][4])

---

## 2. リポジトリ作成（構成）

```bash
# 任意の作業ディレクトリで
mkdir -p quarto-task-slides-skill/.claude/skills/quarto-task-slides/scripts
cd quarto-task-slides-skill
git init
```

**ディレクトリ最終形（目標）**

```
quarto-task-slides-skill/
├─ .claude/
│  └─ skills/
│      └─ quarto-task-slides/
│          ├─ SKILL.md
│          └─ scripts/
│              ├─ task_slides.sh
│              └─ gen_task_qmd.py
├─ .gitignore
└─ README.md
```

> **Claude Code** はプロジェクト内の **`.claude/skills/*/SKILL.md`** を「プロジェクト Skill」として自動検出します。個人スコープで使うなら `~/.claude/skills/` 直下でも可。([Claude Docs][1])

---

## 3. ファイルを配置（コピペ用）

### 3.1 `.claude/skills/quarto-task-slides/SKILL.md`

> **最重要ファイル**。`name` / `description` を含む YAML フロントマターが必要です（短く明確に。Claude は **description** を手がかりに起動可否を判断）。([Claude Docs][1])

````markdown
---
name: quarto-task-slides
description: >
  Git からタスクIDに紐づくコミットを収集し、Quarto（reveal.js）でスライド（HTML/PDF）を生成する。
  ユーザーが「TASK-xxx をスライドに」などタスク粒度の報告を求めたときに使用する。
version: 1.0.0
---

# Quarto Task Slides（タスク粒度のスライド生成）

## 目的
- 指定タスク（例: `TASK-123` やブランチ名）に関連するコミットを抽出し、要約・diffstat・頻出ファイルなどを自動整形。
- Quarto（reveal.js）で HTML / PDF スライドを生成して配布可能にする。

## 前提
- 実行環境に `git`, `python3`, `quarto` が入っていること。
- PDF を出す場合は TinyTeX などの LaTeX が必要（`quarto install tinytex`）。

## 入力パラメータ
- `task_id`（必須）: 例 `TASK-123` / `feature/foo`
- `repo_dir`（既定 `.`）
- `since` / `until`（例 `since=origin/main`, `until=HEAD`。省略時は `merge-base origin/main..HEAD`）
- `paths`（任意: `src/foo,app/` など）
- `grep`（任意の追加フィルタ）
- `include_diff`（bool, 既定 false）
- `max_patch_lines`（既定 600）
- `title`（任意）
- `format`（`html` | `pdf`、既定 `html`）
- `outdir`（既定 `slides/`）

## 実行手順（Claude が行うべきこと）
1. 足りない入力をユーザーに軽く確認し、未指定は既定値で補う。
2. 次のスクリプトを実行する（プロジェクト内の相対パス）。
   ```bash
   bash .claude/skills/quarto-task-slides/scripts/task_slides.sh \
     --task "<task_id>" \
     --repo "<repo_dir>" \
     ${since:+--since "<since>"} ${until:+--until "<until>"} \
     ${paths:+--paths "<paths>"} \
     ${grep:+--grep "<grep>"} \
     ${title:+--title "<title>"} \
     --format "<format>" \
     --outdir "<outdir>" \
     $( [[ "<include_diff>" == "true" ]] && echo --include-diff )
````

3. 成功したら、出力ファイル（`<outdir>/*.html` or `*.pdf`）のパスを報告する。
4. 失敗時は、`git`/`quarto` の存在を確認し、必要ならユーザーにインストールを提案する。

## 例

* 「`TASK-123` を `src/auth` に限定、HTMLで」

  ```bash
  bash .claude/skills/quarto-task-slides/scripts/task_slides.sh \
    --task TASK-123 --paths src/auth --format html
  ```
* 「ブランチ `feature/2fa` を PDF で、パッチ付き」

  ```bash
  bash .claude/skills/quarto-task-slides/scripts/task_slides.sh \
    --task feature/2fa --include-diff --format pdf
  ```

## 注意

* 変更は読み取り中心だが、`slides/` に成果物（.qmd / .html / .pdf）を出力する。
* ネットワークや外部 API は不要（ローカル Git に依存）。
* セキュリティ: 不要な外部コマンド導入は避ける。必要時のみ最小限に。

````

> Claude Code の **Project Skill** / **Personal Skill** の場所や、Skill の発見・起動の仕組みは公式ドキュメントを参照してください。:contentReference[oaicite:6]{index=6}

---

### 3.2 `.claude/skills/quarto-task-slides/scripts/task_slides.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

TASK_ID=""
REPO_DIR="."
SINCE=""
UNTIL=""
PATHS=""
EXTRA_GREP=""
INCLUDE_DIFF="false"
MAX_PATCH_LINES="600"
TITLE=""
FORMAT="html"
OUTDIR="slides"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --task) TASK_ID="$2"; shift 2;;
    --repo) REPO_DIR="$2"; shift 2;;
    --since) SINCE="$2"; shift 2;;
    --until) UNTIL="$2"; shift 2;;
    --paths) PATHS="$2"; shift 2;;           # comma-separated
    --grep) EXTRA_GREP="$2"; shift 2;;
    --include-diff) INCLUDE_DIFF="true"; shift 1;;
    --max-patch-lines) MAX_PATCH_LINES="$2"; shift 2;;
    --title) TITLE="$2"; shift 2;;
    --format) FORMAT="$2"; shift 2;;         # html | pdf
    --outdir) OUTDIR="$2"; shift 2;;
    *) echo "Unknown arg: $1"; exit 1;;
  esac
done

if ! command -v git >/dev/null 2>&1; then echo "git not found"; exit 1; fi
if ! command -v python3 >/dev/null 2>&1; then echo "python3 not found"; exit 1; fi
if ! command -v quarto >/dev/null 2>&1; then echo "quarto not found"; exit 1; fi
if [[ -z "$TASK_ID" ]]; then echo "--task is required"; exit 1; fi

mkdir -p "$OUTDIR"
QMD_PATH="$OUTDIR/task_${TASK_ID//\//-}.qmd"

python3 ".claude/skills/quarto-task-slides/scripts/gen_task_qmd.py" \
  --task "$TASK_ID" --repo "$REPO_DIR" \
  ${SINCE:+--since "$SINCE"} ${UNTIL:+--until "$UNTIL"} \
  ${PATHS:+--paths "$PATHS"} \
  ${EXTRA_GREP:+--grep "$EXTRA_GREP"} \
  ${TITLE:+--title "$TITLE"} \
  --out "$QMD_PATH" \
  --format "$FORMAT" \
  --max-patch-lines "$MAX_PATCH_LINES" \
  $( [[ "$INCLUDE_DIFF" == "true" ]] && echo "--include-diff" )

# Quarto render
if [[ "$FORMAT" == "pdf" ]]; then
  quarto render "$QMD_PATH" --to pdf
else
  quarto render "$QMD_PATH" --to revealjs
fi

echo "Done. Output in: $OUTDIR"
````

### 3.3 `.claude/skills/quarto-task-slides/scripts/gen_task_qmd.py`

````python
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
    ap.add_argument("--task", required=True)
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
    args += ["--regexp-ignore-case","--grep", task_id]
    if extra_grep:
        args += ["--grep", extra_grep]
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
    title = args.title or f"Task Report: {args.task}"
    q = [fm(title)]
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    rng = f"{args.since+'..' if args.since else ''}{args.until}"
    q.append(f"# {md(title)}\n\n- **Task**: `{md(args.task)}`  \n- **Repo**: `{md(os.path.abspath(repo))}`  \n- **Range**: `{md(rng)}`  \n- **Generated**: {now}\n\n---\n")

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
````

### 3.4 `.gitignore`（例）

```gitignore
# outputs
slides/
*.html
*.pdf

# Python
__pycache__/
*.pyc
```

### 3.5 `README.md`（最小）

````markdown
# Quarto Task Slides Skill

タスクIDに紐づく Git 変更を集約し、Quarto（reveal.js）でスライド化する Claude 用スキル。
- Skill パス: `.claude/skills/quarto-task-slides/`
- 入口: `SKILL.md`

## 使い方（手動）
```bash
bash .claude/skills/quarto-task-slides/scripts/task_slides.sh --task TASK-123 --format html
````

````

---

## 4. 動作確認（ローカル）

```bash
# 例: 現在のリポに対して
bash .claude/skills/quarto-task-slides/scripts/task_slides.sh \
  --task TASK-123 --since origin/main --until HEAD --format html
# 成功すると slides/task_TASK-123.qmd と HTML/PDF が生成
````

> PDF 生成に失敗した場合は LaTeX/TinyTeX の導入を見直し（`quarto install tinytex` / `quarto update tinytex`）。([Quarto][5])

---

## 5. GitHub へ公開（推奨）

```bash
git add .
git commit -m "feat(skill): add quarto-task-slides"
git branch -M main
git remote add origin <your-repo-url>
git push -u origin main
```

---

## 6. Claude から利用する

### A. **Claude Code（プロジェクト Skill）**

1. 上記リポジトリをローカルに clone
2. Claude Code でそのフォルダを開く
3. モデルに「`TASK-123` の作業をスライド化して」と依頼
   → Claude は **`.claude/skills/`** から Skill を検出し、`SKILL.md` 記述に従いスクリプトを実行します（必要に応じて許可ダイアログあり）。([Claude Docs][1])

> 必要に応じて **allowed-tools**（許可ツールの制限）を `SKILL.md` に追加できます。未指定なら通常の許可フローです。([Claude Docs][1])

### B. **claude.ai（Web アプリ / ヘルプセンター準拠）**

* **Settings → Capabilities → Skills** で Skills/Code execution を有効化
* 「**Upload skill**」から **ZIP（Skill フォルダをルートに含む）** をアップロード
* 以後、該当依頼で自動的にスキルが使われます（トグルで ON/OFF 可）([Claude Help Center][2])

> カスタム Skill の ZIP 構成やメタデータ要件はヘルプの「**How to create custom Skills**」を参照。([Claude Help Center][6])

---

## 7. Codex 等、他エージェントでの利用

* *SKILL.md* の自動起動は **Claude 固有**の仕組みです。([Claude Docs][1])
* 他エージェントでは、**同リポのスクリプトを直接実行**させてください：

  ```bash
  bash .claude/skills/quarto-task-slides/scripts/task_slides.sh --task TASK-123 --format html
  ```
* 生成物は `slides/` に出力され、配布可能な HTML/PDF が手に入ります。

---

## 8. 実運用のコツ

* **抽出精度**：コミットメッセージにタスクID（`[TASK-123]`）を含める。スコープ（`feat(auth):`）も有効。
* **範囲指定**：デフォは `merge-base origin/main..HEAD`。マージ済タスクは `--since <merge or tag>` で固定化。
* **肥大化対策**：本編は **diffstat**、詳細は付録（`--include-diff` と `--max-patch-lines`）に。
* **チーム共有**：プロジェクト Skill は **git 共有**で自動配布できます（チームメンバーが pull すると利用可能）。([Claude Docs][1])

---

## 9. トラブルシュート（要点）

* **Skill が見つからない / 起動しない**

  * `SKILL.md` の YAML 先頭/終了やパス（`.claude/skills/<name>/SKILL.md`）を確認。
  * **description を具体的に**（「いつ使うか」まで書く）。([Claude Docs][1])
  * Claude 側の **Skills / Code execution を有効化**。([Claude Help Center][2])
* **ZIP アップロードの失敗（claude.ai）**

  * ルート直下に Skill フォルダが入っているか、`SKILL.md` があるか、サイズ上限など。([Claude Help Center][2])
* **PDF だけ失敗**

  * TinyTeX などの LaTeX を導入・更新。([Quarto][5])

---

## 10. 追加リソース

* **公式：Agent Skills（Claude Code Docs）**—Skill の場所、作り方、ベストプラクティス。([Claude Docs][1])
* **公式：Using Skills in Claude / Create custom Skills（Help Center）**—claude.ai での有効化／ZIP アップロード。([Claude Help Center][2])
* **公式：Engineering ブログ（Agent Skills 概要）**—SKILL.md とコード併用の考え方。([Anthropic][7])
* **公式：Quarto Get Started / Download / TinyTeX**—インストールと PDF 出力。([Quarto][3])
* **例：Anthropic 公開 Skill 集**—雛形の参考に。([GitHub][8])

---

### 次のアクション（最短ルート）

1. 上記の構成で **リポジトリを作成**して `git push`。
2. **Claude Code** でそのリポを開き、「`TASK-123` をスライド化して」と依頼。
3. **claude.ai** 側でも使いたければ、`.claude/skills/quarto-task-slides/` を ZIP 化して **Settings → Capabilities → Skills** からアップロード。([Claude Help Center][2])

必要であれば、**Skill 名や出力テーマ、スライドの章立て**（例：課題→対応→成果→次アクション）に合わせた **テンプレ強化版**もすぐ用意します。

[1]: https://docs.claude.com/en/docs/claude-code/skills "Agent Skills - Claude Code Docs"
[2]: https://support.claude.com/en/articles/12512180-using-skills-in-claude "Using Skills in Claude | Claude Help Center"
[3]: https://quarto.org/docs/get-started/?utm_source=chatgpt.com "Get Started"
[4]: https://learn.microsoft.com/en-us/windows/wsl/install?utm_source=chatgpt.com "How to install Linux on Windows with WSL"
[5]: https://quarto.org/docs/output-formats/pdf-engine.html?utm_source=chatgpt.com "PDF Engines"
[6]: https://support.claude.com/en/articles/12512198-how-to-create-custom-skills "How to create custom Skills | Claude Help Center"
[7]: https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills?utm_source=chatgpt.com "Equipping agents for the real world with Agent Skills"
[8]: https://github.com/anthropics/skills?utm_source=chatgpt.com "anthropics/skills: Public repository for Skills"
