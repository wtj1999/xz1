from django.db import models

class PredictionRecord(models.Model):
    """
    存储一次预测请求和结果
    """
    # 输入数据，可以是 JSON 格式
    input_data = models.JSONField()

    # 模型预测结果
    prediction = models.FloatField()

    # 记录预测时间
    created_at = models.DateTimeField(auto_now_add=True)

    # 可选：标记用户或来源
    user_id = models.IntegerField(null=True, blank=True)
    source = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return f"Prediction {self.id} - {self.prediction}"
