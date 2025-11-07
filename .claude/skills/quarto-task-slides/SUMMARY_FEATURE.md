# Commit Summary Generation Feature

## Overview

The quarto-task-slides skill now supports automatic generation of natural language summaries for commits. This feature helps make commit changes more understandable for non-technical stakeholders, team reviews, and documentation purposes.

## Features

### Summary Modes

1. **None (default)**: No summary generation
2. **Template Mode**: Extracts structured information from commit message bodies
3. **AI Mode**: Uses Claude API to generate comprehensive summaries
4. **Manual Mode**: Loads pre-written summaries from files

## Usage Examples

### 1. Template Mode

Extracts bullet points and structured content from commit message bodies.

```bash
bash .claude/skills/quarto-task-slides/scripts/task_slides.sh \
  --since origin/main --until HEAD \
  --summary-mode template
```

**Best for:**
- Well-structured commit messages
- Commits following conventional commit format
- Quick summaries without API costs

### 2. AI Mode

Uses Claude to generate intelligent summaries from commit data.

#### In Claude Code Environment (Recommended)

When using Claude Code, **no API key is required**! Claude Code automatically generates summaries.

```bash
bash .claude/skills/quarto-task-slides/scripts/task_slides.sh \
  --since origin/main --until HEAD \
  --summary-mode ai
```

**How it works:**
1. The script extracts commit information to `.commit-summaries/.pending_summaries.json`
2. Claude Code automatically reads the JSON file
3. Claude Code generates natural language summaries for each commit
4. Summaries are saved as `.commit-summaries/<short-sha>.md`
5. The script automatically re-runs with manual mode to generate slides

**Advantages:**
- No API key needed
- No additional API costs
- Seamless integration with Claude Code workflow
- Uses the same Claude instance you're already interacting with

#### Standalone Mode (without Claude Code)

For use outside Claude Code environment:

```bash
export ANTHROPIC_API_KEY="your-api-key-here"

bash .claude/skills/quarto-task-slides/scripts/task_slides.sh \
  --since origin/main --until HEAD \
  --summary-mode ai \
  --summary-api-key "$ANTHROPIC_API_KEY"
```

**Requirements:**
- `anthropic` package: `pip install anthropic`
- Valid Anthropic API key

**Best for:**
- Comprehensive analysis of changes
- Stakeholder presentations
- When commit messages lack detail
- Professional documentation

### 3. Manual Mode

Uses pre-written markdown summaries from a directory.

```bash
# 1. Create summaries directory
mkdir -p .commit-summaries

# 2. Write a summary for a commit (use full or short SHA)
cat > .commit-summaries/abc1234.md << 'EOF'
## Major Database Migration

This commit implements a new user authentication system:

**Key Changes:**
- Migrated from bcrypt to Argon2 for password hashing
- Added multi-factor authentication support
- Implemented session management with Redis

**Impact:**
- 40% improvement in login speed
- Enhanced security with modern algorithms
- Better scalability for concurrent users
EOF

# 3. Generate slides with manual summaries
bash .claude/skills/quarto-task-slides/scripts/task_slides.sh \
  --since origin/main --until HEAD \
  --summary-mode manual \
  --summary-dir .commit-summaries
```

**Best for:**
- Highly customized summaries
- Consistent formatting across projects
- Including non-code context (business impact, etc.)
- Reusable summaries across multiple presentations

## Configuration

### Command-Line Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--summary-mode` | Summary generation mode: `none`, `template`, `ai`, `manual` | `none` |
| `--summary-api-key` | Anthropic API key for AI mode | (from `ANTHROPIC_API_KEY` env) |
| `--summary-dir` | Directory containing manual summary files | `.commit-summaries` |

### Environment Variables

- `ANTHROPIC_API_KEY`: API key for AI mode (alternative to `--summary-api-key`)

## Summary File Format (Manual Mode)

Manual summary files should be placed in the summaries directory with the filename format:

```
<commit-sha>.md  or  <short-sha>.md
```

Examples:
- `.commit-summaries/abc123def456.md` (full SHA)
- `.commit-summaries/abc123d.md` (short SHA)

File content can be any markdown text. It will be inserted directly into the slide.

## Output Example

When summary mode is enabled, each commit slide will include a "Summary:" section:

```markdown
### abc1234 — Add user authentication feature
`2025-11-07 14:30:00 +0900` / John Doe

**Summary:**

- Implemented JWT-based authentication system
- Added login/logout endpoints with secure token management
- Integrated with existing user database
- Added middleware for protected routes
- Includes comprehensive unit tests

```text
abc1234 Add user authentication feature
 src/auth/jwt.py        | 120 +++++++++++++++++++++++
 src/routes/auth.py     |  85 ++++++++++++++++
 tests/test_auth.py     | 156 +++++++++++++++++++++++++++++
 3 files changed, 361 insertions(+)
```
```

## AI Summary Generation Details

The AI mode analyzes:
1. Commit subject and body
2. Diffstat (file changes and line counts)
3. Code changes preview (first 2000 characters of diff)

The AI generates:
- What functionality was added/modified/removed
- Why the change was made (if inferable)
- Key highlights for non-technical stakeholders

## Best Practices

### Template Mode
- Write detailed commit messages with bullet points
- Use consistent formatting (-, *, + for lists)
- Include context in commit body

### AI Mode
- Use for important commits or milestones
- Consider API costs for large commit ranges
- Provide detailed commit messages for better AI analysis

### Manual Mode
- Create summaries for key commits only
- Use consistent formatting across summaries
- Include business context and impact
- Store summaries in version control for team reuse

## Use Cases

1. **Sprint Reviews**: Generate slides with AI summaries for team presentations
2. **Stakeholder Updates**: Use manual mode for curated, business-focused summaries
3. **Onboarding**: Help new team members understand recent changes
4. **Documentation**: Template mode for extracting structured commit information
5. **Release Notes**: Combine modes for comprehensive release documentation

## Troubleshooting

### "anthropic package not installed"
```bash
pip install anthropic
```

### "No API key provided"
Set the environment variable:
```bash
export ANTHROPIC_API_KEY="your-api-key"
```

Or pass it directly:
```bash
--summary-api-key "your-api-key"
```

### "No manual summary found"
Ensure summary file exists at:
- `.commit-summaries/<full-sha>.md`, or
- `.commit-summaries/<short-sha>.md`

Check the short SHA with: `git log --oneline`

## Performance Notes

- **Template mode**: Fast, no external dependencies
- **AI mode**: ~1-2 seconds per commit (API latency)
- **Manual mode**: Fast, file I/O only

For large commit ranges with AI mode, consider:
1. Using `--paths` to limit scope
2. Generating summaries in batches
3. Caching AI summaries as manual files for reuse
