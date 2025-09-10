from django.apps import AppConfig


class PredictorConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'predictor'


    def ready(self):
    # 可选：启动时加载模型以减少首次请求延迟
        try:
            from .utils import get_model_service
            get_model_service()
        except Exception:
            # 启动期间不要让异常中断整个 Django 启动；日志记录即可
            import logging
            logging.exception('模型加载失败（启动时）')