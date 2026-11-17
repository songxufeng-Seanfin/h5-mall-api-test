"""模块 06：支付与越权（4 条）"""
import allure
import pytest

MODULE = "06 支付与越权"
FEATURE = "支付"
SEVERITY = "P0"
pytestmark = [allure.epic("H5 商城接口回归"), allure.feature("支付")]


def test_pay_success(logged_in):
    _, created = logged_in.create_order("机械键盘", 1)
    order_id = created["data"]["id"]
    with allure.step("支付一笔未支付订单"):
        resp, body = logged_in.post(f"/api/orders/{order_id}/pay/", {})
    assert resp.status_code == 200
    assert body["data"]["status"] == "paid"
    assert body["data"]["paid_count"] == 1


@pytest.mark.defect("DEF-006")
@allure.severity(allure.severity_level.CRITICAL)
def test_pay_duplicate_rejected(logged_in):
    """同一订单重复支付必须被幂等拦截（缺陷打开时会重复扣款）"""
    _, created = logged_in.create_order("蓝牙耳机", 1)
    order_id = created["data"]["id"]
    with allure.step("第一次支付"):
        r1, _ = logged_in.post(f"/api/orders/{order_id}/pay/", {})
    with allure.step("第二次支付（重复请求）"):
        r2, b2 = logged_in.post(f"/api/orders/{order_id}/pay/", {})
    assert r1.status_code == 200
    assert r2.status_code == 409, f"重复支付未被拦截，存在重复扣款：{b2}"
    _, detail = logged_in.get(f"/api/orders/{order_id}/")
    assert detail["data"]["paid_count"] == 1, "重复支付导致 paid_count > 1"


def test_pay_status_after_success(logged_in):
    _, created = logged_in.create_order("显示器支架", 1)
    order_id = created["data"]["id"]
    logged_in.post(f"/api/orders/{order_id}/pay/", {})
    with allure.step("支付后订单状态应为 paid"):
        resp, body = logged_in.get(f"/api/orders/{order_id}/")
    assert resp.status_code == 200
    assert body["data"]["status"] == "paid"


def test_order_of_other_user_403(logged_in, bob_client):
    _, created = logged_in.create_order("校园自行车", 1)
    order_id = created["data"]["id"]
    with allure.step("用 bob 的 token 查看 alice 的订单"):
        resp, body = bob_client.get(f"/api/orders/{order_id}/")
    assert resp.status_code == 403
    assert body["code"] == 403
