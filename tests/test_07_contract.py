"""模块 07：统一契约与性能基线（2 条）"""
import allure
import pytest

MODULE = "07 契约与性能"
FEATURE = "契约"
SEVERITY = "P2"
pytestmark = [allure.epic("H5 商城接口回归"), allure.feature("契约")]


@pytest.mark.contract
def test_unified_response_contract(api):
    """成功与失败响应都必须是 {code, message, data}，且 code 与 HTTP 状态自洽"""
    checks = [
        ("健康检查", api.get("/api/health/")),
        ("商品列表", api.get("/api/products/", params={"page": 1, "size": 2})),
        ("搜索缺参数", api.get("/api/products/search/")),
        ("未登录访问", api.get("/api/auth/profile/", with_token=False)),
    ]
    for label, (resp, body) in checks:
        with allure.step(f"校验 {label} 的响应契约"):
            assert {"code", "message", "data"} <= set(body), f"{label} 响应缺少契约字段：{body}"
            assert isinstance(body["message"], str)
            if resp.status_code >= 400:
                assert body["code"] == resp.status_code, f"{label} 的 code 与 HTTP 状态不一致"
                assert body["data"] is None
            else:
                assert body["code"] == 0


@pytest.mark.contract
def test_api_latency_sla(api):
    """基线：本地商品列表接口连续 5 次都应低于 1.5 秒"""
    durations = []
    for i in range(5):
        with allure.step(f"第 {i + 1} 次请求商品列表"):
            resp, _ = api.get("/api/products/", params={"page": 1, "size": 3})
        assert resp.status_code == 200
        durations.append(api.calls[-1]["duration_ms"])
    allure.attach(" / ".join(f"{d}ms" for d in durations), name="耗时明细",
                  attachment_type=allure.attachment_type.TEXT)
    assert max(durations) < 1500, f"接口耗时超出基线：{durations}"
