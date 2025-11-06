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
   ```

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
