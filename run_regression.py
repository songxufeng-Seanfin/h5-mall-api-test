#!/usr/bin/env python3
"""一键回归：跑 35 条 pytest 用例 → 产出四类交付物。

用法：
    python run_regression.py                 # 直接跑（没有服务时 conftest 会临时拉起）
    python run_regression.py --reuse-server  # 看板调用，复用已经在跑的 8002 服务

产物：
    reports/allure-results/   Allure 原始结果（有 Java 可 allure serve）
    reports/junit.xml         JUnit XML（CI 通用格式）
    reports/results.json     结构化用例结果 + 请求响应证据
    reports/last_run.json     看板读取的最近一次运行摘要
    reports/report.html      免 Java 的 Allure 风格单页报告
    reports/defects.md       6 条规范化缺陷单
"""
import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent
REPORTS = BASE / "reports"
REPORTS.mkdir(exist_ok=True)


def main():
    ap = argparse.ArgumentParser(description="H5 商城接口一键回归")
    ap.add_argument("--reuse-server", action="store_true",
                    help="复用已启动的被测服务（由看板调用时传入）")
    args = ap.parse_args()

    # 每轮写独立批次目录：既不删除历史结果，也不会把多轮数据混在一起
    run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    allure_dir = f"reports/allure-results/{run_id}"
    (REPORTS / "allure-results" / run_id).mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env["NO_PROXY"] = env["no_proxy"] = "127.0.0.1,localhost"

    print("[1/4] 执行 pytest 35 条接口用例 …", flush=True)
    start = time.perf_counter()
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q",
         f"--alluredir={allure_dir}",
         "--junitxml=reports/junit.xml"],
        cwd=str(BASE), env=env,
    )
    wall = round(time.perf_counter() - start, 1)

    results_path = REPORTS / "results.json"
    if not results_path.exists():
        print("pytest 未产出 results.json，请检查 conftest.py 是否被加载", file=sys.stderr)
        return 2
    results = json.loads(results_path.read_text(encoding="utf-8"))

    flags_path = BASE / "runtime" / "bug_flags.json"
    flags = json.loads(flags_path.read_text(encoding="utf-8")) if flags_path.exists() else {}
    total = results["total"]
    passed = results["passed"]
    failed = results["failed"]

    print("[2/4] 汇总本轮结果 …", flush=True)
    last_run = {
        "run_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total": total, "passed": passed, "failed": failed, "skipped": 0,
        "duration": wall,
        "pass_rate": round(passed / total * 100, 1) if total else 0,
        "bugs_active": sum(bool(v) for v in flags.values()),
        "base_url": os.environ.get("MALL_BASE_URL", "http://127.0.0.1:8002"),
        "cases": results["cases"],
        "pytest_exit_code": proc.returncode,
        "junit": "reports/junit.xml",
        "allure": allure_dir,
    }
    (REPORTS / "last_run.json").write_text(
        json.dumps(last_run, ensure_ascii=False, indent=2), encoding="utf-8")

    print("[3/4] 生成单页报告与缺陷单 …", flush=True)
    for script in ("build_report.py", "defect_reports.py"):
        r = subprocess.run([sys.executable, str(REPORTS / script)], cwd=str(BASE), env=env)
        if r.returncode != 0:
            print(f"{script} 执行失败", file=sys.stderr)
            return 3

    print("[4/4] 完成", flush=True)
    print(f"    用例 {total} 条：通过 {passed} / 失败 {failed} / 耗时 {wall}s")
    print(f"    缺陷开关：开启 {last_run['bugs_active']}/6")
    print("    报告：reports/report.html　缺陷单：reports/defects.md")
    # pytest 有失败是「发现缺陷」，属于正常回归结果，脚本本身返回 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
