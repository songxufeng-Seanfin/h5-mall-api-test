#!/usr/bin/env python3
"""把结构化缺陷数据渲染成 6 条规范化缺陷单（Markdown）。"""
import json
import sys
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
REPORTS = BASE / "reports"
sys.path.insert(0, str(BASE))
from defect_catalog import DEFECTS  # noqa: E402


def render():
    last = {}
    p = REPORTS / "last_run.json"
    if p.exists():
        last = json.loads(p.read_text(encoding="utf-8"))
    found_ids = {c.get("defect") for c in last.get("cases", []) if c.get("status") == "failed"}
    flags = {}
    f = BASE / "runtime" / "bug_flags.json"
    if f.exists():
        flags = json.loads(f.read_text(encoding="utf-8"))

    lines = [
        "# H5 商城接口回归 · 缺陷单汇总",
        "",
        f"> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}　|　"
        f"本轮：{last.get('total', 0)} 条用例 / {last.get('passed', 0)} 通过 / {last.get('failed', 0)} 失败　|　"
        f"缺陷开关开启 {sum(flags.values())}/6",
        "",
        "## 一、汇总表",
        "",
        "| 编号 | 标题 | 等级 | 模块 | 接口 | 关联用例 | 本轮结果 |",
        "|---|---|---|---|---|---|---|",
    ]
    for d in DEFECTS:
        state = "🔴 本轮抓到" if d["id"] in found_ids else "🟢 本轮通过（缺陷已修复）"
        lines.append(
            f"| {d['id']} | {d['title']} | {d['severity']} | {d['module']} | "
            f"`{d['endpoint']}` | `{d['case']}` | {state} |"
        )
    lines += ["", "## 二、逐条详情", ""]
    for d in DEFECTS:
        state = "待修复 / 本轮复现" if d["id"] in found_ids else "本轮回归通过（开关已关闭）"
        lines += [
            f"### {d['id']}　{d['title']}",
            "",
            f"- **严重级别**：{d['severity']}　|　**所属模块**：{d['module']}　|　**状态**：{state}",
            f"- **接口**：`{d['endpoint']}`",
            f"- **关联用例**：`{d['case']}`",
            f"- **前置条件**：{d['precondition']}",
            "- **复现步骤**：",
        ]
        lines += [f"  {s}" for s in d["steps"]]
        lines += [
            f"- **预期结果**：{d['expected']}",
            f"- **实际结果**：{d['actual']}",
            f"- **证据**：{d['evidence']}",
            f"- **根因推测**：{d['root_cause']}",
            f"- **修复建议**：{d['fix']}",
            "",
        ]
    lines += [
        "## 三、如何验证修复",
        "",
        "看板上点「模拟开发修完全部缺陷」，或直接执行：",
        "",
        "```bash",
        "curl -X POST http://127.0.0.1:8002/api/toggle/ -H \"Content-Type: application/json\" -d '{\"all\": false}'",
        "python run_regression.py",
        "```",
        "",
        "同一套 35 条用例不做任何修改，应从 29 通过 / 6 失败变成 35 通过 / 0 失败，",
        "这就是回归测试的价值：用不变的清单反复验证修改没有引入新问题。",
        "",
    ]
    out = REPORTS / "defects.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


if __name__ == "__main__":
    print("缺陷单已生成：", render())
