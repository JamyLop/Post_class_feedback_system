"""通用分页参数：上线前收敛全表 `.all()` 风险。

默认 limit=200（兼容存量前端全量拉取），上限 500，前端可逐步传 limit/offset。
"""

from fastapi import Query

DEFAULT_LIMIT = 200
MAX_LIMIT = 500


def pagination_params(
    limit: int = Query(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    offset: int = Query(default=0, ge=0),
) -> dict:
    return {"limit": limit, "offset": offset}
