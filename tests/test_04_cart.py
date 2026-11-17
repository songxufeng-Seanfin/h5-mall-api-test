"""模块 04：购物车（6 条）"""
import allure
import pytest

MODULE = "04 购物车"
FEATURE = "购物车"
SEVERITY = "P1"
pytestmark = [allure.epic("H5 商城接口回归"), allure.feature("购物车")]


def _ipad(logged_in):
    return logged_in.product_by_name("二手 iPad Air 5")["id"]


def test_cart_add_item(logged_in):
    with allure.step("加入一件商品"):
        resp, body = logged_in.post("/api/cart/items/",
                                    {"product_id": _ipad(logged_in), "qty": 1})
    assert resp.status_code == 201
    assert body["data"]["cart"]["total_qty"] == 1


@pytest.mark.defect("DEF-004")
@allure.severity(allure.severity_level.NORMAL)
def test_cart_add_same_item_accumulates(logged_in):
    """重复添加同一商品应累加数量而不是生成重复行（缺陷打开时会重复）"""
    pid = _ipad(logged_in)
    with allure.step("连续两次添加同一商品"):
        r1, _ = logged_in.post("/api/cart/items/", {"product_id": pid, "qty": 1})
        r2, b2 = logged_in.post("/api/cart/items/", {"product_id": pid, "qty": 1})
    assert r1.status_code == r2.status_code == 201
    items = b2["data"]["cart"]["items"]
    assert len(items) == 1, f"购物车出现 {len(items)} 行相同商品，未做幂等累加"
    assert items[0]["qty"] == 2
    assert b2["data"]["cart"]["total_qty"] == 2


def test_cart_list_total(logged_in):
    p1 = logged_in.product_by_name("二手 iPad Air 5")
    p2 = logged_in.product_by_name("校园自行车")
    logged_in.post("/api/cart/items/", {"product_id": p1["id"], "qty": 2})
    logged_in.post("/api/cart/items/", {"product_id": p2["id"], "qty": 3})
    with allure.step("校验购物车数量与金额合计"):
        resp, body = logged_in.get("/api/cart/")
    cart = body["data"]
    assert resp.status_code == 200
    assert cart["total_qty"] == 5
    assert cart["total_amount"] == p1["price"] * 2 + p2["price"] * 3


def test_cart_remove_item(logged_in):
    _, body = logged_in.post("/api/cart/items/", {"product_id": _ipad(logged_in), "qty": 1})
    item_id = body["data"]["item"]["id"]
    with allure.step("删除购物车条目"):
        resp, body = logged_in.delete(f"/api/cart/items/{item_id}/")
    assert resp.status_code == 200
    assert body["data"]["total_qty"] == 0


def test_cart_add_unauthorized_401(api):
    with allure.step("未登录添加购物车"):
        resp, body = api.post("/api/cart/items/", {"product_id": 1, "qty": 1}, with_token=False)
    assert resp.status_code == 401
    assert body["code"] == 401


def test_cart_invalid_qty_400(logged_in):
    with allure.step("数量传 0，应被参数校验拦下"):
        resp, body = logged_in.post("/api/cart/items/",
                                     {"product_id": _ipad(logged_in), "qty": 0})
    assert resp.status_code == 400
    assert body["code"] == 400
