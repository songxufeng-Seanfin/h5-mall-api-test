"""pytest 的公共装配层：起服务、清数据、管登录态、收证据、写结果文件。

白话解释三个词：
- fixture（夹具）：每个用例开跑前自动准备好的东西，比如「一个已登录的客户端」。
- hook（钩子）：pytest 在关键时刻留的插口，这里用它把失败证据挂到报告上。
- session（会话）：一整轮测试只做一次的事，比如启动被测服务。
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import allure
import pytest
import requests

BASE = Path(__file__).resolve().parents[1]
REPORTS = BASE / "reports"
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from tests.client import ApiClient  # noqa: E402

_RESULTS = []
_LOCAL = requests.Session()
_LOCAL.trust_env = False  # 同 client.py：绕开全局 HTTP_PROXY，直连本机被测服务
os.environ["NO_PROXY"] = "127.0.0.1,localhost"
os.environ["no_proxy"] = "127.0.0.1,localhost"


def _alive(url):
    try:
        return _LOCAL.get(url + "/api/health/", timeout=1.5).status_code == 200
    except requests.RequestException:
        return False


@pytest.fixture(scope="session")
def server():
    """优先复用已经在跑的看板服务；否则临时拉起一个，跑完关掉。"""
    url = os.environ.get("MALL_BASE_URL", "http://127.0.0.1:8002").rstrip("/")
    if _alive(url):
        yield url
        return
    port = int(os.environ.get("MALL_TEST_PORT", "8012"))
    alt = f"http://127.0.0.1:{port}"
    if _alive(alt):
        yield alt
        return
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env["NO_PROXY"] = env["no_proxy"] = "127.0.0.1,localhost"
    proc = subprocess.Popen(
        [sys.executable, str(BASE / "manage.py"), "runserver",
         f"127.0.0.1:{port}", "--noreload"],
        cwd=str(BASE), env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    for _ in range(80):
        if _alive(alt):
            break
        time.sleep(0.25)
    else:
        proc.terminate()
        pytest.fail("被测商城服务未能启动，请先执行 python manage.py runserver")
    os.environ["MALL_BASE_URL"] = alt
    try:
        yield alt
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=8)
        except subprocess.TimeoutExpired:
            proc.kill()


@pytest.fixture(autouse=True)
def fresh_state(server):
    """每条用例前重置种子数据 —— 用例之间不许互相污染。"""
    resp = _LOCAL.post(server + "/api/admin/reset/", timeout=10)
    assert resp.status_code == 200, f"重置种子数据失败：{resp.status_code}"
    yield


@pytest.fixture
def api(server):
    return ApiClient(server)


@pytest.fixture
def logged_in(api):
    resp, body = api.login("alice", "123456")
    assert resp.status_code == 200 and body["code"] == 0, f"登录失败：{body}"
    assert body["data"]["token"], "登录未返回 token"
    return api


@pytest.fixture
def bob_client(server):
    client = ApiClient(server)
    resp, body = client.login("bob", "123456")
    assert resp.status_code == 200 and body["code"] == 0
    return client


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """用例跑完后：收集结构化结果 + 把请求/响应 JSON 挂成 Allure 附件。"""
    outcome = yield
    rep = outcome.get_result()
    if rep.when != "call":
        return

    marker = item.get_closest_marker("defect")
    defect = marker.args[0] if marker and marker.args else None
    mod = item.module
    client = item.funcargs.get("logged_in") or item.funcargs.get("bob_client") or item.funcargs.get("api")
    calls = client.calls[-10:] if client else []

    try:
        allure.attach(
            json.dumps(calls, ensure_ascii=False, indent=2),
            name="请求与响应证据",
            attachment_type=allure.attachment_type.JSON,
        )
    except Exception:
        pass  # 附件失败不能影响用例结论

    _RESULTS.append({
        "name": item.name,
        "nodeid": item.nodeid,
        "module": getattr(mod, "MODULE", "其他"),
        "feature": getattr(mod, "FEATURE", "通用"),
        "severity": getattr(mod, "SEVERITY", "P2"),
        "status": "passed" if rep.passed else "failed",
        "duration": round(float(getattr(rep, "duration", 0)), 3),
        "defect": defect,
        "endpoint": _last_endpoint(calls),
        "message": (str(rep.longrepr)[:1800] if rep.failed else ""),
        "evidence": calls[-2:],
    })


def _last_endpoint(calls):
    if not calls:
        return ""
    return f"{calls[-1]['method']} {calls[-1]['url'].split('/api/')[-1].split('?')[0]}"


def pytest_sessionfinish(session, exitstatus):
    REPORTS.mkdir(exist_ok=True)
    passed = sum(1 for c in _RESULTS if c["status"] == "passed")
    failed = sum(1 for c in _RESULTS if c["status"] == "failed")
    payload = {
        "total": len(_RESULTS),
        "passed": passed,
        "failed": failed,
        "duration": round(sum(c["duration"] for c in _RESULTS), 3),
        "cases": _RESULTS,
    }
    (REPORTS / "results.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
