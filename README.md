# Personal Philosophy OS（个人思想库）

一个本地优先、证据优先的个人思想系统。它不按“哲学、心理学、管理学”等知识来源整理材料，而是把思想组织到稳定的人生根问题之下，再连接个人原则、真实案例、决策复盘、外部来源与辩论修订。

> 当前版本：`v0.1.0-alpha.1`。这是可安装、可验证的公开引擎预发行版，不是稳定版。

## 它解决什么

- 读到一段文案时，判断它对应哪个人生根问题、是否只是已有原则的新表达。
- 面对现实选择时，先调用自己的已确认原则与历史证据，而不是临时拼一套大道理。
- 把“事实、解释、责任、动机、代价”分开，形成最小行动。
- 用最强反方检验原则，修订适用条件，而不是让 AI 一味认同。
- 让外部思想保持可追溯：读过不等于认同，引用不等于属于自己。

## 最重要的隐私边界

这个仓库只包含通用引擎、技能说明、Schema、空模板和合成示例。

你的思想卡、原始对话、关系案例、复盘、影子报告和运行日志始终保存在仓库之外的本地 Vault。引擎默认不联网、无遥测，也不会自动提交或上传任何 Vault 数据。完整边界见 [PRIVACY.md](PRIVACY.md)。

```text
公开 GitHub 仓库                 你的本地 Vault
engine / skill / schemas   →    cards / mappings / principles
templates / synthetic demo      cases / reflections / sources
可公开、可升级                   私有、由你掌控
```

## 5 分钟开始

环境要求：Python 3.10 或更高版本，macOS / Linux / Windows。

```bash
git clone https://github.com/junchilee1982-lab/personal-philosophy-os.git
cd personal-philosophy-os
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

Windows PowerShell 激活虚拟环境：

```powershell
.venv\Scripts\Activate.ps1
```

初始化一个带完全虚构示例的本地 Vault：

```bash
ppos init --vault "$HOME/.personal-philosophy-os/vault" --demo
ppos data use "$HOME/.personal-philosophy-os/vault"
ppos doctor
```

安装 Codex 与 Claude Code 技能：

```bash
ppos skill install --target both
```

然后可以这样说：

- “使用个人思想库，分析这段文案和我的原则是什么关系。”
- “使用个人思想库，按五问熔炉帮我想清楚这次选择。”
- “使用个人思想库，选这条原则跟我辩一辩。”

## CLI

```text
ppos init --vault PATH [--demo]             初始化空 Vault 或合成演示 Vault
ppos data use PATH                          校验并记住默认 Vault
ppos validate [--vault PATH] [--json]       校验结构、权限和版本链
ppos doctor [--vault PATH] [--json]         检查引擎、Vault 与技能安装
ppos search QUERY --channel evidence        检索可回源的已确认原话
ppos search QUERY --channel conclusion      检索已确认原则
ppos context ROOT_ID [--include-candidates] 读取一个根问题的最小上下文
ppos mode show                              查看 rollout 模式
ppos mode set active --confirm              显式切换模式
ppos skill install --target both            安装技能
ppos skill uninstall --target both          只卸载本项目管理的技能
```

Vault 解析优先级：命令行 `--vault` → `PPOS_VAULT` → `PERSONAL_THOUGHT_VAULT_HOME` → 用户配置 → 平台默认目录。

## Python API（Alpha）

公开 API 在 Alpha 期间遵循语义化版本，但仍可能在后续预发行版中收窄；升级前请看 Changelog。

```python
from personal_philosophy_os import open_vault, validate_vault

report = validate_vault("path/to/local-vault")
if report.valid:
    vault = open_vault("path/to/local-vault")
    evidence = vault.search("选择的代价", channel="evidence", top_k=5)
    context = vault.root_context("root-04")
```

稳定公开面是 `open_vault`、`init_vault`、`validate_vault`、`Vault.search`、`Vault.root_context`、`Vault.set_mode` 及其返回的数据类。内部文件布局在 Schema 版本升级时可能迁移。

## 默认人生根问题

| 编号 | 问题 |
|---|---|
| root-00 | 待归区：现在还不知道它属于哪里 |
| root-01 | 我是谁，我愿意成为什么样的人？ |
| root-02 | 我如何与他人相处，同时不失去自己？ |
| root-03 | 我如何面对痛苦、不确定和失去？ |
| root-04 | 我如何选择，并承担选择的代价？ |
| root-05 | 我如何成长、行动和修正自己？ |

这是一套默认模板，不是知识分类法。一级骨架只能由 Vault 所有者修改；AI 只能提案。原子卡不可变，根问题映射独立保存，因此以后调整骨架不会改写原始证据。

## 核心治理规则

1. **允许不知道**：归不清就进入 `root-00`，禁止硬塞。
2. **AI 提案、人类确认**：AI 不能确认原则、改变一级骨架或把外部观点变成用户原则。
3. **只追加版本**：核心记录保留历史；已确认版本不会被更高版本的 AI 候选覆盖。
4. **外部思想隔离**：外部原文、AI 释义、用户自己的解释使用不同字段。
5. **默认只读**：分析、照镜子、判同不自动保存；写入必须有明确请求。
6. **证据和结论分层**：一句原话能证明“说过”，不能自动证明稳定人格或普遍规律。

## 项目结构

```text
skills/personal-thought-vault/   Codex / Claude Code 技能
src/personal_philosophy_os/      Python 引擎与 CLI
schemas/                         可公开的数据契约
templates/vault/                 空 Vault 说明
examples/synthetic-vault/        完全虚构的演示数据
tests/                           单元、集成与安装测试
scripts/check_public_safety.py   发布前隐私与秘密门禁
```

架构、数据模型和完整工作流见 [docs/architecture.md](docs/architecture.md)、[docs/data-model.md](docs/data-model.md) 与 [docs/workflows.md](docs/workflows.md)。

## 开发与验证

```bash
python -m unittest discover -s tests -v
python scripts/check_public_safety.py --all
python scripts/validate_skill.py skills/personal-thought-vault
python -m pip wheel . --no-deps --wheel-dir dist
```

贡献前请读 [CONTRIBUTING.md](CONTRIBUTING.md)。安全问题不要在公开 Issue 中粘贴私人 Vault 内容，见 [SECURITY.md](SECURITY.md)。

## 许可证

引擎和通用技能使用 [Apache License 2.0](LICENSE)。你的本地 Vault 数据不因使用本项目而被改变所有权或纳入本项目许可证。
