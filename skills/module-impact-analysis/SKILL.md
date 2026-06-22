---
name: module-impact-analysis
description: 模块影响性分析。根据需求描述分析对软件架构中各模块的修改可能性（高/中/低/无）。支持三种输入场景：工作目录+SR-design.md+AR-clarify.md、工作目录+SR-design.md、仅一句话需求。用于AAW工作流步骤3和US设计Phase 2。Use when the user asks for 模块影响分析、模块影响性分析、module-impact、impact analysis。
version: 1.0
---

# Module Impact Analysis

## 问题管理工具

你可使用以下 MCP 工具辅助管理问题状态：

- `add_questions` – 批量添加待确认问题
- `answer_question` – 记录用户答案，并返回是否需要分析新问题的指示
- `update_answer` – 修改已记录问题的答案，用于用户纠正或补充
- `get_status` – 查看所有问题及状态（含已回答问题的答案），用于回顾已知信息
- `finalize_questions` – 检查所有问题是否已回答，并返回问答摘要

## 工作流执行流程

工作流全景： ‘识别输入场景,人工确认’ -> '启动Subagent进行影响性分析' -> ‘启动Subagent进行二次校验’ -> ‘用户确认最终结果’

### 步骤 1: 识别输入场景，明确工作目录

1. 明确当前工作目录
2. 判断是否存在'SR-design.md'、'AR-clarify.md'文档
3. 根据存在情况确定场景：

| 场景 | SR-design.md | AR-clarify.md | 分析精度 |
|------|-------------|-----------|---------|
| 场景1 | ✅ 存在 | ✅ 存在 | 高 |
| 场景2 | ✅ 存在 | ❌ 不存在 | 中 |
| 场景3 | ❌ 不存在 | ❌ 不存在 | 低 |

4. 请用户确认是否确认以此场景、此工作目录继续
    - **继续** → 进入 Step 2
    - **取消** → 结束分析

### 步骤 2: 启动 Subagent 进行模块影响性分析

启动一个 subagent，执行以下分析：

```
**拷贝模板：**
拷贝`<skill-dir>/references/module-impact-template.md` 到 `<当前工作目录>/module-impact.md`

请读取当前工作目录下的需求文件进行**模块影响性分析**：
- 如果存在`AR-clarify.md`则读取此文档，不存在则读取`SR-clarify.md`，都不存在则参考`用户一句话需求描述`。
- 增量功能设计文档：`SR-design.md`
- AR范围澄清文档：`AR-clarify.md`,此文档是`SR-design.md`的切片。`AR-clarify`存在时，不要参考`SR-design.md`
- 用户提供的一句话需求描述

读取 `.sdd/software_architecture.md` 文件，获取：
1. 模块定义表（模块名称和职责描述）
2. 配置清单/模块列表

基于 software_architecture.md 中定义的所有模块，逐一分析每个模块涉及修改的可能性（高/中/低/无），填充`module-impact.md`中占位符`{{xxx}}`。


**IMPORTANT：**
- 列举 `software_architecture.md` 中定义的所有模块，不能省略任一模块
- 当需求内容超出已定义模块职责范围时，考虑新增模块并标记 `**新增**`
- 填充模板中所有占位符 `{{***}}`
- 修改可能性分级：**高**、**中**、**低**、**无**
- 修改说明需自然语言简要描述"为什么这个模块需要修改"
- 配置影响性分析需要列出配置清单中所有目录
```

### 步骤 3: 启动 Subagent 进行对抗式审查

启动第二个 subagent 校验 `module-impact.md`：

```
请对已生成的 `module-impact.md` 进行对抗式审查（假设module-impact.md中内容完全错误）：

`module-impact.md`作用：根据新需求分析可能对哪些代码模块、代码配置产生影响，并给出代码模块、代码配置影响性。

以下文件是生成`module-impact.md`的输入：
- 增量功能设计文档：`SR-design.md`
- AR范围澄清文档：`AR-clarify.md`,此文档是`SR-design.md`的切片。`AR-clarify`存在时，不要参考`SR-design.md`
- 用户提供的一句话需求描述
- 软件架构文档：`.sdd/software_architecture.md`

对抗式审查内容：
1. 是否列举了所有模块？有无遗漏？
2. 文档中的模块是否在`software_architecture.md`中定义？如果没有，该模块是否新增，如果新增则无问题，如果不是新增则有问题。
3. 每个模块的修改可能性评估是否合理：**是否真的受影响，如果没影响则影响性修改为无，如果有影响则矫正影响概率**
4. 修改说明是否清晰、准确？
5. 是否正确地引用了需求中的功能点？
6. 配置影响性分析是否完整？
7. 是否有超出当前AR或SR范围的内容？
8. 对抗式审查后不能包含`可能、有概率`等不明确的语言，你需要仔细探索后明确这些问题
9. 请使用问题管理工具`add_question`添加问题
```
### 步骤 4：使用问题管理工具闭环问题
使用**问题管理工具**逐个引导用户回答**步骤 3**问题，并闭环问题刷新文档

### 步骤 5：询问是否刷新software_architecture.md
1、检查`module-impact.md`中是否有新增模块，且`software_architecture.md`中未定义，如果存在，则询问用户是否更新`software_architecture.md`。
2、用户同意后，更新`software_architecture.md`

### 步骤 6: 输出结果

1、向用户展示最终的 `module-impact.md` 内容，并请用户确认分析结果，并汇总：

```
## 分析结果汇总

- 分析覆盖模块数：{N} 个
- 高可能性：{X} 个模块
- 中可能性：{Y} 个模块
- 低可能性：{Z} 个模块
- 无修改：{W} 个模块

```
2、判断当前工作目录下是否存在workflow.md若存在，则：最后询问用户是否标记工作目录下模块影响性分析为完成
