# ASIS 证据挖掘清单

在完成 ASIS 分析前，使用本清单检查代码仓。根据实际技术栈选择适用项，不要求机械覆盖无关项。

## 1. 模块边界

- `.sdd/software_architecture.md`。该文件是模块边界必要输入，缺失、不可读或目标模块缺失时中断。
- 包、命名空间、模块、工作区、Gradle/Maven/npm/pnpm/yarn/go/cargo/dotnet 工程边界。仅在 `.sdd/software_architecture.md` 已明确边界后，用于分析边界内 ASIS 事实。
- 归属元数据、CODEOWNERS、README、架构文档、ADR。仅用于补充边界内事实，不替代模块边界。
- 目标模块的 import 关系和反向引用。仅用于验证边界内调用事实，不替代模块边界。
- 构建目标、部署清单、Helm/Kubernetes 配置、Dockerfile、服务描述文件。

## 2. 入口

- HTTP 路由、Controller、Resource、Router、Middleware。
- RPC 或 gRPC 服务、proto 文件、OpenAPI 文件、生成的客户端。
- 消息 Consumer、事件 Listener、流处理器。
- 定时任务、cron 配置、任务队列、Worker。
- CLI 命令、管理脚本、迁移脚本、批处理任务。
- 框架注册、依赖注入、插件注册、自动配置。

## 3. 内部组件

- 应用服务、领域服务、用例、命令/查询处理器。
- 领域模型、实体、值对象、聚合、状态机。
- Validator、Policy、权限校验、Guard。
- Repository、DAO、Mapper、Query Builder。
- Adapter、Client、Gateway、Facade、防腐层。
- 承载业务语义的工具类，而不是普通通用工具函数。

## 4. 数据与状态

- 数据库 Schema、迁移、种子数据、Fixture、ORM 映射。
- 表、索引、唯一约束、可空列、外键。
- 缓存 Key、TTL、失效路径、本地缓存。
- 消息 Schema、事件名、Topic、Queue、分区 Key。
- DTO、请求/响应 Schema、序列化字段别名、枚举值。
- 文件格式、对象存储路径、路径命名规则。

## 5. 运行时配置

- 各环境配置文件。
- 环境变量和密钥名称。
- Feature Flag、灰度开关、熔断或关闭开关。
- 超时、重试次数、批大小、分页默认值、限流配置。
- 按地域、租户、客户、账号、版本、部署模式区分的条件行为。

## 6. 跨模块交互

- 对其他模块的直接 import。
- API、RPC、事件、数据库、缓存或文件耦合。
- 共享常量、共享 DTO、共享数据库表。
- 启动顺序、初始化顺序、调度顺序、最终一致性假设。
- 对调用方或下游消费者的向后兼容保证。

## 7. 失败与保护行为

- 异常类、错误码、错误映射、用户可见文案。
- 重试、超时、熔断、降级、补偿。
- 事务边界、锁、乐观版本、唯一性保护。
- 幂等 Key、去重表、消息重放处理。
- 局部失败行为和清理路径。
- 安全、权限、租户隔离、数据脱敏、审计事件。

## 8. 可观测性与运维

- 日志字段、Trace Span、指标名、告警名。
- 健康检查、就绪检查、看板、运行手册。
- 运维脚本、数据修复脚本、回填脚本。
- 写在脚本或文档里的已知支持流程。

## 9. 测试作为证据

- 覆盖业务规则和边界场景的单元测试。
- 覆盖数据库、缓存、队列、RPC、HTTP 的集成测试。
- 契约测试、Golden File、快照测试。
- 与历史缺陷或兼容行为相关的回归测试。
- 揭示必填默认值的测试 Fixture 和 Builder。
- 被跳过、不稳定、忽略或隔离的测试。

## 10. 隐藏约束搜索词

搜索与技术栈匹配的变体：

- `TODO`、`FIXME`、`HACK`、`XXX`、`deprecated`、`legacy`、`compat`、`backward`、`temporary`。
- `retry`、`timeout`、`lock`、`transaction`、`idempotent`、`dedupe`、`duplicate`。
- `feature`、`flag`、`gray`、`canary`、`enable`、`disable`、`kill`。
- `permission`、`auth`、`tenant`、`audit`、`mask`、`encrypt`、`decrypt`。
- `migration`、`backfill`、`repair`、`cleanup`、`rollback`。
- `null`、`default`、`fallback`、`unknown`、`other`、`none`、`empty`。
- `limit`、`max`、`threshold`、`capacity`、`size`、`path`、`archive`、`catalog`、`default`，用于发现文档与代码之间的阈值、路径、默认值规格漂移。

## 11. 证据标准

每个重要结论至少捕获以下一种证据，并分配稳定证据编号，例如 `E1`、`E2`：

- 文件路径加行号；如无法定位行号，再记录类名、函数名或方法名。
- 配置 Key 加配置文件或环境来源。
- 测试文件加测试名。
- 迁移文件加表、索引或字段。
- API 路由、事件名、Topic、Job 名或命令名。
- 分析过程中生成的简短命令输出摘要。

ASIS 阶段必须在同名前缀 `.context.md` 中记录稳定证据编号和 ASIS 结论编号。后续正式说明书中的重要结论必须引用这些证据编号，并能在 `.context.md` 的证据索引中反查到具体位置和支撑结论。ASIS 阶段不得创建或编辑正式说明书。

没有直接证据但与本次设计相关的结论，必须标记为 `推断` 或 `待确认`，并在待确认问题或 ASIS 阻塞项中说明影响。
