# Quarto Task Slides Skill

タスクIDに紐づく Git 変更を集約し、Quarto（reveal.js）でスライド化する Claude 用スキル。

## 概要

このスキルは、指定したタスクID（例: `TASK-123`）やブランチ名に関連するGitコミットを抽出し、以下の情報を含むスライドを自動生成します：

- コミット履歴とdiffstat
- よく変更されたファイルのトップ10
- オプションでパッチの詳細

生成されるスライドは、Quarto（reveal.js）を使用したHTML/PDF形式です。

## ディレクトリ構成

```
.
├─ .claude/
│  └─ skills/
│      └─ quarto-task-slides/
│          ├─ SKILL.md              # スキル定義ファイル
│          └─ scripts/
│              ├─ task_slides.sh    # メインスクリプト
│              └─ gen_task_qmd.py   # QMD生成Pythonスクリプト
├─ .gitignore
└─ README.md
```

## 前提条件

以下のツールがインストールされている必要があります：

- `git`
- `python3`
- `quarto` - [インストール方法](https://quarto.org/docs/get-started/)
- （PDF生成の場合）TinyTeX: `quarto install tinytex`

## インストール方法

### 方法1: 個人スコープにインストール（推奨）

すべてのプロジェクトでこのスキルを使えるようにするには、個人スコープにコピーします：

```bash
# このリポジトリをクローン
git clone <your-repo-url> QuartoSlideGenerator
cd QuartoSlideGenerator

# 個人スコープにコピー
mkdir -p ~/.claude/skills/
cp -r .claude/skills/quarto-task-slides ~/.claude/skills/

# 確認
ls -la ~/.claude/skills/quarto-task-slides/
```

これで、Claude Code を使用するすべてのプロジェクトでこのスキルが利用可能になります。

### 方法2: プロジェクト固有のスキルとして利用

特定のプロジェクトでのみ使用する場合は、そのプロジェクトの `.claude/skills/` ディレクトリにコピーします：

```bash
cd /path/to/your-project
mkdir -p .claude/skills/
cp -r /path/to/QuartoSlideGenerator/.claude/skills/quarto-task-slides .claude/skills/
```

### 方法3: シンボリックリンクで参照

複数のプロジェクトで最新版を共有したい場合、シンボリックリンクを使用します：

```bash
cd /path/to/your-project
mkdir -p .claude/skills/
ln -s /path/to/QuartoSlideGenerator/.claude/skills/quarto-task-slides .claude/skills/
```

## 使い方

### Claude Code での利用

スキルがインストールされていると、Claude は自動的に検出します。以下のように依頼してください：

```
TASK-123 のスライドを作成して
```

```
feature/authentication ブランチの作業内容をスライドにまとめて
```

Claude がスキルを起動し、必要に応じてパラメータを確認してから実行します。

### 手動実行

スクリプトを直接実行することもできます：

```bash
# 基本的な使い方（HTML形式）
bash .claude/skills/quarto-task-slides/scripts/task_slides.sh \
  --task TASK-123 --format html

# 特定のパスに限定
bash .claude/skills/quarto-task-slides/scripts/task_slides.sh \
  --task TASK-123 --paths src/auth --format html

# PDF形式でパッチ付き
bash .claude/skills/quarto-task-slides/scripts/task_slides.sh \
  --task feature/2fa --include-diff --format pdf

# 範囲を指定
bash .claude/skills/quarto-task-slides/scripts/task_slides.sh \
  --task TASK-123 --since origin/main --until HEAD --format html
```

### パラメータ

- `--task <id>` （必須）: タスクIDまたはブランチ名
- `--repo <dir>` （既定: `.`）: Gitリポジトリのパス
- `--since <ref>` （省略時: `merge-base origin/main..HEAD`）: コミット範囲の開始点
- `--until <ref>` （既定: `HEAD`）: コミット範囲の終了点
- `--paths <paths>` （任意）: カンマ区切りのパスフィルタ（例: `src/auth,app/`）
- `--grep <pattern>` （任意）: 追加のgrepフィルタ
- `--include-diff` （既定: false）: パッチの詳細を含める
- `--max-patch-lines <num>` （既定: 600）: パッチの最大行数
- `--title <title>` （任意）: スライドのタイトル
- `--format <html|pdf>` （既定: `html`）: 出力形式
- `--outdir <dir>` （既定: `slides/`）: 出力ディレクトリ

## 出力

スライドは `slides/` ディレクトリに生成されます：

- `slides/task_TASK-123.qmd` - Quarto マークダウンファイル
- `slides/task_TASK-123.html` または `slides/task_TASK-123.pdf` - 生成されたスライド

## トラブルシューティング

### スキルが見つからない

- `SKILL.md` が正しい場所にあるか確認（`.claude/skills/quarto-task-slides/SKILL.md`）
- Claude Code の設定で Skills / Code execution が有効化されているか確認

### PDF生成が失敗する

TinyTeX をインストール：

```bash
quarto install tinytex
```

または更新：

```bash
quarto update tinytex
```

### git/python3/quarto が見つからない

必要なツールをインストールしてください：

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y git python3

# Quarto
# https://quarto.org/docs/get-started/ を参照
```

## ベストプラクティス

- **コミットメッセージ**: タスクIDを含める（例: `[TASK-123] Add authentication feature`）
- **範囲指定**: デフォルトは `merge-base origin/main..HEAD`。マージ済みタスクは `--since` で固定化
- **肥大化対策**: 本編はdiffstatのみ、詳細は付録（`--include-diff` と `--max-patch-lines`）に

## 更新方法

### 個人スコープにインストールした場合

```bash
cd /path/to/QuartoSlideGenerator
git pull
cp -r .claude/skills/quarto-task-slides ~/.claude/skills/
```

## 参考リンク

- [Claude Code - Agent Skills](https://docs.claude.com/en/docs/claude-code/skills)
- [Quarto - Get Started](https://quarto.org/docs/get-started/)
- [Quarto - Reveal.js](https://quarto.org/docs/presentations/revealjs/)

## ライセンス

MIT License - 詳細は [LICENSE](LICENSE) ファイルを参照してください。
