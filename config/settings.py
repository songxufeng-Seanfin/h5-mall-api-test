"""项目 4 全局配置。

这里同时跑两样东西：
1) mall/ —— 被测系统（H5 商城的 JSON 接口），故意留了 6 个可开关的缺陷；
2) 根 templates/ —— 接口回归看板（把 pytest 结果画出来）。

刻意做成一个自包含仓库：clone 下来不用先启动「项目 1」也能跑全套回归。
若确实要测外部服务，把环境变量 MALL_TARGET_BASE_URL 指过去即可。
"""
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("MALL_SECRET_KEY", "dev-only-h5-mall-api-test-key")
DEBUG = True
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.staticfiles",
    "mall",
]

# API 用 token 鉴权，不依赖 Django session/csrf，中间件保持最小。
MIDDLEWARE = [
    "django.middleware.common.CommonMiddleware",
    "mall.middleware.ApiLogMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
            ]
        },
    }
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

LANGUAGE_CODE = "zh-hans"
TIME_ZONE = "Asia/Shanghai"
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# 回归脚本 / 看板共用的运行期目录（数据文件，不入库）
RUNTIME_DIR = BASE_DIR / "runtime"
REPORTS_DIR = BASE_DIR / "reports"
RUNTIME_DIR.mkdir(exist_ok=True)
REPORTS_DIR.mkdir(exist_ok=True)
