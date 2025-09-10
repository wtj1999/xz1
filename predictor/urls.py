from django.urls import path
from .views import PredictSingle, PredictBatch, PredictFile, HealthCheck

app_name = 'predictor'

urlpatterns = [
    path('health/', HealthCheck.as_view(), name='health'),
    path('predict/', PredictSingle.as_view(), name='predict_single'),      # POST /api/predict/
    path('predict/batch/', PredictBatch.as_view(), name='predict_batch'),  # POST /api/predict/batch/
    path('predict/file/', PredictFile.as_view(), name='predict_file'),     # POST /api/predict/file/
]