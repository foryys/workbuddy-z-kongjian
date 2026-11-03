# 自建技能命名与中文显示名

## 一、两套名字

| 用途 | 位置 | 值 |
|---|---|---|
| 机器标识 | `SKILL.md` frontmatter 的 `name:`、目录名 | 英文，如 `ath-sample` |
| 界面显示 | 同目录 `_marketplace_meta.json` 的 `name` | 中文，如 `ATH-示例技能` |

两者并存，互不覆盖。斜杠命令走 `name`（英文），设置页与技能列表走 `_marketplace_meta.json`（中文）。

## 二、中文显示名的命名规则

1. 只适用于 WorkBuddy：`Workbuddy-Z-中文名`
2. 跨平台通用（agent to human）：`ATH-中文名`
3. 前缀大写照写，后面直接接中文，不空格、不加下划线。

示例（名字是编的，只看格式）：
- `Workbuddy-Z-会话重命名`
- `ATH-示例技能`

## 三、写显示名的文件

在技能目录下建 `_marketplace_meta.json`：

```json
{
  "name": "ATH-示例技能",
  "source": "local"
}
```

要点（均为实测结论）：

- 必须用 `_marketplace_meta.json`。`_user_meta.json` 不参与显示名解析；`_skillhub_meta.json` 会被识别为市场来源，另有用途。
- **frontmatter 里写 `display_name:` 无效**。它只被读进内部字段，技能列表显示名仍取目录名。历史版本曾这么写过，2026-11-02 复验仍不生效，不要再用。
- 只改 meta 不生效：`SKILL.md` 本身或其目录 mtime / 大小必须变化，扫描器才会重建该条记录。追加一个换行即可。
- 客户端有内存级列表缓存，光改文件不够；重扫可由改 `SKILL.md` 触发，实测同一轮对话内即生效，不必重启客户端。
- 中文显示名不影响斜杠命令：命令始终取英文 `name`，2026-11-02 实测过纯中文名也未出现触发失败。
- 该 meta 文件不随技能功能走：换机器或从仓库取回技能后要补建，否则显示名回落到英文目录名。

## 四、新增技能时的落法

1. 目录名与 `name:` 用英文，按前缀定：`workbuddy-z-xxx` 或 `ath-xxx`。
2. 建 `_marketplace_meta.json`，按第二节规则填中文名。
3. 版本号、`agent_created: true` 等照常写在 frontmatter。
