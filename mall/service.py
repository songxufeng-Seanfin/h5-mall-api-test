"""被测商城的业务逻辑层。

视图（views.py）只负责「收请求 / 回响应」，判断都放这里，
这样缺陷位集中在同一处，文档里可以逐条对照。
"""
import json
import secrets
import uuid

from django.db import transaction
from django.db.models import F
from django.http import JsonResponse
from django.utils import timezone

from . import bugflags
from .models import ApiCallLog, CartItem, MallOrder, MallUser, Product


# ---------- 统一响应契约 ----------
def ok(data=None, message="ok", status=200):
    return JsonResponse({"code": 0, "message": message, "data": data}, status=status,
                        json_dumps_params={"ensure_ascii": False})


def err(status, message):
    return JsonResponse({"code": status, "message": message, "data": None}, status=status,
                        json_dumps_params={"ensure_ascii": False})


def parse_body(request):
    try:
        data = json.loads(request.body or b"{}")
        return data if isinstance(data, dict) else {}
    except (ValueError, UnicodeDecodeError):
        return {}


def auth_user(request):
    """token 允许两种常见写法：Authorization: Bearer xxx 或 X-Token: xxx"""
    raw = request.META.get("HTTP_AUTHORIZATION", "")
    if raw.lower().startswith("bearer "):
        token = raw[7:].strip()
    else:
        token = request.META.get("HTTP_X_TOKEN", "").strip()
    if not token:
        return None
    return MallUser.objects.filter(token=token).first()


def product_dict(p):
    return {
        "id": p.pk, "name": p.name, "price": p.price, "stock": p.stock,
        "category": p.category, "status": p.status,
    }


def order_dict(o):
    return {
        "id": o.pk, "order_no": o.order_no, "user": o.user.username,
        "product_id": o.product_id, "qty": o.qty,
        "unit_price": o.unit_price, "total": o.total,
        "status": o.status, "paid_count": o.paid_count,
        "created_at": o.created_at.isoformat(),
    }


def cart_payload(user):
    rows = CartItem.objects.filter(user=user).select_related("product").order_by("id")
    items = [{
        "id": r.pk, "product_id": r.product_id, "name": r.product.name,
        "price": r.product.price, "qty": r.qty,
    } for r in rows]
    return {
        "items": items,
        "total_qty": sum(i["qty"] for i in items),
        "total_amount": sum(i["qty"] * i["price"] for i in items),
    }


# ---------- 种子数据 ----------
SEED_USERS = [
    ("alice", "123456", "阿梨"),
    ("bob", "123456", "阿波"),
]

SEED_PRODUCTS = [
    ("二手 iPad Air 5", 189900, 5, "数码", Product.ON_SALE),
    ("校园自行车", 12900, 3, "出行", Product.ON_SALE),
    ("考研数学真题", 3900, 1, "图书", Product.ON_SALE),
    ("机械键盘", 25900, 6, "数码", Product.ON_SALE),
    ("下架校园台灯", 4900, 0, "生活", Product.OFF_SHELF),
    ("蓝牙耳机", 9900, 2, "数码", Product.ON_SALE),
    ("保温杯", 2900, 4, "生活", Product.ON_SALE),
    ("显示器支架", 6900, 2, "数码", Product.ON_SALE),
]


def reset_demo():
    """把商城恢复到干净种子态。pytest 每条用例前都会调一次，保证相互隔离。"""
    with transaction.atomic():
        MallOrder.objects.all().delete()
        CartItem.objects.all().delete()
        Product.objects.all().delete()
        MallUser.objects.all().delete()
        MallUser.objects.bulk_create([
            MallUser(username=u, password=p, nickname=n) for u, p, n in SEED_USERS
        ])
        Product.objects.bulk_create([
            Product(name=n, price=pr, stock=st, category=c, status=s)
            for n, pr, st, c, s in SEED_PRODUCTS
        ])
    return {
        "users": MallUser.objects.count(),
        "products": Product.objects.count(),
        "orders": 0,
        "cart_items": 0,
    }


def login(username, password):
    user = MallUser.objects.filter(username=username).first()
    if user is None:
        return None, err(401, "用户不存在")
    if user.password != password:
        # DEF-001：故意漏掉密码校验，错误密码也放行
        if bugflags.is_on("AUTH_BYPASS_WRONG_PASSWORD"):
            user.token = secrets.token_hex(16)
            user.save(update_fields=["token"])
            return user, None
        return None, err(401, "账号或密码错误")
    user.token = secrets.token_hex(16)
    user.save(update_fields=["token"])
    return user, None


def visible_products():
    return Product.objects.filter(status=Product.ON_SALE)


def add_to_cart(user, product, qty):
    # DEF-004：正常应 upsert 累加；缺陷态每次都插入新行
    if bugflags.is_on("CART_DUPLICATE_ROW"):
        row = CartItem.objects.create(user=user, product=product, qty=qty)
        return row, True
    row = CartItem.objects.filter(user=user, product=product).first()
    if row:
        CartItem.objects.filter(pk=row.pk).update(qty=F("qty") + qty)
        row.refresh_from_db()
        return row, False
    return CartItem.objects.create(user=user, product=product, qty=qty), True


def create_order(user, product, qty):
    """返回 (order, error_response)。正确实现：条件更新扣库存，天然防超卖。"""
    if product.status != Product.ON_SALE:
        return None, err(409, "商品已下架")
    if not bugflags.is_on("ORDER_IGNORE_STOCK"):
        # 原子条件更新：受影响行数为 0 说明库存不足
        affected = Product.objects.filter(
            pk=product.pk, stock__gte=qty
        ).update(stock=F("stock") - qty)
        if affected == 0:
            return None, err(409, "库存不足")
    with transaction.atomic():
        order = MallOrder.objects.create(
            order_no="ORD" + uuid.uuid4().hex[:12].upper(),
            user=user, product=product, qty=qty,
            unit_price=product.price, total=product.price * qty,
            status=MallOrder.CREATED,
        )
    return order, None


def pay_order(order):
    """返回 (dict, error_response)。正确实现：状态机 + 幂等拦截。"""
    if not bugflags.is_on("PAY_NOT_IDEMPOTENT") and order.status != MallOrder.CREATED:
        return None, err(409, "订单已支付或已取消，重复请求已拦截")
    with transaction.atomic():
        locked = MallOrder.objects.get(pk=order.pk)
        locked.paid_count = F("paid_count") + 1
        locked.status = MallOrder.PAID
        locked.paid_at = timezone.now()
        locked.save(update_fields=["paid_count", "status", "paid_at"])
        locked.refresh_from_db()
    return {"id": locked.pk, "order_no": locked.order_no, "status": locked.status,
            "paid_count": locked.paid_count}, None
