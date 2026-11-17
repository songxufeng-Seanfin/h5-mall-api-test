"""接口路由的两类视图：被测商城 API + 回归看板。"""
import json
import os
import subprocess
import sys
import threading
from pathlib import Path

from django.conf import settings
from django.db.models import F
from django.http import FileResponse, HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from defect_catalog import DEFECTS
from . import bugflags, service
from .models import ApiCallLog, CartItem, MallOrder, MallUser, Product

_BASE = settings.BASE_DIR
_RUN_STATUS = settings.RUNTIME_DIR / "run_status.json"
_RUN_LOCK = threading.Lock()

ok, err = service.ok, service.err


# ==================== 被测商城 API ====================
def api_health(request):
    return ok({"status": "healthy", "service": "h5-mall-sut", "version": "1.0"})


@require_http_methods(["POST"])
def api_reset(request):
    return ok(service.reset_demo(), "商城已重置为种子数据")


@require_http_methods(["POST"])
def api_login(request):
    body = service.parse_body(request)
    username, password = body.get("username"), body.get("password")
    if not username or not password:
        return err(400, "username 与 password 均不能为空")
    user, error = service.login(username, password)
    if error:
        return error
    return ok({"token": user.token, "username": user.username, "nickname": user.nickname}, "登录成功")


@require_http_methods(["POST"])
def api_logout(request):
    user = service.auth_user(request)
    if not user:
        return err(401, "缺少有效 token")
    user.token = ""
    user.save(update_fields=["token"])
    return ok(message="已退出登录")


def api_profile(request):
    user = service.auth_user(request)
    if not user:
        return err(401, "缺少有效 token")
    return ok({"username": user.username, "nickname": user.nickname})


def api_products(request):
    """商品列表：分页 + 类目筛选，故意留一个越界 500 的缺陷位。"""
    try:
        page = int(request.GET.get("page", 1))
        size = int(request.GET.get("size", 3))
    except ValueError:
        return err(400, "page / size 必须是整数")
    if page < 1 or size < 1 or size > 50:
        return err(400, "page / size 超出合法范围")

    qs = service.visible_products().order_by("id")
    category = request.GET.get("category")
    if category:
        qs = qs.filter(category=category)
    total = qs.count()
    start = (page - 1) * size

    # DEF-002：页码越界没有兜底，直接抛 500
    if bugflags.is_on("PAGE_OUT_OF_RANGE_500") and start >= total and total > 0:
        return err(500, "内部错误：list index out of range")

    rows = list(qs[start:start + size])
    return ok({
        "items": [service.product_dict(p) for p in rows],
        "total": total, "page": page, "size": size,
        "has_more": start + size < total,
    })


def api_search(request):
    kw = request.GET.get("kw", "").strip()
    if not kw:
        return err(400, "kw 不能为空")
    qs = Product.objects.filter(name__icontains=kw)
    # DEF-003：忘了过滤下架商品
    if not bugflags.is_on("SEARCH_INCLUDE_OFF_SHELF"):
        qs = qs.filter(status=Product.ON_SALE)
    rows = list(qs.order_by("id"))
    return ok({"items": [service.product_dict(p) for p in rows], "total": len(rows), "kw": kw})


def api_product_detail(request, pk):
    p = Product.objects.filter(pk=pk).first()
    if not p:
        return err(404, "商品不存在")
    return ok(service.product_dict(p))


def api_cart(request):
    user = service.auth_user(request)
    if not user:
        return err(401, "缺少有效 token")
    return ok(service.cart_payload(user))


@require_http_methods(["POST"])
def api_cart_add(request):
    user = service.auth_user(request)
    if not user:
        return err(401, "缺少有效 token")
    body = service.parse_body(request)
    pid, qty = body.get("product_id"), body.get("qty", 1)
    if not isinstance(pid, int) or not isinstance(qty, int) or qty < 1 or qty > 99:
        return err(400, "product_id / qty 参数非法")
    product = Product.objects.filter(pk=pid, status=Product.ON_SALE).first()
    if not product:
        return err(404, "商品不存在或已下架")
    row, created = service.add_to_cart(user, product, qty)
    return ok({"item": {"id": row.pk, "product_id": pid, "qty": row.qty},
               "cart": service.cart_payload(user), "created": created}, "已加入购物车", status=201)


@require_http_methods(["DELETE"])
def api_cart_remove(request, pk):
    user = service.auth_user(request)
    if not user:
        return err(401, "缺少有效 token")
    row = CartItem.objects.filter(pk=pk, user=user).first()
    if not row:
        return err(404, "购物车条目不存在")
    row.delete()
    return ok(service.cart_payload(user), "已移除")


@require_http_methods(["GET", "POST"])
def api_orders(request):
    user = service.auth_user(request)
    if not user:
        return err(401, "缺少有效 token")
    if request.method == "GET":
        rows = MallOrder.objects.filter(user=user).order_by("-id")[:20]
        return ok({"items": [service.order_dict(o) for o in rows]})
    body = service.parse_body(request)
    pid, qty = body.get("product_id"), body.get("qty", 1)
    if not isinstance(pid, int) or not isinstance(qty, int) or qty < 1:
        return err(400, "product_id / qty 参数非法")
    product = Product.objects.filter(pk=pid).first()
    if not product:
        return err(404, "商品不存在")
    order, error = service.create_order(user, product, qty)
    if error:
        return error
    return ok(service.order_dict(order), "下单成功", status=201)


def api_order_detail(request, pk):
    user = service.auth_user(request)
    if not user:
        return err(401, "缺少有效 token")
    order = MallOrder.objects.filter(pk=pk).first()
    if not order:
        return err(404, "订单不存在")
    if order.user_id != user.pk:
        return err(403, "无权查看他人订单")
    return ok(service.order_dict(order))


@require_http_methods(["POST"])
def api_order_pay(request, pk):
    user = service.auth_user(request)
    if not user:
        return err(401, "缺少有效 token")
    order = MallOrder.objects.filter(pk=pk).first()
    if not order:
        return err(404, "订单不存在")
    if order.user_id != user.pk:
        return err(403, "无权支付他人订单")
    if order.status == MallOrder.CANCELLED:
        return err(409, "订单已取消")
    data, error = service.pay_order(order)
    if error:
        return error
    return ok(data, "支付成功")


@require_http_methods(["POST"])
def api_order_cancel(request, pk):
    user = service.auth_user(request)
    if not user:
        return err(401, "缺少有效 token")
    order = MallOrder.objects.filter(pk=pk, user=user).first()
    if not order:
        return err(404, "订单不存在")
    if order.status != MallOrder.CREATED:
        return err(409, "当前状态不可取消")
    order.status = MallOrder.CANCELLED
    order.save(update_fields=["status"])
    return ok(service.order_dict(order), "已取消")


# ==================== 回归看板 ====================
def console(request):
    return render(request, "console.html")


def report_view(request):
    path = settings.REPORTS_DIR / "report.html"
    if not path.exists():
        return HttpResponse("还没有生成报告，请先点看板上的「一键跑回归」。", status=404)
    return FileResponse(path.open("rb"), content_type="text/html; charset=utf-8")


def _read_json(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def api_state(request):
    flags = bugflags.all_flags()
    last_run = _read_json(settings.REPORTS_DIR / "last_run.json", None)
    run_status = _read_json(_RUN_STATUS, {"running": False, "log": ""})
    calls = list(ApiCallLog.objects.all().values("method", "path", "status", "duration_ms", "actor")[:24])

    found_ids = set()
    if last_run:
        found_ids = {c.get("defect") for c in last_run.get("cases", []) if c.get("status") == "failed"}
    defects = []
    for d in DEFECTS:
        item = dict(d)
        item["active"] = flags.get(d["flag"], False)
        item["found"] = d["id"] in found_ids
        defects.append(item)

    return JsonResponse({
        "code": 0, "message": "ok",
        "data": {
            "flags": flags,
            "flag_labels": bugflags.BUG_CATALOG,
            "defects": defects,
            "last_run": last_run,
            "run_status": run_status,
            "calls": calls,
            "inventory": {
                "users": MallUser.objects.count(),
                "products": Product.objects.count(),
                "orders": MallOrder.objects.count(),
                "cart_items": CartItem.objects.count(),
            },
        },
    }, json_dumps_params={"ensure_ascii": False})


@require_http_methods(["POST"])
def api_toggle(request):
    body = service.parse_body(request)
    if "all" in body:
        flags = bugflags.set_all(body["all"])
    elif "key" in body and "value" in body:
        flags = bugflags.set_flag(str(body["key"]), body["value"])
        if flags is None:
            return err(400, "未知缺陷开关")
    else:
        return err(400, "请求体需包含 all 或 key+value")
    return ok({"flags": flags, "active_count": sum(flags.values())}, "缺陷开关已更新")


def _write_run_status(payload):
    with _RUN_LOCK:
        _RUN_STATUS.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _run_worker(base_url):
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env["NO_PROXY"] = env["no_proxy"] = "127.0.0.1,localhost"
    env["MALL_BASE_URL"] = base_url
    try:
        proc = subprocess.run(
            [sys.executable, str(_BASE / "run_regression.py"), "--reuse-server"],
            cwd=str(_BASE), env=env, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=420,
        )
        log = (proc.stdout or "") + (proc.stderr or "")
        _write_run_status({
            "running": False, "exit_code": proc.returncode,
            "log": log[-4000:],
            "finished_at": __import__("time").strftime("%Y-%m-%d %H:%M:%S"),
        })
    except Exception as exc:  # 子进程异常也要把状态收尾，避免看板一直转圈
        _write_run_status({"running": False, "exit_code": -1, "log": f"执行失败：{exc}"})


@require_http_methods(["POST"])
def api_run(request):
    status = _read_json(_RUN_STATUS, {"running": False})
    if status.get("running"):
        return ok({"started": False}, "回归正在运行中，请稍候")
    _write_run_status({"running": True, "exit_code": None, "log": "正在启动 pytest …"})
    base_url = f"http://{request.get_host()}"
    threading.Thread(target=_run_worker, args=(base_url,), daemon=True).start()
    return ok({"started": True}, "已启动回归")
