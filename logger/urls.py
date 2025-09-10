# logger/urls.py
from django.urls import path
from .views import LogRecordView

urlpatterns = [
    path("log/", LogRecordView.as_view(), name="log-record"),
]
