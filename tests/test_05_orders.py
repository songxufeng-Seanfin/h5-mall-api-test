"""模块 05：订单（6 条）"""
import allure
import pytest

MODULE = "05 订单"
FEATURE = "订单"
SEVERITY = "P0"
pytestmark = [allure.epic("H5 商城接口回归"), allure.feature("订单")]


def test_order_create_success(logged_in):
    with allure.step("正常下单"):
        resp, body = logged_in.create_order("二手 iPad Air 5", 1)
    assert resp.status_code == 201
    order = body["data"]
    assert order["status"] == "created"
    assert order["total"] == order["unit_price"] * order["qty"]
    assert order["order_no"].startswith("ORD")


@pytest.mark.defect("DEF-005")
@allure.severity(allure.severity_level.CRITICAL)
def test_order_reject_when_stock_insufficient(logged_in):
    """库存只有 1 件时买 5 件必须 409（缺陷打开时会超卖）"""
    product = logged_in.product_by_name("考研数学真题")
    assert product["stock"] == 1, "种子数据异常：该商品库存应为 1"
    with allure.step("用超过库存的数量下单"):
        resp, body = logged_in.post("/api/orders/",
                                    {"product_id": product["id"], "qty": 5})
    assert resp.status_code == 409, f"库存不足仍然下单成功，发生超卖：{body}"
    assert body["code"] == 409
    after = logged_in.product_by_name("考研数学真题")
    assert after["stock"] == 1, "被拒绝的订单不应扣减库存"


def test_order_total_calculation(logged_in):
    product = logged_in.product_by_name("校园自行车")
    with allure.step("下单 2 件，校验金额 = 单价 × 数量"):
        resp, body = logged_in.post("/api/orders/",
                                    {"product_id": product["id"], "qty": 2})
    assert resp.status_code == 201
    assert body["data"]["total"] == product["price"] * 2
    assert body["data"]["unit_price"] == product["price"]


def test_order_detail(logged_in):
    _, created = logged_in.create_order("蓝牙耳机", 1)
    order_id = created["data"]["id"]
    with allure.step("按 id 查询订单详情"):
        resp, body = logged_in.get(f"/api/orders/{order_id}/")
    assert resp.status_code == 200
    assert body["data"]["order_no"] == created["data"]["order_no"]
    assert body["data"]["status"] == "created"


def test_order_cancel(logged_in):
    _, created = logged_in.create_order("保温杯", 1)
    order_id = created["data"]["id"]
    with allure.step("取消未支付订单"):
        resp, body = logged_in.post(f"/api/orders/{order_id}/cancel/", {})
    assert resp.status_code == 200
    assert body["data"]["status"] == "cancelled"


def test_order_create_unauthorized_401(api):
    with allure.step("未登录下单"):
        resp, body = api.post("/api/orders/", {"product_id": 1, "qty": 1}, with_token=False)
    assert resp.status_code == 401
    assert body["code"] == 401
