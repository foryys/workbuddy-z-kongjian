# -*- coding: utf-8 -*-
"""工作空间体检（**只读**，不改任何文件）

用法：
    python 体检.py                          # 体检当前目录（自动判文本型／代码型）
    python 体检.py <项目根路径>              # 体检指定项目
    python 体检.py <项目根> --type text      # 手动指定型：text / code（判错时用）

输出两块：
    A. 目录体检 —— 一级目录数 / 项目根文件数 / .workbuddy 顶层数 / 顶层散文件数 / archive 顶层条目数 / output 顶层散文件数
    B. 体积体检 —— 项目记忆 / 日志 / 用户级记忆 / 项目规则与 WORKBUDDY / 技能 SKILL.md（按官方「<5,000 词」）/ 临时区 / 归档大件 / 同一产物快照份数（剥时间戳归组，>3 份报警）

阈值与处置口径见 SKILL 第六节：6.1 技能自身（官方口径）／ 6.2 项目资源。
本脚本**只打印报告**；归位、归档、删除一律由助手按纪律单独执行（删除先出清单让用户点头）。
"""

import re
import sys
from pathlib import Path

KB = 1024
MB = KB * 1024

# ── 项目型判定（2026-10-29 加）──────────────────────────────────────
# 两型的差别只有一条：数不数一级目录个数。
#   文本型 → 一级目录 ≤3（archive/ output/ .workbuddy/）
#   代码型 → 不数个数（src/ bin/ 由代码本身决定，硬压只会逼人往根上乱塞），
#            改判「源码夹与产物夹各一个 ＋ 根散文件 ≤6」
# 判错的代价很小：命令行 --type text / --type code 手动指定即可。
CODE_MARKER_FILES = ("go.mod", "package.json", "pom.xml", "requirements.txt",
                     "Cargo.toml", "build.gradle", "CMakeLists.txt", "pyproject.toml")
CODE_MARKER_GLOBS = ("*.sln", "*.csproj", "*.vcxproj", "*.pro")
CODE_MARKER_DIRS = ("src", "bin", "dist", "app")
DASHBOARD = "看板.html"  # 模板就放 .workbuddy/ 下，不算散件、不占顶层名额


def detect_project_type(root: Path) -> str:
    """只看项目根这一层。认不出来按 text 处理（保守：宁可多提醒，不会漏清）。"""
    for name in CODE_MARKER_FILES:
        if (root / name).exists():
            return "code"
    for pat in CODE_MARKER_GLOBS:
        if any(root.glob(pat)):
            return "code"
    for name in CODE_MARKER_DIRS:
        if (root / name).is_dir():
            return "code"
    return "text"

# ── 阈值（与 SKILL 第六节判定总表一致，改这里就是改口径）────────────────
DIR_LIMITS = {
    "一级目录数": 3,
    "项目根文件数": 6,
    ".workbuddy 顶层数": 4,
    ".workbuddy 顶层散文件数": 0,
    "output 顶层散文件数": 0,
}
SIZE_LIMITS = {
    # 两个记忆文件按**字符**算 —— 客户端注入上限按字符；其余按字节。
    # 数字出处（客户端原文，2026-10-13 从 app.asar 挖出）：
    #   项目记忆 `Limit: 3,000 chars/session`；用户级 `Limit: 4,000 chars/session`。
    "项目记忆 MEMORY.md": 3000,
    "日志 YYYY-MM-DD.md": 8 * KB,
    "用户级记忆": 4000,
}
BIG_ARCHIVE = 10 * MB  # 归档件超过这个体积 → 归档前先问用户
SNAPSHOT_KEEP = 3      # 同一产物快照只留最近 3 份（2026-10-15 用户定，原为 1 份）

HOME_WB = Path.home() / ".workbuddy"


def user_memory_path() -> Path:
    """用户级记忆的真身：`~/.workbuddy/user-<uid>-<企业id>/MEMORY.md`。
    旧路径 `~/.workbuddy/MEMORY.md` 已废弃 —— 2026-10-13 实测该文件不存在，
    体检因此**长期漏检**这一项。"""
    cand = sorted(HOME_WB.glob("user-*/MEMORY.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    return cand[0] if cand else HOME_WB / "MEMORY.md"


def human(n: int) -> str:
    if n >= MB:
        return f"{n / MB:.1f} MB"
    return f"{n / KB:.1f} KB"


# ── 快照归组：把文件名里的时间戳／版本号剥掉，剩下的算「同一产物」──────────
# 这是**启发式**：只用于体检报告（先出清单、人工确认后才动文件），不直接当删除依据。
_SNAP_PATS = [
    r"[-_ ]?20\d{6}[-_ ]?\d{0,6}",   # YYYYMMDD / YYYYMMDD_HHMMSS
    r"[-_ ]?\d{6}(?=[.\-_ (]|$)",    # 6 位时间戳（如 _123416）
    r"[-_ ]?v\d+([.\-]\d+)*",        # v1 / v1.2
    r"[-_ (]?\(?\d{1,3}\)?$",        # 结尾编号：(1) / -12
]


def snapshot_key(p: Path) -> str:
    stem = p.stem
    for pat in _SNAP_PATS:
        stem = re.sub(pat, "", stem, flags=re.IGNORECASE)
    stem = re.sub(r"[-_ ]+", "-", stem).strip("-_ ").lower()
    return f"{stem}{p.suffix.lower()}"


def check(label: str, value, limit=None, bytes_mode: bool = False) -> str:
    """bytes_mode=True 时 value/limit 都是字节数；否则按纯数字比大小。"""
    if limit is None:
        return f"      {label:<36} {value}  （仅报数）"
    flag = "OK  " if value <= limit else "⚠️ 超"
    shown = human(value) if bytes_mode else str(value)
    cap = human(limit) if bytes_mode else str(limit)
    return f"{flag} {label:<36} {shown}  （上限 {cap}）"


def dir_audit(root: Path, ptype: str) -> list:
    """目录体检五项"""
    out = []
    entries = [p for p in root.iterdir() if p.name != ".git"]
    dirs = [p for p in entries if p.is_dir()]
    files = [p for p in entries if p.is_file()]

    if ptype == "code":
        out.append("      项目型：**代码型** → 一级目录只报数不判超（看根散文件 ≤6、源码夹与产物夹各一个）")
        out.append(check("一级目录数", len(dirs)))
        out.append("       目录清单：" + ("、".join(sorted(p.name for p in dirs)) or "无"))
    else:
        out.append("      项目型：**文本型** → 一级目录 ≤3（archive/ output/ .workbuddy/）")
        out.append(check("一级目录数", len(dirs), DIR_LIMITS["一级目录数"]))
    out.append(check("项目根文件数", len(files), DIR_LIMITS["项目根文件数"]))

    wb = root / ".workbuddy"
    if wb.is_dir():
        wb_entries = list(wb.iterdir())
        # 看板放 .workbuddy/ 是模板口径，不算散件、不占顶层名额
        counted = [p for p in wb_entries if p.name != DASHBOARD]
        wb_files = [p for p in counted if p.is_file()]
        out.append(check(".workbuddy 顶层数", len(counted), DIR_LIMITS[".workbuddy 顶层数"]))
        out.append(check(".workbuddy 顶层散文件数", len(wb_files), DIR_LIMITS[".workbuddy 顶层散文件数"]))
        if wb_files:
            out.append("       散文件清单：" + "、".join(p.name for p in wb_files))
    else:
        out.append("       未发现 .workbuddy/（单次档属正常）")

    arc = root / "archive"
    if arc.is_dir():
        out.append(check("archive 顶层条目数", len(list(arc.iterdir()))))

    # ── output/ 顶层散件：应按客户端会话名归进任务文件夹 ──────────────────
    # 命名规则见 project-rules.md「output/ 的任务文件夹名 ＝ 客户端会话名」。
    # 这里只报数（散件清单），不判归属 —— 归属要查客户端会话名，脚本不连库。
    outd = root / "output"
    if outd.is_dir():
        od_files = [p for p in outd.iterdir() if p.is_file()]
        od_dirs = [p for p in outd.iterdir() if p.is_dir()]
        out.append(check("output 顶层散文件数", len(od_files), DIR_LIMITS["output 顶层散文件数"]))
        if od_files:
            out.append("       散件清单（应按会话名归进任务文件夹）："
                       + "、".join(p.name for p in od_files))
        out.append("       output 任务文件夹数：" + str(len(od_dirs)))
    else:
        out.append("       未发现 output/（单次档属正常）")
    return out


def size_audit(root: Path) -> list:
    """体积体检"""
    out = []
    wb = root / ".workbuddy"
    skill = Path(__file__).resolve().parent.parent

    targets = [
        ("项目记忆 MEMORY.md", wb / "memory" / "MEMORY.md", False),
        ("用户级记忆", user_memory_path(), False),
    ]
    for label, path, bmode in targets:
        if path.is_file():
            val = path.stat().st_size if bmode else len(path.read_text(encoding="utf-8", errors="replace"))
            shown = label if bmode else label + "（字符）"
            out.append(check(shown, val, SIZE_LIMITS[label], bytes_mode=bmode))
        else:
            out.append(f"      {label:<36} 不存在，跳过")

    # ── 技能自身 SKILL.md —— 官方口径是「< 5,000 词」，**不是 KB** ─────────────
    # 保守判法：中文一个词至少一个字，所以「汉字数 + 英文词数」是词数的**上界**；
    # 这个上界都 < 5000 → 一定没超官方线。上界 ≥ 5000 才需要人工细看。
    sk = skill / "SKILL.md"
    if sk.is_file():
        txt = sk.read_text(encoding="utf-8", errors="replace")
        hanzi = len(re.findall(r"[\u4e00-\u9fff]", txt))
        enw = len(re.findall(r"[A-Za-z][A-Za-z0-9\-./]*", txt))
        total = hanzi + enw
        flag = "OK  " if total < 5000 else "⚠️ 需人工核"
        out.append(f"{flag} {'技能 SKILL.md 正文（词）':<34} 汉字{hanzi} ＋ 英文词{enw} ＝ {total}"
                   f"  （官方线 <5000 词；此数为保守上界）")

        # references/ 单文件：官方无上限，但 >10k 词必须在 SKILL.md 里有检索式。
        # 这里不判「超限」，只判**有没有留检索式**（留了才算合格）。
        refs_dir = skill / "references"
        if refs_dir.is_dir():
            for rp in sorted(refs_dir.glob("*.md")):
                rtxt = rp.read_text(encoding="utf-8", errors="replace")
                r_hanzi = len(re.findall(r"[\u4e00-\u9fff]", rtxt))
                r_enw = len(re.findall(r"[A-Za-z][A-Za-z0-9\-./]*", rtxt))
                r_total = r_hanzi + r_enw
                if r_total <= 10000:
                    continue  # 未过 10k 词，不需要检索式
                has_hint = rp.name in txt
                flag2 = "OK  " if has_hint else "⚠️ 缺"
                out.append(f"{flag2} {'参考件 ' + rp.name:<34} 约 {r_total} 词"
                           f"（汉字{r_hanzi}＋英文词{r_enw}）"
                           f"  {'SKILL.md 已给检索式' if has_hint else 'SKILL.md 里没给 grep 检索式'}")

        # 技能包自洁：SKILL.md 之外的散件、.bak 备份、临时文件 —— 都会被打进技能包。
        stray = [p.name for p in skill.iterdir()
                 if p.is_file() and p.name != "SKILL.md"]
        if stray:
            out.append(f"      {'技能根散件':<34} ⚠️ {'、'.join(stray)}"
                       f"（技能包只该有 SKILL.md ＋ 三个子目录）")
        else:
            out.append(f"OK   {'技能根散件':<34} 无（只有 SKILL.md）")
        backups = [p.name for p in skill.rglob("*.bak*")]
        if backups:
            out.append(f"      {'遗留 .bak 备份件':<32} ⚠️ {'、'.join(backups)}"
                       f"（移出技能包，别留着）")

    mem_dir = wb / "memory"
    if mem_dir.is_dir():
        for p in sorted(mem_dir.glob("*.md")):
            if p.name == "MEMORY.md":
                continue
            out.append(check(f"日志 {p.name}", p.stat().st_size, SIZE_LIMITS["日志 YYYY-MM-DD.md"], bytes_mode=True))

    for name in ("tmp",):
        d = wb / name
        if d.is_dir():
            total = sum(p.stat().st_size for p in d.rglob("*") if p.is_file())
            n = sum(1 for p in d.rglob("*") if p.is_file())
            flag = "OK  " if total == 0 else "⚠️ 清"
            out.append(f"{flag} {'.workbuddy/' + name:<36} {human(total)} / {n} 件  （收尾后应为 0）")

    # ── 项目内「要读的文件」（SKILL 6.2 表；「必读段 ≤2 KB」那条留给人工核）──
    rules_dir = wb / "rules"
    if rules_dir.is_dir():
        for p in sorted(rules_dir.glob("*.md")):
            out.append(check(f"规则 {p.name}", p.stat().st_size, 24 * KB, bytes_mode=True))
    wbd = root / "WORKBUDDY.md"
    if wbd.is_file():
        out.append(check("WORKBUDDY.md", wbd.stat().st_size, 6 * KB, bytes_mode=True))

    arc = root / "archive"
    if arc.is_dir():
        total = sum(p.stat().st_size for p in arc.rglob("*") if p.is_file())
        n = sum(1 for p in arc.rglob("*") if p.is_file())
        out.append(f"      {'archive 总占用':<36} {human(total)} / {n} 件")
        big = sorted((p for p in arc.rglob("*") if p.is_file() and p.stat().st_size > BIG_ARCHIVE),
                     key=lambda p: -p.stat().st_size)
        for p in big:
            out.append(f"   ⚠️ 大件（>{human(BIG_ARCHIVE)}，归档/删除前须先问用户）：{p.name}  {human(p.stat().st_size)}")

        # ── 同一产物快照份数检测（剥时间戳／版本号后归组）────────────────
        groups: dict = {}
        for p in arc.rglob("*"):
            if p.is_file():
                groups.setdefault(snapshot_key(p), []).append(p)
        over = sorted(((k, v) for k, v in groups.items() if len(v) > SNAPSHOT_KEEP),
                      key=lambda kv: -len(kv[1]))
        for k, ps in over:
            names = "、".join(sorted(p.name for p in ps)[:4])
            tail = f" 等 {len(ps)} 份" if len(ps) > 4 else f" 共 {len(ps)} 份"
            out.append(f"   ⚠️ 快照超限：{k}{tail} → 只留最近 {SNAPSHOT_KEEP} 份，"
                       f"其余走回收站（先出清单）：{names}")
        if not over and len(big) > 1:
            out.append(f"   ⚠️ 有 {len(big)} 份大件但按名没并成组，人工核一眼是否同产物快照"
                       f"（上限 {SNAPSHOT_KEEP} 份）")
    return out


def main() -> int:
    forced, rest = None, []
    it = iter(sys.argv[1:])
    for a in it:
        if a == "--type":
            forced = next(it, None)
        elif a.startswith("--type="):
            forced = a.split("=", 1)[1]
        else:
            rest.append(a)
    if forced not in (None, "text", "code"):
        print("--type 只接受 text 或 code")
        return 3

    root = Path(rest[0]).resolve() if rest else Path.cwd()
    if not root.is_dir():
        print(f"路径不存在：{root}")
        return 2
    ptype = forced or detect_project_type(root)

    print("=" * 70)
    print(f"工作空间体检（只读）  {root}")
    print("=" * 70)
    print("\n【A】目录体检")
    for line in dir_audit(root, ptype):
        print("  " + line)
    print("\n【B】体积体检")
    for line in size_audit(root):
        print("  " + line)
    print("\n提示：超标一律**先归位／先问**；删除类操作先出清单、走回收站，逐字核对文件名。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
