"""接口调用留痕：记录 method / path / 状态码 / 耗时，供看板展示请求流水。"""
import time
from .models import ApiCallLog


class ApiLogMiddleware:
    SKIP = {"/api/state/", "/api/run/", "/api/admin/reset/"}

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.perf_counter()
        response = self.get_response(request)
        path = request.path
        if path.startswith("/api/") and path not in self.SKIP and not path.startswith("/api/admin/"):
            try:
                ApiCallLog.objects.create(
                    method=request.method,
                    path=path[:200],
                    status=getattr(response, "status_code", 0),
                    duration_ms=int((time.perf_counter() - start) * 1000),
                    actor=request.META.get("HTTP_X_ACTOR", "")[:64],
                )
            except Exception:
                pass  # 留痕失败不能影响被测接口本身
        return response
