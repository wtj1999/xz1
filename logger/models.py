# logger/models.py
from django.db import models

class LogRecord(models.Model):
    LEVEL_CHOICES = [
        ("INFO", "Info"),
        ("WARNING", "Warning"),
        ("ERROR", "Error"),
    ]

    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default="INFO")
    message = models.TextField()  # 日志内容
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "logger"   # 确保数据库路由识别
        db_table = "log_record"

    def __str__(self):
        return f"[{self.level}] {self.message[:30]}"

