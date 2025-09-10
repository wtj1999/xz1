# logger/serializers.py
from rest_framework import serializers
from .models import LogRecord

class LogRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = LogRecord
        fields = ["id", "level", "message", "created_at"]
