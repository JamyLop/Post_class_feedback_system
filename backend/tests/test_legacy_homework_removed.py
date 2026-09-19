"""作业闭环已下线：公开 OpenAPI 不得重新暴露旧端点。"""

from app.main import app


def test_openapi_excludes_legacy_homework_routes():
    paths = app.openapi()["paths"]
    forbidden_segments = (
        "/assignments",
        "/submissions",
        "/gradings",
        "/questions",
        "/analytics",
        "/feedback",
    )

    assert not [
        path for path in paths
        if any(segment in path for segment in forbidden_segments)
    ]
