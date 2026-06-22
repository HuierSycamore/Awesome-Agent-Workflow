---
name: module-interact-design
description: 模块交互设计。根据模块影响性分析结果，参考SR设计，输出受影响模块间的交互设计文档。包括：受影响模块清单、模块交互时序（含外部依赖/对外接口）、受影响模块接口设计。用于AAW工作流步骤4。Use when the user asks for 模块交互设计、module-interact-design。
version: 1.0
---

# Module Interact Design

## 工作流执行流程

工作流全景： ‘识别输入文件’ -> '启动Subagent进行交互设计' -> ‘启动Subagent进行对抗式审查’ -> ‘用户确认最终结果’

### 步骤 1: 识别输入文件

1. 明确当前工作目录
2. 判断是否存在以下输入文件：
   - `module-impact.md`（必须存在）
   - `SR-design.md`（必须存在）
   - `AR-clarify.md`(非必须，有则参考)
   - `.sdd/software_architecture.md`（用于获取模块详细信息）
3. 如果缺少必要文件，提示用户补充

### 步骤 2: 启动 Subagent 进行模块交互设计

启动一个 subagent，执行以下分析：

```
**拷贝模板：**
拷贝`<skill-dir>/references/module-interact-design-template.md` 到 `<当前工作目录>/\module-interact-design.md`

请读取以下文件进行模块交互设计：
1. 在当前工作目录下，如果存在`AR-clarify.md`则读取`AR-clarify.md`，如果不存在则读取`SR-clarify.md`
2. 增量功能设计文档：`SR-design.md`
3. AR范围澄清文档：`AR-clarify.md`,此文档是`SR-design.md`的切片。`AR-clarify`存在时，不要参考`SR-design.md`
4. 模块影响性分析文档：`module-impact.md`
5. 软件架构文档：`.sdd/software_architecture.md`

基于以上输入，填充`module-interact-design-template.md`中占位符`{{xxx}}`。

**要求：**
- 必须体现外部依赖（如数据库、外部服务、消息队列等）
- 必须体现对外接口（暴露给其他模块/系统的接口）
- 按调用时序从左到右排列参与方
- 受影响模块需要与`module-impact.md`中修改可能性为高、中、低的完全一致
- 如果与software_architecture.md中模块依赖不一致的地方，需要标记出来
```

### 步骤 3: 启动 Subagent 进行对抗式审查

启动第二个 subagent 校验 `module-interact-design.md`：

```
请对已生成的 `module-interact-design.md` 进行对抗式审查（假设其中内容完全错误）：

`module-interact-design.md`作用：在需求设计过程中，对各模块之间应该如何交互、边界如何定义的详细设计文档。

以下文档是生成`module-interact-design.md`的输入：
1. 增量功能设计文档：`SR-design.md`
2. AR范围澄清文档：`AR-clarify.md`,此文档是`SR-design.md`的切片。`AR-clarify`存在时，不要参考`SR-design.md`
3. 模块影响性分析文档：`module-impact.md`
4. 软件架构文档：`.sdd/software_architecture.md`
5. 现有模块的代码实现（探索相关模块目录）

## 审查要点

### 1. 受影响模块清单审查
- 是否遗漏了高/中可能性模块？
- 模块功能描述是否与SR-design.md中的功能点对应？
- 是否有未在module-impact.md中出现的模块？（不应新增未分析的模块）

### 2. 模块交互时序审查
- 时序图是否覆盖所有高/中可能性模块？
- 外部依赖是否完整？（数据库、缓存、外部服务、消息队列等）
- 对外接口是否准确？
- 调用链路是否与SR-design.md中的设计方案一致？
- 是否存在循环依赖或不合理的设计？

### 3. 模块接口设计审查
- 接口设计是否与现有接口风格一致？
- 请求/响应参数设计是否合理？
- 异常处理是否完整？
- 模块间数据交互是否与代码实现匹配？

### 4. 完整性审查
- 文档格式是否规范？
- 占位符是否全部填充？
- 描述是否清晰、准确、无歧义？

## 审查要求
- 假设原始文档完全错误，需重新验证每一个结论
- 必须探索代码实现来验证接口和数据交互的准确性
- 对抗式审查后不能包含`可能、有概率、应该`等不明确的语言
- 请使用问题管理工具`add_question`添加问题
```

### 步骤 4：使用问题管理工具闭环问题
若有问题，使用**问题管理工具**逐个引导用户回答**步骤3**问题，并闭环问题刷新文档

### 步骤 5: 输出结果

1、向用户展示最终的 `module-interact-design.md` 内容，并请用户确认分析结果，汇总：

2、判断当前工作目录下是否存在 `workflow.md`，若存在，则最后询问用户是否标记工作目录下模块交互设计为完成