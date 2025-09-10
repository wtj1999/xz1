# logger/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import LogRecord
from .serializers import LogRecordSerializer

class LogRecordView(APIView):
    def post(self, request):
        serializer = LogRecordSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()  # 保存到 logger_db.sqlite3
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
