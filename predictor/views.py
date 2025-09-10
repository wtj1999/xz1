# predictor/views.py
import io
import csv
import os
import time
import uuid
import logging
from typing import List

import pandas as pd
from django.conf import settings
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import PredictionRecord
from logger.models import LogRecord
from .utils import get_model_service
from .serializers import SinglePredictSerializer, BatchPredictSerializer

logger = logging.getLogger(__name__)

# --- 辅助函数 -------------------------------------------------------------
def _make_download_path(filename: str) -> str:
    """
    返回结果文件保存路径（绝对），并确保目录存在。
    保存到 settings.MEDIA_ROOT/predictions/
    """
    media_root = getattr(settings, "MEDIA_ROOT", None)
    if not media_root:
        # fallback to project root /media
        media_root = os.path.join(settings.BASE_DIR, "media")
    out_dir = os.path.join(media_root, "predictions")
    os.makedirs(out_dir, exist_ok=True)
    return os.path.join(out_dir, filename)


def _build_download_url(request, filepath: str) -> str:
    """
    根据 request 构建可被浏览器下载的绝对 URL（假设 MEDIA_URL 可直接访问，或者 nginx 配置了 media 路径）
    如果 MEDIA_URL 是默认 '/media/'，并且 nginx 正确映射 MEDIA_ROOT，则该 URL 可下载文件。
    """
    media_url = getattr(settings, "MEDIA_URL", "/media/")
    # filename relative to media root
    filename = os.path.basename(filepath)
    # build absolute uri
    base = request.build_absolute_uri('/')
    # ensure no double slashes
    return request.build_absolute_uri(os.path.join(media_url.lstrip('/'), 'predictions', filename))


# --- Views ----------------------------------------------------------------
class HealthCheck(APIView):
    """
    简单健康检查接口。返回 ok + model_version（如果加载成功）。
    GET /api/health/
    """
    permission_classes = []  # 如果需要鉴权，在这里添加

    def get(self, request):
        info = {"status": "ok"}
        try:
            svc = get_model_service()
            # metadata may include model_version
            model_version = getattr(svc, "model_version", None)
            # some metadata may be loaded from meta
            info.update({
                "model_version": model_version,
                "feature_count": len(getattr(svc, "feature_cols", []))
            })
        except Exception as e:
            logger.exception("Health: model service not loaded")
            info.update({"model_load_error": str(e)})
        return Response(info)


class PredictSingle(APIView):
    """
    单条预测接口（同步，低延迟场景）
    POST /api/predict/
    body: {"data": {"feature1": val1, "feature2": val2, ...}}
    """
    permission_classes = []

    def post(self, request):
        t0 = time.time()
        serializer = SinglePredictSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            logger.debug("SinglePredict: validation failed: %s", e)
            LogRecord.objects.create(
                level="ERROR",
                message=f"Validation failed: {serializer.errors}"
            )
            return Response(
                {"error": "validation_error", "detail": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )


        # validated data: cleaned dict (按 feature_cols 顺序)
        cleaned = serializer.validated_data['data']

        try:
            svc = get_model_service()
            df = pd.DataFrame([cleaned], columns=svc.feature_cols)  # 保证列顺序
            preds = svc.predict(df)
            elapsed = time.time() - t0
            prediction_value = float(preds[0])

            # 保存预测结果到 predictor 数据库
            PredictionRecord.objects.create(
                input_data=cleaned,
                prediction=prediction_value
            )

            # 写日志到 logger 数据库
            LogRecord.objects.create(
                level="INFO",
                message=f"Prediction success, value={prediction_value}, elapsed={elapsed:.3f}s"
            )

            resp = {
                "prediction": prediction_value,
                "model_version": getattr(svc, "model_version", None),
                "elapsed_seconds": round(elapsed, 4)
            }
            logger.info("SinglePredict success, elapsed=%.3fs", elapsed)
            return Response(resp)
        except Exception as e:
            logger.exception("SinglePredict: predict failed")
            LogRecord.objects.create(
                level="ERROR",
                message=f"Prediction failed: {str(e)}"
            )
            return Response(
                {"error": "predict_failed", "detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PredictBatch(APIView):
    """
    批量预测接口（接收 list of dict）
    POST /api/predict/batch/
    body: {"data": [ {feature dict}, {feature dict}, ... ]}
    返回：{"predictions": [ {原输入..., "prediction": x}, ... ], "model_version": ...}
    注意：当数据量非常大时，建议使用文件上传 + 后台任务（Celery）。
    """
    permission_classes = []

    def post(self, request):
        t0 = time.time()
        serializer = BatchPredictSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except Exception:
            logger.debug("BatchPredict: validation failed: %s", serializer.errors)
            return Response({"error": "validation_error", "detail": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        records: List[dict] = serializer.validated_data['data']

        try:
            svc = get_model_service()
            # DataFrame, 确保列顺序一致
            df = pd.DataFrame(records, columns=svc.feature_cols)
            preds = svc.predict(df)  # numpy array
            df_result = df.copy()
            df_result['prediction'] = preds
            elapsed = time.time() - t0
            # 将结果转为 records（谨慎：如果数据量大，不要把全部放到内存返回）
            results = df_result.to_dict(orient='records')
            resp = {
                "predictions": results,
                "count": len(results),
                "model_version": getattr(svc, "model_version", None),
                "elapsed_seconds": round(elapsed, 4)
            }
            logger.info("BatchPredict success, count=%d, elapsed=%.3fs", len(results), elapsed)
            return Response(resp)
        except Exception as e:
            logger.exception("BatchPredict: predict failed")
            return Response({"error": "predict_failed", "detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PredictFile(APIView):
    """
    文件上传批量预测接口（同步处理小/中等文件）
    POST /api/predict/file/
    FormData: file=<csv file>
    - CSV 必须包含模型的 feature 列名（可以有额外列）
    - 返回：成功时生成 CSV 文件链接（保存于 MEDIA_ROOT/predictions/）
    注意：若文件很大或需并发处理，请改成异步任务队列（Celery）。
    """
    permission_classes = []

    def post(self, request):
        # 简单 auth key（可选）
        file_obj = request.FILES.get('file', None)
        if file_obj is None:
            return Response({"error": "no_file"}, status=status.HTTP_400_BAD_REQUEST)

        # 限制上传文件大小（可配置），防止滥用
        max_size_mb = int(os.environ.get("PREDICT_MAX_FILE_MB", 50))
        if file_obj.size > max_size_mb * 1024 * 1024:
            return Response({"error": "file_too_large", "max_mb": max_size_mb}, status=status.HTTP_400_BAD_REQUEST)

        svc = None
        try:
            svc = get_model_service()
        except Exception as e:
            logger.exception("PredictFile: model service not available")
            return Response({"error": "model_not_loaded", "detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 读取 CSV 到 DataFrame（注意 encoding / separator，可根据实际定制）
        try:
            # 先把上传文件读到内存 bytes，然后 pandas 读取（更通用，避免 tempfile）
            content = file_obj.read()
            # 尝试 UTF-8, 若失败可尝试 GBK 等（可按需扩展）
            try:
                df_in = pd.read_csv(io.BytesIO(content))
            except Exception:
                # second attempt with gbk
                df_in = pd.read_csv(io.BytesIO(content), encoding='gbk')
        except Exception as e:
            logger.exception("PredictFile: failed to read csv")
            return Response({"error": "read_csv_failed", "detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # 检查是否包含必须的 feature 列
        missing = [c for c in svc.feature_cols if c not in df_in.columns]
        if missing:
            return Response({"error": "missing_features", "missing": missing}, status=status.HTTP_400_BAD_REQUEST)

        # 只取需要的列并保证列顺序
        df_need = df_in[svc.feature_cols].copy()

        # 按块预测以节省内存（可配置 chunk_size）
        chunk_size = int(os.environ.get("PREDICT_CHUNK_SIZE", 5000))
        out_rows = []
        total = len(df_need)
        start_time = time.time()
        try:
            for start in range(0, total, chunk_size):
                end = min(total, start + chunk_size)
                df_chunk = df_need.iloc[start:end]
                preds = svc.predict(df_chunk)
                df_chunk_result = df_in.iloc[start:end].copy()  # 保持原始列（包含额外列）
                df_chunk_result['prediction'] = preds
                out_rows.append(df_chunk_result)
            df_out = pd.concat(out_rows, axis=0)
        except Exception as e:
            logger.exception("PredictFile: batch predict failed")
            return Response({"error": "predict_failed", "detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 保存结果为 csv
        filename = f"pred_{uuid.uuid4().hex}.csv"
        out_path = _make_download_path(filename)
        try:
            df_out.to_csv(out_path, index=False, encoding='utf-8-sig')
            download_url = _build_download_url(request, out_path)
            elapsed = time.time() - start_time
            logger.info("PredictFile success: saved %s, rows=%d, elapsed=%.2fs", filename, len(df_out), elapsed)
            return Response({
                "file_name": filename,
                "rows": len(df_out),
                "download_url": download_url,
                "model_version": getattr(svc, "model_version", None),
                "elapsed_seconds": round(elapsed, 3)
            })
        except Exception as e:
            logger.exception("PredictFile: save failed")
            return Response({"error": "save_failed", "detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
