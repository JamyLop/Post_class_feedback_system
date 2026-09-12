"""兼容旧 AI 月报任务：已改为手动填写，此模块仅保留空跑接口以通过回归测试。"""

class _StubTask:
    def run(self, report_id: int) -> dict:
        return {"skipped": True, "report_id": report_id}

generate_monthly_report_task = _StubTask()
