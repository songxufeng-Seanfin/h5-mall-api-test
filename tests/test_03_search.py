"""模块 03：商品搜索（5 条）"""
import allure
import pytest

MODULE = "03 商品搜索"
FEATURE = "搜索"
SEVERITY = "P1"
pytestmark = [allure.epic("H5 商城接口回归"), allure.feature("搜索")]


def test_search_keyword_hit(api):
    with allure.step("关键词命中"):
        resp, body = api.get("/api/products/search/", params={"kw": "校园"})
    assert resp.status_code == 200
    items = body["data"]["items"]
    assert items, "关键词应有命中"
    assert all("校园" in i["name"] for i in items)
    assert body["data"]["total"] == len(items)


def test_search_case_insensitive(api):
    with allure.step("英文关键词大小写不敏感"):
        resp, body = api.get("/api/products/search/", params={"kw": "IPAD"})
    assert resp.status_code == 200
    names = [i["name"].lower() for i in body["data"]["items"]]
    assert any("ipad" in n for n in names), "大小写敏感，英文关键词漏召回"


def test_search_no_result_empty(api):
    with allure.step("无结果时返回空数组而非报错"):
        resp, body = api.get("/api/products/search/", params={"kw": "不存在的商品xyz123"})
    assert resp.status_code == 200
    assert body["data"]["items"] == []
    assert body["data"]["total"] == 0


@pytest.mark.defect("DEF-003")
@allure.severity(allure.severity_level.NORMAL)
def test_search_excludes_off_shelf(api):
    """已下架商品不能出现在搜索结果里（缺陷打开时会混入）"""
    with allure.step("搜索「校园」，检查每一条的状态"):
        resp, body = api.get("/api/products/search/", params={"kw": "校园"})
    assert resp.status_code == 200
    items = body["data"]["items"]
    assert items
    off = [i["name"] for i in items if i["status"] != "on_sale"]
    assert not off, f"搜索结果混入已下架商品：{off}"


def test_search_special_chars_no_500(api):
    with allure.step("传入 SQL 注入样式字符串，不应 500 也不应拖库"):
        resp, body = api.get("/api/products/search/", params={"kw": "' OR 1=1 --"})
    assert resp.status_code == 200
    assert body["code"] == 0
    assert body["data"]["total"] == 0
