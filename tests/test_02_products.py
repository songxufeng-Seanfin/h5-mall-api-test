"""模块 02：商品列表与详情（6 条）"""
import allure
import pytest

MODULE = "02 商品列表与详情"
FEATURE = "商品"
SEVERITY = "P1"
pytestmark = [allure.epic("H5 商城接口回归"), allure.feature("商品")]


def test_product_list_shape(api):
    with allure.step("分页查询商品列表，校验字段与类型"):
        resp, body = api.get("/api/products/", params={"page": 1, "size": 3})
    assert resp.status_code == 200
    data = body["data"]
    assert len(data["items"]) <= 3
    assert data["page"] == 1 and data["size"] == 3
    assert isinstance(data["total"], int) and data["total"] > 0
    assert isinstance(data["has_more"], bool)
    for item in data["items"]:
        assert {"id", "name", "price", "stock", "category", "status"} <= set(item)
        assert isinstance(item["price"], int) and item["price"] > 0
        assert item["status"] == "on_sale"


def test_product_list_pagination(api):
    with allure.step("相邻两页不应出现重复商品"):
        r1, b1 = api.get("/api/products/", params={"page": 1, "size": 2})
        r2, b2 = api.get("/api/products/", params={"page": 2, "size": 2})
    assert r1.status_code == r2.status_code == 200
    ids1 = [i["id"] for i in b1["data"]["items"]]
    ids2 = [i["id"] for i in b2["data"]["items"]]
    assert len(ids1) == 2 and len(ids2) == 2
    assert not set(ids1) & set(ids2), "分页出现重复数据"


@pytest.mark.defect("DEF-002")
@allure.severity(allure.severity_level.NORMAL)
def test_product_list_page_out_of_range_empty(api):
    """页码越界应返回空列表而不是 500（缺陷打开时会 500）"""
    with allure.step("请求远超总页数的页码"):
        resp, body = api.get("/api/products/", params={"page": 999, "size": 2})
    assert resp.status_code == 200, f"页码越界导致服务端错误：{body}"
    assert body["code"] == 0
    assert body["data"]["items"] == []


def test_product_list_category_filter(api):
    with allure.step("按类目筛选"):
        resp, body = api.get("/api/products/", params={"page": 1, "size": 3, "category": "数码"})
    assert resp.status_code == 200
    items = body["data"]["items"]
    assert items, "数码类目不应为空"
    assert all(i["category"] == "数码" for i in items), "筛选结果混入其他类目"
    assert body["data"]["total"] >= len(items)


def test_product_detail(api):
    product = api.product_by_name("校园自行车")
    with allure.step("查询商品详情"):
        resp, body = api.get(f"/api/products/{product['id']}/")
    assert resp.status_code == 200
    assert body["data"]["id"] == product["id"]
    assert body["data"]["name"] == "校园自行车"
    assert body["data"]["price"] == product["price"]


def test_product_detail_not_found_404(api):
    with allure.step("查询不存在的商品"):
        resp, body = api.get("/api/products/999999/")
    assert resp.status_code == 404
    assert body["code"] == 404
    assert body["data"] is None
