---
name: repo-init
description: Use when the user asks for 软件实现设计/software_architect/初始化代码仓/sdd/初始化/init/更新代码仓软件架构/更新代码仓软件实现设计.
version: 1.0
---

# Repo Init
Make a todo list to follow this workflow below.

### Phase 1 Launch a subagent to initiate directory
excute `<skill-dir>/scripts/create_sdd_structure.py` in the skill to initiate directory

### Phase 2 Launch a subagent to copy file
```
if (./AGENTS.md)文件不存在
    Copy `<skill-dir>/references/AGENTS.md` to `./`
if (./.sdd/software_architecture.md)文件不存在
    Copy `<skill-dir>/references/software_architecture.md` to `./.sdd/`
```

### Phase 3 Launch a subagent to copy spec
Launch a subagent to survey the codebase to make sure what the program language is？
if `c`:
|__ Copy `<skill-dir>/assets/c-spec.md` to `./.sdd/spec.md`
if `c++`:
|__ Copy `<skill-dir>/assets/C++-spec.md` to `./.sdd/spec.md`
if `java`:
|__ Copy `<skill-dir>/assets/java-spec.md` to `./.sdd/spec.md`
if `python`:
|__ Copy `<skill-dir>/assets/Python-spec.md` to `./.sdd/spec.md`
if `javascript`:
|__ Copy `<skill-dir>/assets/js-spec.md` to `./.sdd/spec.md`

### Phase 4 Launch a subagent to Write software_architecture.md
if software_architecture.md is existed in './.sdd/' 
- skip this phase.

else
- Launch a subagent to survey the codebase，Fill in all placeholders '{{***}}' in software_architecture.md，IMPORTANT: do NOT modify or fill in any placeholders in 'section 1.2' and 'section 1.3' and 目录.

### Phase 5 Launch a subagent to Write AGENTS.md
if AGENTS.md is existed in './' 
- skip this phase.

else

Launch a subagent to survey the codebase
Detect:
- Build, test, and lint commands (especially non-standard ones)
- Languages, frameworks, and package manager
- Project structure (monorepo with workspaces, multi-module, or single project)
- Code style rules that differ from language defaults
- Non-obvious gotchas, required env vars, or workflow quirks
- Existing .claude/skills/ and .claude/rules/ directories
- Formatter configuration (prettier, biome, ruff, black, gofmt, rustfmt, or a unified format script like `npm run format` / `make fmt`)

Exclude:
- File-by-file structure or component lists (Claude can discover these by reading the codebase)
- Standard language conventions Claude already knows
- Generic advice ("write clean code", "handle errors")
- Detailed API docs or long references — use `@path/to/import` syntax instead (e.g., `@docs/api-reference.md`) to inline content on demand without bloating CLAUDE.md
- Information that changes frequently — reference the source with `@path/to/import` so Claude always reads the current version
- Long tutorials or walkthroughs (move to a separate file and reference with `@path/to/import`, or put in a skill)
- Commands obvious from manifest files (e.g., standard "npm test", "cargo test", "pytest")

Be specific: "Use 2-space indentation in TypeScript" is better than "Format code properly."

Do not repeat yourself and do not make up sections like "Common Development Tasks" or "Tips for Development" — only include information expressly found in files you read.

Write a minimal AGENTS.md according to the .sdd/AGENTS.md.

### Phase 6 **update '目录'**
Update section '目录' with correct line numbers after all content is assembled. Do NOT fill in placeholders.

### Phase 7 **Remind user should check what is insure**
Remind user should check what is insure