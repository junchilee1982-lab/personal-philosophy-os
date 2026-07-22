# 数据契约

## Vault 定位

统一使用 `ppos` 解析 Vault。优先级：

1. 命令行 `--vault`
2. `PPOS_VAULT`
3. `PERSONAL_THOUGHT_VAULT_HOME`
4. 用户配置
5. 平台默认数据目录

不要硬编码用户名、主目录或某一台机器的路径。

## 标准布局

```text
vault.json
roots.json
cards/cards.jsonl
mappings/root-mappings.jsonl
mappings/verdicts.jsonl
principles/principles.jsonl
cases/cases.jsonl
reflections/reflections.jsonl
sources/external-sources.jsonl
```

## 读取前校验

先运行：

```bash
ppos validate --json
```

校验失败时停止写入。不要使用 grep 绕过坏 JSON、坏版本链、未知引用或权限错误。

## 追加式版本

映射、原则与外部来源使用对象 ID 加版本号形成唯一键。旧版本不原地修改。读取时，用户已确认版本优先于 AI 候选；更高版本的 AI 候选不能覆盖已有的人类裁决。

否决写入独立 verdict ledger，撤销否决也追加新裁决，不删除历史。

## JSONL

文件必须是严格 UTF-8。只把真实换行字节当作记录分隔符；不要使用会把 Unicode 行分隔字符拆成新记录的通用 splitlines 行为。
