# H5 商城接口回归 · 缺陷单汇总

> 生成时间：2026-11-16 23:43:24　|　本轮：35 条用例 / 29 通过 / 6 失败　|　缺陷开关开启 6/6

## 一、汇总表

| 编号 | 标题 | 等级 | 模块 | 接口 | 关联用例 | 本轮结果 |
|---|---|---|---|---|---|---|
| DEF-001 | 错误密码仍可登录并签发 token，存在认证绕过 | P0 / 致命 | 认证 | `POST /api/auth/login/` | `test_01_health_auth.py::test_login_wrong_password_rejected` | 🔴 本轮抓到 |
| DEF-002 | 商品列表页码越界返回 500，未做边界兜底 | P1 / 严重 | 商品 | `GET /api/products/?page=999&size=2` | `test_02_products.py::test_product_list_page_out_of_range_empty` | 🔴 本轮抓到 |
| DEF-003 | 搜索结果包含已下架商品，状态过滤缺失 | P1 / 严重 | 搜索 | `GET /api/products/search/?kw=校园` | `test_03_search.py::test_search_excludes_off_shelf` | 🔴 本轮抓到 |
| DEF-004 | 购物车重复添加同一商品未累加数量，生成重复行 | P1 / 严重 | 购物车 | `POST /api/cart/items/` | `test_04_cart.py::test_cart_add_same_item_accumulates` | 🔴 本轮抓到 |
| DEF-005 | 下单未校验库存且未扣减库存，可超卖 | P0 / 致命 | 订单 | `POST /api/orders/` | `test_05_orders.py::test_order_reject_when_stock_insufficient` | 🔴 本轮抓到 |
| DEF-006 | 重复支付未拦截，同一订单被重复扣款 | P0 / 致命 | 支付 | `POST /api/orders/<id>/pay/` | `test_06_pay.py::test_pay_duplicate_rejected` | 🔴 本轮抓到 |

## 二、逐条详情

### DEF-001　错误密码仍可登录并签发 token，存在认证绕过

- **严重级别**：P0 / 致命　|　**所属模块**：认证　|　**状态**：待修复 / 本轮复现
- **接口**：`POST /api/auth/login/`
- **关联用例**：`test_01_health_auth.py::test_login_wrong_password_rejected`
- **前置条件**：存在账号 alice / 123456；缺陷开关打开
- **复现步骤**：
  1. POST /api/auth/login/，body = {"username":"alice","password":"wrong-pwd"}
  2. 观察 HTTP 状态码与响应体
- **预期结果**：HTTP 401，code=401，data 为 null，不返回任何 token
- **实际结果**：HTTP 200，code=0，data 中携带有效 token，攻击者可直接访问 /api/auth/profile/
- **证据**：response.data.token 非空 → 用该 token 调 profile 返回 200
- **根因推测**：登录分支只判断用户是否存在，漏掉密码比对（等价于 if user: 直接放行）
- **修复建议**：补全 check_password；失败时统一返回 401 且不写 token；补一条越权访问回归用例

### DEF-002　商品列表页码越界返回 500，未做边界兜底

- **严重级别**：P1 / 严重　|　**所属模块**：商品　|　**状态**：待修复 / 本轮复现
- **接口**：`GET /api/products/?page=999&size=2`
- **关联用例**：`test_02_products.py::test_product_list_page_out_of_range_empty`
- **前置条件**：库中 8 个商品，size=2 共 4 页；缺陷开关打开
- **复现步骤**：
  1. GET /api/products/?page=1&size=2 确认正常
  2. GET /api/products/?page=999&size=2
- **预期结果**：HTTP 200，data.items=[]，data.total / data.page 保持一致，不报错
- **实际结果**：HTTP 500，响应体为服务端错误，前端下拉加载更多时白屏
- **证据**：status_code=500，响应不是统一 {code,message,data} 契约
- **根因推测**：切片下标未做 clamp，且异常没有统一转成空结果，直接冒泡到框架 500
- **修复建议**：page 越界时返回空列表；对 page/size 做正整数校验；统一异常处理器转 code=400

### DEF-003　搜索结果包含已下架商品，状态过滤缺失

- **严重级别**：P1 / 严重　|　**所属模块**：搜索　|　**状态**：待修复 / 本轮复现
- **接口**：`GET /api/products/search/?kw=校园`
- **关联用例**：`test_03_search.py::test_search_excludes_off_shelf`
- **前置条件**：存在 status=off_shelf 的「下架校园台灯」；缺陷开关打开
- **复现步骤**：
  1. GET /api/products/search/?kw=校园
  2. 检查返回列表中每一条的 status 字段
- **预期结果**：仅返回 status=on_sale 的商品，下架商品不可被搜到
- **实际结果**：返回中包含 off_shelf 商品，用户点进详情页后无法下单
- **证据**：items[].status 出现 off_shelf
- **根因推测**：搜索查询只拼了 name__icontains，漏掉 status=on_sale 条件
- **修复建议**：搜索与列表共用同一个「可见商品」QuerySet；补下架商品不出现在搜索的用例

### DEF-004　购物车重复添加同一商品未累加数量，生成重复行

- **严重级别**：P1 / 严重　|　**所属模块**：购物车　|　**状态**：待修复 / 本轮复现
- **接口**：`POST /api/cart/items/`
- **关联用例**：`test_04_cart.py::test_cart_add_same_item_accumulates`
- **前置条件**：alice 购物车为空；缺陷开关打开
- **复现步骤**：
  1. 带 token POST /api/cart/items/ {"product_id":1,"qty":1}
  2. 用同样参数再请求一次
  3. GET /api/cart/ 查看行数和数量
- **预期结果**：购物车仅 1 行，qty=2（接口幂等、数量累加）
- **实际结果**：购物车出现 2 行相同商品，行数 2、总数量 2，结算页重复展示
- **证据**：cart.items.length=2，但两个 item.product_id 相同
- **根因推测**：每次请求直接 create，未用 get_or_create / 唯一约束 (user, product)
- **修复建议**：以 (user, product) 唯一键 upsert，用 F('qty') + n 原子累加；数据库补联合唯一约束

### DEF-005　下单未校验库存且未扣减库存，可超卖

- **严重级别**：P0 / 致命　|　**所属模块**：订单　|　**状态**：待修复 / 本轮复现
- **接口**：`POST /api/orders/`
- **关联用例**：`test_05_orders.py::test_order_reject_when_stock_insufficient`
- **前置条件**：商品 3 库存为 1；缺陷开关打开
- **复现步骤**：
  1. 查询商品 3 的 stock=1
  2. 带 token POST /api/orders/ {"product_id":3,"qty":5}
  3. 再查商品 3 的库存
- **预期结果**：HTTP 409，code=409，提示库存不足；库存不变
- **实际结果**：HTTP 201 下单成功，total 按 5 件计算，stock 仍为 1 → 超卖
- **证据**：order.qty=5 > product.stock=1，且下单前后 stock 未变
- **根因推测**：创建订单前缺少 stock >= qty 判断，且没有事务内条件更新库存
- **修复建议**：事务内用条件更新 UPDATE ... WHERE stock >= qty 原子扣减，受影响行数为 0 则回滚返回 409

### DEF-006　重复支付未拦截，同一订单被重复扣款

- **严重级别**：P0 / 致命　|　**所属模块**：支付　|　**状态**：待修复 / 本轮复现
- **接口**：`POST /api/orders/<id>/pay/`
- **关联用例**：`test_06_pay.py::test_pay_duplicate_rejected`
- **前置条件**：订单状态 created；缺陷开关打开
- **复现步骤**：
  1. 对同一订单连续两次 POST /api/orders/<id>/pay/
  2. 观察第二次响应与订单 paid_count
- **预期结果**：第一次 200，第二次 409（或 200 但幂等返回同一结果），paid_count 恒为 1
- **实际结果**：两次都返回 200 且提示支付成功，paid_count=2，存在重复扣款风险
- **证据**：第二次 status_code=200，order.paid_count=2
- **根因推测**：支付处理前没有状态机校验，也没有以 (order_no, 支付请求号) 做唯一约束
- **修复建议**：支付前在事务内校验 status=created 并 CAS 更新为 paid；重复请求返回 409 或幂等返回原结果

## 三、如何验证修复

看板上点「模拟开发修完全部缺陷」，或直接执行：

```bash
curl -X POST http://127.0.0.1:8002/api/toggle/ -H "Content-Type: application/json" -d '{"all": false}'
python run_regression.py
```

同一套 35 条用例不做任何修改，应从 29 通过 / 6 失败变成 35 通过 / 0 失败，
这就是回归测试的价值：用不变的清单反复验证修改没有引入新问题。
