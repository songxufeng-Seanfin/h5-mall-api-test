"""被测商城的数据表（故意保持精简，方便逐条对照接口用例）。

金额统一用「分」存整数，避免浮点误差——这也是接口测试里常查的一个点。
"""
from django.db import models


class MallUser(models.Model):
    username = models.CharField(max_length=64, unique=True)
    password = models.CharField(max_length=128)  # 演示用明文，真实项目必须哈希
    nickname = models.CharField(max_length=64)
    token = models.CharField(max_length=64, blank=True, default="")

    def __str__(self):
        return self.username


class Product(models.Model):
    ON_SALE = "on_sale"
    OFF_SHELF = "off_shelf"
    name = models.CharField(max_length=128)
    price = models.IntegerField(help_text="单位：分")
    stock = models.IntegerField(default=0)
    category = models.CharField(max_length=32, default="数码")
    status = models.CharField(max_length=16, default=ON_SALE)

    def __str__(self):
        return self.name


class CartItem(models.Model):
    user = models.ForeignKey(MallUser, on_delete=models.CASCADE, related_name="cart_items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    qty = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)


class MallOrder(models.Model):
    CREATED = "created"
    PAID = "paid"
    CANCELLED = "cancelled"
    order_no = models.CharField(max_length=40, unique=True)
    user = models.ForeignKey(MallUser, on_delete=models.CASCADE, related_name="orders")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    qty = models.IntegerField()
    unit_price = models.IntegerField()
    total = models.IntegerField()
    status = models.CharField(max_length=16, default=CREATED)
    paid_count = models.IntegerField(default=0)  # 用来暴露「重复支付」缺陷
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)


class ApiCallLog(models.Model):
    """每次接口调用的留痕，看板右下角的「请求流水」就是它。"""
    method = models.CharField(max_length=8)
    path = models.CharField(max_length=200)
    status = models.IntegerField()
    duration_ms = models.IntegerField(default=0)
    actor = models.CharField(max_length=64, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]
