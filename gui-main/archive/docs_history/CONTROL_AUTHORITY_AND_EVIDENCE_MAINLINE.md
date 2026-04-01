# Control Authority and Evidence Mainline

这一轮主线不再满足于“前后端能互联”，而是把**唯一控制权**和**会话证据封印**纳入正式产品骨架。

## 1. 唯一控制权

正式写命令现在必须经过 `ControlAuthorityService`。

它负责：
- 控制租约（lease）申请与释放
- lease 与 session 的绑定
- 命令上下文标准化（actor / role / workspace / session / intent / lease）
- 冲突写命令阻断

目标不是简单“谁先点按钮谁生效”，而是确保：
- 同一时刻只有一个正式控制源
- UI / headless / web / adapter 看到的是同一控制主权状态
- 写命令有来源、意图和会话归属

## 2. 会话证据封印

正式 session 不再只生成若干产物文件，还会生成 `session_evidence_seal.json`。

封印文件固定记录：
- session manifest 摘要
- artifact registry 摘要
- 产物哈希与 schema
- seal digest
- producer / timestamp / schema version

这样做的目的有两个：
- 让 replay / review / QA 能验证 session 产物是否被篡改或漂移
- 让 release gate 有正式可追溯的冻结点

## 3. 新的 API 主线

headless API 现在提供：
- `GET /api/v1/control-authority`
- `POST /api/v1/control-lease/acquire`
- `POST /api/v1/control-lease/release`
- `GET /api/v1/sessions/current/evidence-seal`

这些接口让桌面端和 Web 端不再只读取“系统状态”，还能读取：
- 当前唯一控制源
- 当前租约归属
- 当前 session 是否已经形成正式封印证据

## 4. 正式启动门禁的新增要求

启动正式扫查前，现在不仅要看：
- SDK alignment
- backend link
- control plane
- bridge observability

还要看：
- 唯一控制权是否处于合法状态
- 当前 session 是否可形成冻结后的证据闭环

## 5. 与真实机器人联调的边界

这一轮交付的是：
- 控制权租约骨架
- API/desktop/headless 的统一控制权视图
- 会话证据封印主线

它并不等于：
- 已在真实 xCore SDK 动态库上完成硬件独占联调
- 已替代控制柜或 RobotAssist 的底层仲裁能力

真实环境里，最终的控制权仲裁仍应以 `cpp_robot_core` 和真实控制器状态为准。
