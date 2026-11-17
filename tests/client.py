"""接口客户端封装：把「发请求 / 记证据 / 管登录态」收在一处，用例里只写断言。

白话：requests 是「替手机发请求的人」，这个类给它加了两件事——
自动带 token，以及把每一次请求和响应都记下来，失败时挂到报告上当证据。
"""
import time
import requests


class ApiClient:
    def __init__(self, base_url):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        # 本机接口测试必须直连：环境里的 HTTP_PROXY 会把 127.0.0.1 的请求
        # 转到外部代理，拿回来的就不是被测服务响应了（第一轮踩过的坑）。
        self.session.trust_env = False
        self.token = None
        self.calls = []

    def request(self, method, path, *, json_body=None, params=None, with_token=True):
        url = self.base_url + path
        headers = {"X-Actor": "pytest"}
        if with_token and self.token:
            headers["X-Token"] = self.token
        start = time.perf_counter()
        resp = self.session.request(
            method, url, json=json_body, params=params,
            headers=headers, timeout=10,
        )
        duration = round((time.perf_counter() - start) * 1000, 1)
        try:
            body = resp.json()
        except ValueError:
            body = {"raw": resp.text[:400]}
        self.calls.append({
            "method": method, "url": url,
            "request": {"json": json_body, "params": params, "token": bool(with_token and self.token)},
            "response": {"status_code": resp.status_code, "body": body},
            "duration_ms": duration,
        })
        return resp, body

    def get(self, path, **kw):
        return self.request("GET", path, **kw)

    def post(self, path, json_body=None, **kw):
        return self.request("POST", path, json_body=json_body, **kw)

    def delete(self, path, **kw):
        return self.request("DELETE", path, **kw)

    def login(self, username="alice", password="123456"):
        resp, body = self.post("/api/auth/login/",
                               {"username": username, "password": password},
                               with_token=False)
        if resp.status_code == 200 and body.get("code") == 0:
            self.token = body["data"]["token"]
        return resp, body

    def product_by_name(self, name):
        """不硬编码商品 id —— 种子数据每次重置后主键会变，测试应该按名字找。"""
        resp, body = self.get("/api/products/", params={"page": 1, "size": 50})
        assert resp.status_code == 200, f"查询商品列表失败：{body}"
        for item in body["data"]["items"]:
            if item["name"] == name:
                return item
        raise AssertionError(f"种子商品不存在：{name}")

    def create_order(self, product_name, qty=1):
        product = self.product_by_name(product_name)
        return self.post("/api/orders/", {"product_id": product["id"], "qty": qty})
