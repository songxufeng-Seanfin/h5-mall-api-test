#!/usr/bin/env python3
"""把 pytest 结果渲染成一份 Allure 风格的自包含 HTML 报告。

为什么要自己出一份：官方 Allure 报告要靠 Java + allure 命令行生成，
本机没有 Java。allure-pytest 产出的 allure-results 仍然保留，
有 Java 的机器上 `allure serve reports/allure-results` 就能看官方版。
"""
import html
import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
REPORTS = BASE / "reports"
sys.path.insert(0, str(BASE))
from defect_catalog import DEFECTS  # noqa: E402


def esc(s):
    return html.escape(str(s if s is not None else ""), quote=True)


def load(name, default):
    p = REPORTS / name
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding="utf-8"))


PAGE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>H5 商城接口回归报告</title>
<style>
  :root { --bg:#f4f7fc; --surface:#fff; --ink:#16243c; --muted:#64748b; --line:#e2e9f3;
    --brand:#1677ff; --brand-soft:#eaf3ff; --green:#0f9d6e; --green-soft:#e6f7f0;
    --red:#d5443b; --red-soft:#fdeceb; --amber:#b26a00; --amber-soft:#fff4e0;
    --purple:#7048c8; --purple-soft:#f1ecff; }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--bg); color:var(--ink); font:14px/1.7 -apple-system,
    BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif; }
  .page { max-width:1100px; margin:0 auto; padding:24px 18px 60px; }
  .hero { background:linear-gradient(115deg,#1677ff,#4d9bff 58%,#75b6ff); color:#fff;
    border-radius:16px; padding:26px 30px; margin-bottom:18px; }
  .hero .eyebrow { font-size:11.5px; letter-spacing:1.4px; background:rgba(255,255,255,.18);
    padding:3px 11px; border-radius:99px; }
  .hero h1 { font-size:25px; margin:12px 0 6px; font-weight:600; }
  .hero p { margin:0; font-size:13px; opacity:.92; }
  section { margin-bottom:20px; }
  h2 { font-size:16px; margin:0 0 12px; }
  h2 .sub { font-size:12px; color:var(--muted); font-weight:400; margin-left:8px; }
  .card { background:var(--surface); border:1px solid var(--line); border-radius:12px; padding:18px 20px; }
  .stats { display:grid; grid-template-columns:repeat(6,1fr); gap:12px; }
  .stat { background:var(--surface); border:1px solid var(--line); border-radius:12px; padding:13px 15px; }
  .stat .n { font-size:23px; font-weight:600; font-variant-numeric:tabular-nums; }
  .stat .l { font-size:12px; color:var(--muted); }
  .stat.ok .n { color:var(--green); } .stat.bad .n { color:var(--red); }
  .stat.hl .n { color:var(--brand); } .stat.warn .n { color:var(--amber); }
  .bar { height:10px; border-radius:99px; overflow:hidden; background:#e8eef8; display:flex; margin:14px 0 4px; }
  .bar i.ok { background:var(--green); } .bar i.bad { background:var(--red); }
  .legend { font-size:12px; color:var(--muted); }
  table { width:100%; border-collapse:collapse; font-size:12.8px; }
  th,td { padding:9px 10px; text-align:left; border-bottom:1px solid var(--line); vertical-align:top; }
  th { color:var(--muted); font-size:12px; font-weight:500; background:#fafcff; white-space:nowrap; }
  .pill { display:inline-block; font-size:11.5px; padding:1px 9px; border-radius:99px; white-space:nowrap; }
  .pill.ok { background:var(--green-soft); color:var(--green); }
  .pill.bad { background:var(--red-soft); color:var(--red); }
  .pill.warn { background:var(--amber-soft); color:var(--amber); }
  .pill.dup { background:var(--purple-soft); color:var(--purple); }
  .pill.muted { background:#f0f3f8; color:var(--muted); }
  .group { font-size:12.5px; color:var(--muted); padding:14px 10px 6px; font-weight:600; }
  tr.fail td { background:rgba(213,68,59,.045); }
  .mono { font-family:"SFMono-Regular",Consolas,Menlo,monospace; font-size:11.6px; }
  .nodeid { color:var(--muted); font-size:11px; }
  details { margin-top:6px; }
  summary { cursor:pointer; color:var(--brand); font-size:12px; }
  pre { background:#f6f9fd; border:1px solid var(--line); border-radius:8px; padding:11px;
    overflow-x:auto; font-size:11.5px; line-height:1.55; white-space:pre-wrap; word-break:break-all; }
  .defects { display:grid; grid-template-columns:repeat(2,1fr); gap:14px; }
  .defect { background:var(--surface); border:1px solid var(--line); border-radius:12px; padding:15px 17px; }
  .defect.found { border-color:#f3c7c4; }
  .defect h3 { font-size:13.6px; margin:8px 0; }
  .defect dl { margin:0; font-size:12.2px; }
  .defect dt { color:var(--muted); font-size:11.5px; margin-top:7px; }
  .defect dd { margin:2px 0 0; overflow-wrap:anywhere; }
  .defect ol { padding-left:18px; margin:2px 0 0; }
  .foot { text-align:center; color:var(--muted); font-size:12px; margin-top:26px; }
  a { color:var(--brand); }
  @media (max-width:860px) { .stats{grid-template-columns:repeat(3,1fr)} .defects{grid-template-columns:1fr}
    .card{padding:14px} .hero{padding:20px 18px} }
  @media (prefers-color-scheme:dark) {
    :root { --bg:#121821; --surface:#1a2330; --ink:#e6edf7; --muted:#98a8bd; --line:#2b3746;
      --brand:#6aa8ff; --brand-soft:#1e314c; --green:#64d6ab; --green-soft:#1a3a30;
      --red:#f1948c; --red-soft:#3a2323; --amber:#e9b567; --amber-soft:#3a2e18;
      --purple:#b9a2f0; --purple-soft:#2c2440; }
    th,pre { background:#243040; }
    .pill.muted { background:#243040; color:#9aabc0; }
    .bar { background:#243040; }
    tr.fail td { background:rgba(241,148,140,.06); }
  }
</style>
</head>
<body>
<div class="page">
  <div class="hero">
    <span class="eyebrow">API REGRESSION REPORT</span>
    <h1>H5 商城接口回归报告</h1>
    <p>运行时间 {{RUN_AT}}　·　pytest + requests + Allure　·　被测服务 {{BASE_URL}}</p>
  </div>

  <section>
    <h2>执行概览 <span class="sub">{{SUMMARY}}</span></h2>
    <div class="stats">
      <div class="stat hl"><div class="n">{{TOTAL}}</div><div class="l">用例总数</div></div>
      <div class="stat ok"><div class="n">{{PASSED}}</div><div class="l">通过</div></div>
      <div class="stat bad"><div class="n">{{FAILED}}</div><div class="l">失败</div></div>
      <div class="stat hl"><div class="n">{{RATE}}%</div><div class="l">通过率</div></div>
      <div class="stat warn"><div class="n">{{DEFECTS}}</div><div class="l">关联缺陷单</div></div>
      <div class="stat"><div class="n">{{DURATION}}s</div><div class="l">执行耗时</div></div>
    </div>
    <div class="card" style="margin-top:14px">
      <div class="bar"><i class="ok" style="width:{{OK_W}}%"></i><i class="bad" style="width:{{BAD_W}}%"></i></div>
      <div class="legend">绿色 = 通过 {{PASSED}} 条　·　红色 = 失败 {{FAILED}} 条　·　缺陷开关开启 {{BUGS}}/6</div>
    </div>
  </section>

  <section class="card">
    <h2>用例明细 <span class="sub">失败用例可展开断言信息与实际响应证据</span></h2>
    <table>
      <thead><tr><th>状态</th><th>用例</th><th>接口</th><th>耗时</th><th>缺陷单</th></tr></thead>
      <tbody>{{CASES}}</tbody>
    </table>
  </section>

  <section>
    <h2>缺陷单 <span class="sub">6 条规范化记录 · 本轮抓到 {{FOUND}} 条</span></h2>
    <div class="defects">{{DEFECT_CARDS}}</div>
  </section>

  <div class="foot">
    pytest 原始产物：<span class="mono">reports/junit.xml</span>　·　
    Allure 原始结果：<span class="mono">{{ALLURE}}</span>（有 Java 时可执行 allure serve）　·　
    缺陷单 Markdown：<span class="mono">reports/defects.md</span>
  </div>
</div>
</body>
</html>
"""


def render():
    data = load("results.json", {"cases": [], "total": 0, "passed": 0, "failed": 0})
    last = load("last_run.json", {})
    cases = data.get("cases", [])
    total = data.get("total", len(cases)) or 1
    passed = data.get("passed", 0)
    failed = data.get("failed", 0)

    groups = {}
    for c in cases:
        groups.setdefault(c.get("module", "其他"), []).append(c)

    rows = []
    for module, items in groups.items():
        rows.append(f'<tr><td colspan="5" class="group">{esc(module)}（{len(items)} 条）</td></tr>')
        for c in items:
            is_fail = c.get("status") == "failed"
            pill = '<span class="pill bad">失败</span>' if is_fail else '<span class="pill ok">通过</span>'
            defect = (f'<span class="pill dup">{esc(c["defect"])}</span>'
                      if c.get("defect") else '<span class="pill muted">—</span>')
            extra = ""
            if is_fail:
                evidence = json.dumps(c.get("evidence", []), ensure_ascii=False, indent=2)
                extra = ("<details><summary>展开断言失败信息与请求响应证据</summary>"
                         f"<pre>{esc(c.get('message', ''))}</pre><pre>{esc(evidence)}</pre></details>")
            rows.append(
                f'<tr class="{"fail" if is_fail else ""}">'
                f'<td>{pill}</td>'
                f'<td><b>{esc(c.get("name"))}</b>{extra}<div class="nodeid">{esc(c.get("nodeid"))}</div></td>'
                f'<td class="mono">{esc(c.get("endpoint"))}</td>'
                f'<td class="mono">{round(float(c.get("duration", 0)) * 1000)}ms</td>'
                f'<td>{defect}</td></tr>'
            )

    found_ids = {c.get("defect") for c in cases if c.get("status") == "failed"}
    cards = []
    for d in DEFECTS:
        found = d["id"] in found_ids
        badge = ('<span class="pill bad">本轮抓到</span>' if found
                 else '<span class="pill ok">本轮通过</span>')
        cards.append(
            f'<div class="defect {"found" if found else ""}">'
            f'<span class="pill dup">{esc(d["id"])}</span> '
            f'<span class="pill warn">{esc(d["severity"])}</span> {badge}'
            f'<h3>{esc(d["title"])}</h3>'
            f'<div class="mono" style="color:var(--muted)">{esc(d["endpoint"])}</div>'
            f'<dl><dt>复现步骤</dt><dd><ol>{"".join(f"<li>{esc(s)}</li>" for s in d["steps"])}</ol></dd>'
            f'<dt>预期结果</dt><dd>{esc(d["expected"])}</dd>'
            f'<dt>实际结果</dt><dd>{esc(d["actual"])}</dd>'
            f'<dt>根因推测</dt><dd>{esc(d["root_cause"])}</dd>'
            f'<dt>修复建议</dt><dd>{esc(d["fix"])}</dd>'
            f'<dt>关联用例</dt><dd class="mono">{esc(d["case"])}</dd></dl></div>'
        )

    mapping = {
        "{{RUN_AT}}": esc(last.get("run_at", "—")),
        "{{BASE_URL}}": esc(last.get("base_url", "本地内置商城")),
        "{{SUMMARY}}": esc(f"{total} 条用例 / {passed} 通过 / {failed} 失败"),
        "{{TOTAL}}": str(total), "{{PASSED}}": str(passed), "{{FAILED}}": str(failed),
        "{{RATE}}": str(round(passed / total * 100, 1)),
        "{{DEFECTS}}": str(len(DEFECTS)), "{{FOUND}}": str(len(found_ids)),
        "{{DURATION}}": str(last.get("duration", data.get("duration", 0))),
        "{{OK_W}}": str(round(passed / total * 100, 1)),
        "{{BAD_W}}": str(round(failed / total * 100, 1)),
        "{{BUGS}}": str(last.get("bugs_active", 0)),
        "{{ALLURE}}": esc(last.get("allure", "reports/allure-results/")),
        "{{CASES}}": "\n".join(rows),
        "{{DEFECT_CARDS}}": "\n".join(cards),
    }
    out = PAGE
    for key, value in mapping.items():
        out = out.replace(key, value)
    (REPORTS / "report.html").write_text(out, encoding="utf-8")
    return REPORTS / "report.html"


if __name__ == "__main__":
    print("报告已生成：", render())
