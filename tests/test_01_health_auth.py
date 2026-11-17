"""模块 01：健康检查与认证（6 条）"""
import allure
import pytest

MODULE = "01 健康检查与认证"
FEATURE = "认证"
SEVERITY = "P1"
pytestmark = [allure.epic("H5 商城接口回归"), allure.feature("认证")]


def test_health_ok(api):
    """冒烟：服务活着，且遵守统一响应契约"""
    with allure.step("GET /api/health/"):
        resp, body = api.get("/api/health/")
    assert resp.status_code == 200
    assert body["code"] == 0
    assert body["data"]["status"] == "healthy"


@allure.severity(allure.severity_level.CRITICAL)
def test_login_success_returns_token(api):
    with allure.step("正确账号密码登录"):
        resp, body = api.login("alice", "123456")
    assert resp.status_code == 200
    assert body["code"] == 0
    assert body["data"]["username"] == "alice"
    assert len(body["data"]["token"]) >= 16, "token 长度异常"


@pytest.mark.defect("DEF-001")
@allure.severity(allure.severity_level.CRITICAL)
def test_login_wrong_password_rejected(api):
    """错误密码必须 401，且不签发任何 token（缺陷打开时会被放行）"""
    with allure.step("用错误密码登录，应被拒绝"):
        resp, body = api.post("/api/auth/login/",
                              {"username": "alice", "password": "wrong-pwd"})
    assert resp.status_code == 401, f"错误密码被放行，存在认证绕过：{body}"
    assert body.get("data") is None, "认证失败时不应返回数据体"
    assert body.get("code") == 401


def test_login_missing_field_400(api):
    with allure.step("缺少必填字段"):
        resp, body = api.post("/api/auth/login/", {})
    assert resp.status_code == 400
    assert body["code"] == 400
    assert body["data"] is None


def test_profile_with_token(logged_in):
    with allure.step("带 token 访问个人信息"):
        resp, body = logged_in.get("/api/auth/profile/")
    assert resp.status_code == 200
    assert body["data"]["username"] == "alice"
    assert body["data"]["nickname"] == "阿梨"


def test_profile_without_token_401(api):
    with allure.step("不带 token 访问受保护接口"):
        resp, body = api.get("/api/auth/profile/", with_token=False)
    assert resp.status_code == 401
    assert body["code"] == 401
