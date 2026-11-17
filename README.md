# H5 商城接口回归与缺陷单

> 两周计划 · 项目 4（测试方向核心）
> **35 条 pytest 接口用例 · 6 条规范化缺陷单 · 一键回归 + 可视化看板 + 免 Java 报告**

## 一句话骨架

这次不写业务功能，而是写一个「自动检查员」：内置一个小型 H5 商城接口当靶子（故意留 6 个可开关的 bug），用 pytest 调度 35 条用例、requests 模拟手机发请求、逐条比对结果，把不对的地方整理成 6 张缺陷单，最后出一份双击即开的测试报告。

**缺陷全开 → 29 通过 / 6 失败；模拟修复后 → 35 通过 / 0 失败。用例本身一个字都不用改。**

## 快速开始

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 127.0.0.1:8002 --noreload
```

打开：

| 地址 | 内容 |
|---|---|
| `http://127.0.0.1:8002/` | 可视化看板：统计卡、用例清单、缺陷开关、请求流水、缺陷单 |
| `http://127.0.0.1:8002/report/` | 单页测试报告（也可直接双击 `reports/report.html`） |

跑一轮回归：

```bash
python run_regression.py          # 一键：pytest → 汇总 → 报告 → 缺陷单 → 看板数据
python -m pytest -q               # 只跑用例（没有服务时会自动临时拉起）
```

看板上点「一键跑回归」效果相同，页面每 2 秒自动刷新结果。

## 演示闭环（最值得看的一段）

1. 保持 6 个缺陷开关打开 → 点「一键跑回归」→ **35 条 / 29 通过 / 6 失败**，6 张缺陷单标记「本轮抓到」。
2. 点「模拟开发修完全部缺陷」→ 再点「一键跑回归」→ **35 条 / 35 通过 / 0 失败**。
3. 点「重新注入全部缺陷」即可回到演示初始状态。

等价命令行：

```bash
curl -X POST http://127.0.0.1:8002/api/toggle/ -H "Content-Type: application/json" -d '{"all": false}'
python run_regression.py
```

## 目录结构

| 路径 | 作用 |
|---|---|
| `config/` | Django 配置（精简中间件，token 鉴权，运行期目录） |
| `mall/` | 被测商城：5 张表、15 个 JSON 接口、6 个缺陷开关、调用留痕、看板视图 |
| `templates/`、`static/` | 看板页面与原生 JS（统计 / 用例 / 开关 / 缺陷单 / 流水） |
| `tests/` | 35 条用例（7 个模块）+ `conftest.py` 夹具 + `client.py` 请求封装 |
| `defect_catalog.py` | 6 条缺陷单的结构化数据，一处定义三处展示 |
| `run_regression.py` | 一键回归入口 |
| `reports/` | 报告生成脚本 + 交付样例（`report.html`、`defects.md`） |
| `docs/` | 技术文档、博客、离线阅读版 |

## 交付物

| 产物 | 说明 |
|---|---|
| `reports/junit.xml` | 通用测试格式，CI 可用 |
| `reports/allure-results/<批次>/` | Allure 原始结果，有 Java 时 `allure serve <目录>` |
| `reports/report.html` | 免 Java 的 Allure 风格单页报告（随仓库保留样例） |
| `reports/defects.md` | 6 条规范化缺陷单 Markdown |
| `reports/last_run.json` | 看板读取的最近一次运行摘要 |

## 用例与缺陷分布

| 模块 | 条数 | 对应缺陷 |
|---|---|---|
| 01 健康检查与认证 | 6 | DEF-001 认证绕过 |
| 02 商品列表与详情 | 6 | DEF-002 分页越界 500 |
| 03 商品搜索 | 5 | DEF-003 混入下架商品 |
| 04 购物车 | 6 | DEF-004 重复添加不累加 |
| 05 订单 | 6 | DEF-005 超卖 |
| 06 支付与越权 | 4 | DEF-006 重复支付 |
| 07 契约与性能 | 2 | — |

## 文档

- [技术文档](./docs/technical-doc.md) — 由外向内 17 节：骨架、名词白话、三层架构、接口清单、fixture、证据、缺陷单模板、闭环、踩坑复盘
- [博客文章](./docs/blog-post.md) — 第一人称手记：那晚上的 22 个假失败、从 6 个红到全绿
- [离线阅读版](./docs/reader.html) — 双 Tab 自包含 HTML，双击即开，无需联网

改完文档后运行 `python docs/build_reader.py` 可重新生成阅读版。

## 两点说明

- **和项目 1 的关系**：计划里写「依赖项目 1」，但项目 1 是页面型站点、没有 REST JSON 接口。为了让回归套件可独立复现，本仓库内置了同源业务契约的轻量靶子；将来项目 1 加上 API，只要设置 `MALL_BASE_URL` 指过去，契约一致时用例可直接复用。
- **本机环境注意**：运行环境存在全局 `HTTP_PROXY`，Python 的 `requests` 默认会走代理，导致本地接口请求被转发。测试客户端已设置 `trust_env = False` 直连本机；用 curl 手动验证时请加 `--noproxy '*'`。官方 Allure 报告需要 Java 与 `allure` 命令行，本机没有，所以额外提供免 Java 的单页报告。

## 技术栈

pytest 9 · requests 2 · allure-pytest 2 · Django 5.2 · SQLite · 原生 JavaScript
