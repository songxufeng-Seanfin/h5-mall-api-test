# H5 商城接口回归与缺陷单 · 技术文档

> v1.0 · 2026-11-17 · pytest 9 / requests 2 / allure-pytest 2 / Django 5.2
> 35 条接口用例 · 6 条规范化缺陷单 · 一轮回归约 8~15 秒

---

## 0. 一分钟先读懂骨架

前三个项目我们都在**写功能**：商城能下单、通知能消费、文件能秒传。这个项目换了个角色——**写一个专门挑刺的自动检查员**。

用一句话说完整件事：

> 先准备一个小型 H5 商城接口当「靶子」（故意留 6 个 bug），再用 pytest 按 35 条清单逐条调用接口、比对返回结果，把不对的地方自动整理成 6 张缺陷单，最后出一份能双击打开的测试报告；把 6 个 bug 修掉后，同一套清单一跑就全绿。

由外向内分三层，先记住这张图，后面每节都是往里拆一层：

| 层次 | 谁在干活 | 白话比喻 | 主要文件 |
|---|---|---|---|
| 第一层 · 看板 | 浏览器页面 + Django 视图 | 仪表盘，按钮一按就开始考试 | `templates/console.html`、`static/app.js`、`mall/views.py` |
| 第二层 · 检查员 | pytest + requests + Allure | 监考、阅卷、留证据、写成绩单 | `tests/`、`run_regression.py`、`reports/` |
| 第三层 · 靶子 | 内置 H5 商城 JSON 接口 | 被考的学生，身上有 6 个已知错题 | `mall/service.py`、`mall/urls.py`、`mall/models.py` |

一个很容易搞混的点：**这次「失败」是产出，不是事故**。6 条用例变红，正说明检查员把 6 个缺陷抓出来了；如果全绿反而说明靶子没犯错、没东西可报。

---

## 1. 交付清单

| 类别 | 文件 | 作用 |
|---|---|---|
| 一键回归 | `run_regression.py` | 跑 pytest → 汇总 → 出报告 → 更新看板 |
| 被测服务 | `config/`、`mall/` | Django 项目，15 个商城接口 + 5 张表 + 6 个缺陷开关 |
| 测试套件 | `tests/conftest.py`、`tests/client.py`、`tests/test_01~07_*.py` | 夹具、请求封装、35 条用例 |
| 缺陷数据 | `defect_catalog.py` | 6 条缺陷单的结构化数据，看板和报告共用 |
| 报告产物 | `reports/report.html`、`reports/defects.md` | 免 Java 单页报告 + Markdown 缺陷单（随仓库保留样例） |
| 报告脚本 | `reports/build_report.py`、`reports/defect_reports.py` | 把结果渲染成上面两份交付物 |
| 看板 | `templates/`、`static/app.js` | 统计卡、用例清单、缺陷开关、缺陷单、请求流水 |
| 文档 | `docs/technical-doc.md`、`docs/blog-post.md`、`docs/reader.html` | 技术文档、博客、离线双 Tab 阅读版 |

代码规模约 2,500 行，其中测试与报告相关约 1,000 行。运行期数据（`runtime/`、数据库、`allure-results/`、JUnit XML）都不入库，只提交源码、文档与报告样例。

---

## 2. 专有名词，先用白话记住

| 名词 | 白话解释 | 在本项目里对应什么 |
|---|---|---|
| SUT（被测系统） | 被考试的对象 | 内置 H5 商城接口 |
| 接口 / API | 网址 + 方法 + 参数，返回 JSON | `/api/products/?page=1` |
| pytest | 测试调度员：按清单跑、统计通过失败 | `python -m pytest` |
| 用例（case） | 一条检查项：发什么请求、期望什么结果 | `test_login_wrong_password_rejected` |
| 断言（assert） | 「我认为应该是这样」，不对就判失败 | `assert resp.status_code == 401` |
| fixture（夹具） | 用例开跑前自动准备好的东西 | 已登录的客户端、干净的数据库 |
| hook（钩子） | 框架留的插口，在特定时刻插一段自己的逻辑 | 用例跑完收请求响应证据 |
| requests | 用代码模拟手机发 HTTP 请求 | `ApiClient` |
| token | 登录凭证，之后每个请求带上它 | `X-Token` 请求头 |
| Allure | 把测试结果变成可视化报告的框架 | `allure-results/` + 单页报告 |
| JUnit XML | 测试结果的通用交换格式，CI 都认 | `reports/junit.xml` |
| 回归测试 | 代码改完后，用同一套清单再考一次 | 修复后从 29/6 变 35/0 |
| 缺陷单 | 把一个 bug 写清楚：怎么复现、应该怎样、实际怎样 | `DEF-001` ~ `DEF-006` |
| 幂等 | 同一个操作做多次，结果和做一次一样 | 重复添加购物车 / 重复支付 |
| 契约 | 所有接口都遵守的统一格式 | `{code, message, data}` |
| 严重级 | 缺陷有多要命 | P0 致命 / P1 严重 / P2 一般 |

---

## 3. 从外向内：一次回归的完整往返

点一下看板上的「一键跑回归」，背后是这样一圈：

1. 浏览器 `POST /api/run/`（Django 视图 `api_run`）。
2. 视图起一个后台线程，避免把网页请求卡住；同时把 `runtime/run_status.json` 标成 `running=true`。
3. 线程执行 `python run_regression.py --reuse-server`。
4. 脚本调用 `pytest`，pytest 通过 `conftest.py` 的 session 夹具探活：`MALL_BASE_URL`（默认 `127.0.0.1:8002`）能连通就复用，没有就临时拉起一个服务，跑完关掉。
5. 每条用例前，autouse 夹具调 `POST /api/admin/reset/` 把商城恢复成干净种子数据——**用例之间不许互相污染**。
6. `ApiClient` 用 requests 发请求，自动带 token，并记录每一次请求与响应。
7. 断言通过/失败；失败时 hook 把证据挂成 Allure 附件，并写进 `results.json`。
8. 35 条跑完，`run_regression.py` 汇总成 `last_run.json`，再生成 `report.html` 与 `defects.md`。
9. 看板前端每 2 秒轮询 `/api/state/`，读到 `running=false` 就刷新统计卡、用例清单和缺陷单。

这圈里最值得记住的是 **第 5 步和第 8 步**：前者保证结果可复现，后者保证结果可交付。

---

## 4. 三层架构各自负责什么

| 层 | 输入 | 输出 | 关键约束 |
|---|---|---|---|
| 看板层 | 用户点击 / 轮询 | 统计、清单、开关、报告链接 | 只读运行期 JSON，不参与测试判断 |
| 测试层 | 用例清单 + 靶子地址 | 每条用例的通过/失败 + 证据 | 用例只描述「正确行为」，不看缺陷开关 |
| 靶子层 | HTTP 请求 | 统一 JSON 响应 | 6 个开关决定「犯错」还是「正确」 |

这个分层有一个刻意的设计：**用例永远写「应该怎样」，开关只改变靶子行为**。所以同一套 35 条用例，开关打开时 29 通过 / 6 失败，关掉后 35 通过 / 0 失败，用例本身一个字都不用改。这就是回归测试的价值——用不变的清单反复验证修改。

---

## 5. 靶子：5 张表与 15 个接口

数据库用 SQLite，5 张表：

| 表 | 存什么 | 为什么要它 |
|---|---|---|
| `MallUser` | 账号、密码、昵称、token | 登录态与越权校验 |
| `Product` | 名称、价格（分）、库存、类目、上下架状态 | 商品、搜索、库存缺陷 |
| `CartItem` | 用户、商品、数量 | 暴露重复添加未累加的缺陷 |
| `MallOrder` | 订单号、商品、数量、金额、状态、`paid_count` | 暴露超卖与重复支付 |
| `ApiCallLog` | 方法、路径、状态码、耗时、时间 | 看板右侧「接口请求流水」 |

金额统一用「分」存整数，是接口测试里常查的一个点：浮点会有精度误差，金额不能这么做。

15 个商城接口：

| 模块 | 接口 |
|---|---|
| 健康 / 管理 | `GET /api/health/`、`POST /api/admin/reset/` |
| 认证 | `POST /api/auth/login/`、`POST /api/auth/logout/`、`GET /api/auth/profile/` |
| 商品 | `GET /api/products/`、`GET /api/products/search/`、`GET /api/products/<id>/` |
| 购物车 | `GET /api/cart/`、`POST /api/cart/items/`、`DELETE /api/cart/items/<id>/` |
| 订单 / 支付 | `GET|POST /api/orders/`、`GET /api/orders/<id>/`、`POST /api/orders/<id>/pay/`、`POST /api/orders/<id>/cancel/` |

另外 5 个是看板自己的接口（`GET /`、`GET /report/`、`GET /api/state/`、`POST /api/toggle/`、`POST /api/run/`）。

**和项目 1 的关系**：两周计划里写的是「依赖项目 1」，但项目 1 是页面型站点（表单 + 模板），并没有 REST JSON 接口。为了让这套回归能独立复现，本仓库内置了一份**同源业务契约**的轻量靶子（用户 / 商品 / 搜索 / 购物车 / 订单 / 支付）。以后项目 1 若加上 API，只要把环境变量 `MALL_BASE_URL` 指过去，用例在契约一致的前提下不用改写。

---

## 6. 统一响应契约

所有接口，不管成功失败，都返回同一个外壳：

```json
{ "code": 0, "message": "ok", "data": { "...": "..." } }
```

失败时 `code` 等于 HTTP 状态码、`data` 为 `null`：

```json
{ "code": 401, "message": "账号或密码错误", "data": null }
```

`test_unified_response_contract` 一次检查 4 类响应（成功、参数错误、鉴权失败、业务成功），逐条确认三个字段齐全、`code` 与 HTTP 状态自洽。这类用例不测业务，测的是**所有接口都守规矩**，是接口回归里性价比最高的一类。

---

## 7. 6 个可开关的缺陷位

开关状态写在 `runtime/bug_flags.json`，Django 每次请求重新读，改完立刻生效。看板上可以直接逐个拨，也可以一键全开 / 全关。

| 编号 | 开关 | 缺陷 | 级别 | 抓它的用例 |
|---|---|---|---|---|
| DEF-001 | `AUTH_BYPASS_WRONG_PASSWORD` | 错误密码仍签发 token | P0 | `test_login_wrong_password_rejected` |
| DEF-002 | `PAGE_OUT_OF_RANGE_500` | 页码越界返回 500 | P1 | `test_product_list_page_out_of_range_empty` |
| DEF-003 | `SEARCH_INCLUDE_OFF_SHELF` | 搜索混入已下架商品 | P1 | `test_search_excludes_off_shelf` |
| DEF-004 | `CART_DUPLICATE_ROW` | 重复添加生成重复行 | P1 | `test_cart_add_same_item_accumulates` |
| DEF-005 | `ORDER_IGNORE_STOCK` | 不校验库存造成超卖 | P0 | `test_order_reject_when_stock_insufficient` |
| DEF-006 | `PAY_NOT_IDEMPOTENT` | 重复支付不拦截 | P0 | `test_pay_duplicate_rejected` |

为什么不真的把代码写坏？因为真实项目里缺陷是「开发改出来的」，测试人员不会去改生产代码。用开关模拟，可以在同一个仓库里反复演示「发现 → 提单 → 修复 → 回归」，也不会把仓库弄脏。

---

## 8. 35 条用例怎么分组

| 模块 | 文件 | 条数 | 主要检查点 |
|---|---|---|---|
| 01 健康检查与认证 | `test_01_health_auth.py` | 6 | 探活、登录、错误密码、必填字段、token 鉴权 |
| 02 商品列表与详情 | `test_02_products.py` | 6 | 字段与类型、分页不重复、越界、类目筛选、404 |
| 03 商品搜索 | `test_03_search.py` | 5 | 命中、大小写、空结果、下架过滤、特殊字符 |
| 04 购物车 | `test_04_cart.py` | 6 | 添加、幂等累加、金额合计、删除、401、参数校验 |
| 05 订单 | `test_05_orders.py` | 6 | 创建、库存、金额计算、详情、取消、401 |
| 06 支付与越权 | `test_06_pay.py` | 4 | 支付、重复支付、状态流转、他人订单 403 |
| 07 契约与性能 | `test_07_contract.py` | 2 | 统一响应契约、接口耗时基线 |
| **合计** | | **35** | 其中 6 条对应缺陷单 |

分组按**业务模块**而不是按技术层，是为了报告出来时，产品、后端、测试都能看懂哪块出了问题。

---

## 9. fixture：登录态与数据隔离

`tests/conftest.py` 里四个夹具把重复劳动收在一处：

```python
@pytest.fixture(autouse=True)
def fresh_state(server):
    requests.post(server + "/api/admin/reset/", timeout=10)
    yield

@pytest.fixture
def logged_in(api):
    resp, body = api.login("alice", "123456")
    assert resp.status_code == 200
    return api
```

- `server`：session 级，一轮只做一次，负责探活或临时起服务。
- `fresh_state`：`autouse=True` 表示每条用例自动执行，不用在用例里写。
- `api`：一个干净的请求客户端。
- `logged_in` / `bob_client`：已登录的客户端，后者用来测越权。

用例里因此看不到一句登录代码，只写断言。这就是 fixture 的意义：**把「准备」和「判断」分开**。

另一个细节：用例不硬编码商品主键。`reset_demo()` 每次重建种子数据，SQLite 自增 id 会变，所以 `ApiClient.product_by_name("考研数学真题")` 先按名字查回 id 再用。硬编码 id 是接口测试里非常常见的脆点。

---

## 10. 请求证据与 Allure 附件

`ApiClient` 每次请求都记一条：

```python
self.calls.append({
    "method": method, "url": url,
    "request": {"json": json_body, "params": params, "token": ...},
    "response": {"status_code": resp.status_code, "body": body},
    "duration_ms": duration,
})
```

`conftest.py` 的 `pytest_runtest_makereport` 钩子在每条用例跑完后做两件事：把最近 10 次请求响应挂成 Allure 的 JSON 附件；把用例的模块、耗时、状态、缺陷编号、失败信息、最后两次请求写成结构化结果。

于是缺陷单里的「证据」不是手写的描述，而是**真的从这一轮请求里截下来的响应**。例如 DEF-006 的证据就是第二次支付返回 `paid_count: 2` 的那段 JSON。

---

## 11. 四类报告产物

| 产物 | 给谁看 | 说明 |
|---|---|---|
| `reports/junit.xml` | CI / 流水线 | 通用格式，Jenkins、GitHub Actions 都认 |
| `reports/allure-results/<批次>/` | 有 Java 环境的机器 | `allure serve <目录>` 出官方报告 |
| `reports/report.html` | 任何人，双击即开 | 自包含单页，统计条、分组用例、失败证据、缺陷单 |
| `reports/defects.md` | 开发 / 导师 | 6 条规范化缺陷单，可贴到 issue 或邮件 |

本机没有 Java，也没有 `allure` 命令行，所以额外写了 `build_report.py`：读 `results.json` + `last_run.json` + `defect_catalog.py`，用纯标准库渲染一份 Allure 风格单页。官方 `allure-results` 仍然保留，换台机器就能看官方版。

每轮 Allure 结果写进**带时间戳的批次子目录**，既不删除历史结果，也不会把多轮数据混在一起。

---

## 12. 缺陷单模板逐字段解释

以 `DEF-001` 为例，一条规范缺陷单包含：

| 字段 | 内容示例 | 为什么必须有 |
|---|---|---|
| 编号 / 标题 | `DEF-001` 错误密码仍可登录并签发 token | 唯一可追踪 |
| 严重级 / 模块 | P0 致命 / 认证 | 决定修复优先级与分派对象 |
| 接口 | `POST /api/auth/login/` | 定位范围 |
| 前置条件 | 存在账号 alice / 123456，缺陷开关打开 | 别人能复现的前提 |
| 复现步骤 | 1. 用错误密码登录 2. 看状态码与响应体 | 一步一步照做就能重现 |
| 预期结果 | HTTP 401，不返回 token | 判断对错的依据 |
| 实际结果 | HTTP 200，返回有效 token | 现在真实发生了什么 |
| 证据 | 用该 token 能访问 profile 返回 200 | 不是口头描述 |
| 根因推测 | 漏掉密码比对，只判断用户是否存在 | 帮开发少走弯路 |
| 修复建议 | 补全校验，失败统一 401 且补一条越权用例 | 可执行的下一步 |
| 关联用例 | `test_01_health_auth.py::test_login_wrong_password_rejected` | 修复后跑哪条验证 |

`reports/defect_reports.py` 会把 6 条数据渲染成 Markdown，`build_report.py` 和看板则从同一份 `defect_catalog.py` 读取——**一处定义、三处展示**，不会出现报告里写 P1、看板上写 P2 的情况。

---

## 13. 回归闭环：从 6 个红到全绿

同一套 35 条用例，两种状态：

| 状态 | 缺陷开关 | 通过 | 失败 | 通过率 | 说明 |
|---|---|---|---|---|---|
| 注入缺陷 | 6 / 6 | 29 | 6 | 82.9% | 6 条失败正好对应 6 张缺陷单 |
| 模拟修复 | 0 / 6 | 35 | 0 | 100% | 清单不变，缺陷全部收敛 |

操作步骤（看板上点按钮即可）：

```bash
# 1) 一键跑回归：29 通过 / 6 失败，报告与缺陷单生成
python run_regression.py

# 2) 模拟开发修完全部缺陷
curl -X POST http://127.0.0.1:8002/api/toggle/ \
     -H "Content-Type: application/json" -d '{"all": false}'

# 3) 同一套用例再跑一次：35 通过 / 0 失败
python run_regression.py
```

这个闭环是整份简历项目里最值得讲的一段：**测试的价值不在于「跑过了」，而在于「修改之后还能证明没把别的地方改坏」**。

---

## 14. 几个关键实现细节

- **条件更新防超卖**：正确实现用 `Product.objects.filter(pk=..., stock__gte=qty).update(stock=F("stock") - qty)`，受影响行数为 0 就说明库存不足，直接 409。这是数据库层面的原子判断，比「先查再改」安全。
- **购物车幂等**：正确实现按 `(user, product)` 查已有行，用 `F("qty") + n` 原子累加；缺陷态每次直接 `create` 新行。
- **支付状态机**：正确实现先判断 `status == created` 才允许支付，否则 409；`paid_count` 恒为 1。缺陷态不管状态一律 +1。
- **URL 顺序**：`api/products/search/` 必须排在 `api/products/<int:pk>/` 前面，否则 `search` 会被当成主键匹配失败——这个坑在项目 1 的路由里也踩过一次。
- **鉴权**：API 用自定义 token（`X-Token` 或 `Authorization: Bearer`），因此中间件刻意精简，不引入 session / CSRF；看板自身的 POST 也无需 CSRF token。
- **调用留痕**：`ApiLogMiddleware` 记录每个 `/api/` 请求的状态码与耗时，但跳过 `/api/state/`、`/api/run/` 等看板自身接口，避免流水被轮询刷屏。
- **后台线程跑回归**：`api_run` 用 `threading.Thread` + `subprocess.run` 执行，状态写文件，前端轮询。这样网页不会卡 15 秒，也不会因为 HTTP 超时中断测试。

---

## 15. 踩坑复盘（这一轮真实遇到的）

| # | 现象 | 根因 | 处理 |
|---|---|---|---|
| 1 | 首轮 35 条里 22 条失败，大量 404，但手动 curl 全部 200 | 环境有全局 `HTTP_PROXY`，Python `requests` 默认走代理，把 `127.0.0.1` 请求转发出去，拿到的是代理返回的错误页 | `ApiClient.session.trust_env = False`，同时给子进程设 `NO_PROXY`；curl 验证时统一加 `--noproxy '*'` |
| 2 | 一键脚本清理旧结果目录的操作被拦下 | 涉及删除文件 | 不做任何删除，改为每轮写独立批次目录 `reports/allure-results/<时间戳>/` |
| 3 | 本机没有 Java / `allure` 命令行 | 官方 Allure 报告依赖 Java | 保留 `allure-results`，另写纯标准库 `build_report.py` 出免安装单页报告 |
| 4 | 用例里写死 `product_id=1` 会失效 | 每条用例前重置数据，SQLite 自增主键会变 | 按名称查 id（`product_by_name`），不硬编码主键 |
| 5 | 用例耗时显示 `0.00s` | 单条用例通常几十毫秒 | 看板与报告统一改成毫秒显示 |
| 6 | 看板按钮触发的回归若失败，页面可能一直转圈 | 子进程异常时没有收尾 | `_run_worker` 用 `try/except` 保证任何情况都把 `running` 置回 `false` |
| 7 | 暗色主题下灰色标签浅字看不清 | 主题变量没覆盖到 `.pill.muted` | 和前三个项目一样补暗色覆盖规则，并做 500px 手机端截图复核 |

第 1 条最值得记：**测试环境问题经常被误判成业务缺陷**。先把「请求到底发给了谁」确认清楚，再去看断言。

---

## 16. 自己复现与扩展

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 127.0.0.1:8002 --noreload   # 看板 + 靶子
python run_regression.py                                # 一键回归
python -m pytest -q                                     # 只跑用例也行（无服务时自动拉起）
```

打开 `http://127.0.0.1:8002/` 看板，`http://127.0.0.1:8002/report/` 看报告。

加一条新用例的顺序：在对应模块写 `def test_xxx(...)` → 用 `@pytest.mark.defect("DEF-00X")` 标注是否对应缺陷 → 用 `logged_in` / `api` 夹具 → 写断言 → 重跑 `run_regression.py`，看板和报告会自动把新用例纳入统计（数字从 35 变 36 不需要改任何前端代码）。

要接真实服务：设置 `MALL_BASE_URL=http://<host>:<port>`，只要对方遵守 `{code, message, data}` 契约，用例可直接复用。

---

## 17. 术语速查与简历可写要点

**术语速查**：SUT 是被测系统、fixture 是夹具、hook 是钩子、assertion 是断言、regression 是回归、idempotency 是幂等、contract 是契约、severity 是严重级、evidence 是证据、artifact 是产物。

简历里可以据实写的几句话：

- 基于 pytest + requests 设计 35 条 H5 商城接口回归用例，覆盖认证、商品、搜索、购物车、订单、支付、契约与性能 7 个模块。
- 通过 fixture 统一管理登录态与数据隔离，通过 pytest hook 自动收集请求/响应证据并生成 Allure 附件。
- 产出 6 条规范化缺陷单（含复现步骤、预期/实际、根因与修复建议），并用缺陷开关演示「发现 → 修复 → 回归」闭环，修复后用例通过率从 82.9% 升至 100%。
- 输出 JUnit XML、Allure 原始结果、免 Java 单页报告与可视化看板，支持一键回归。

---

*文档随代码存于 `docs/`，`docs/reader.html` 为离线双 Tab 阅读版，双击即可打开。*
