"""6 个「可开关的预置缺陷」。

白话：这是一个面板开关。开关打开时，被测商城故意犯错，回归用例就会抓到 6 个问题；
开关全部关掉（相当于开发修完了 bug），同一套 35 条用例应该全绿。
这样「发现缺陷 → 修复 → 回归验证」的闭环在一个仓库里就能演示，不用真的去改坏代码。

开关状态写在 runtime/bug_flags.json，Django 每次请求都重新读，所以改了立刻生效。
"""
import json
import threading
from django.conf import settings

_LOCK = threading.Lock()

# key -> 中文说明
BUG_CATALOG = {
    "AUTH_BYPASS_WRONG_PASSWORD": "登录：密码错误仍签发 token",
    "PAGE_OUT_OF_RANGE_500": "商品列表：页码越界返回 500",
    "SEARCH_INCLUDE_OFF_SHELF": "搜索：把已下架商品也搜出来",
    "CART_DUPLICATE_ROW": "购物车：重复添加生成重复行而非累加数量",
    "ORDER_IGNORE_STOCK": "下单：不校验库存，造成超卖",
    "PAY_NOT_IDEMPOTENT": "支付：重复支付不拦截，重复扣款",
}


def _path():
    return settings.RUNTIME_DIR / "bug_flags.json"


def all_flags():
    with _LOCK:
        p = _path()
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return {k: bool(data.get(k, True)) for k in BUG_CATALOG}
            except (OSError, ValueError):
                pass
        data = {k: True for k in BUG_CATALOG}
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return dict(data)


def is_on(key):
    return all_flags().get(key, False)


def set_flag(key, value):
    if key not in BUG_CATALOG:
        return None
    data = all_flags()
    data[key] = bool(value)
    with _LOCK:
        _path().write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data


def set_all(value):
    data = {k: bool(value) for k in BUG_CATALOG}
    with _LOCK:
        _path().write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data
