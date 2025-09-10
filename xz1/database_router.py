from django.conf import settings

DATABASE_MAPPING = getattr(settings, "DATABASE_APPS_MAPPING", {})

class DatabaseAppsRouter:
    """
    通用数据库路由器，根据 app_label 决定使用哪个数据库。
    """

    def db_for_read(self, model, **hints):
        """读操作"""
        return DATABASE_MAPPING.get(model._meta.app_label, "default")

    def db_for_write(self, model, **hints):
        """写操作"""
        return DATABASE_MAPPING.get(model._meta.app_label, "default")

    def allow_relation(self, obj1, obj2, **hints):
        """允许两个模型间的关系，如果它们在同一数据库"""
        db_obj1 = DATABASE_MAPPING.get(obj1._meta.app_label, "default")
        db_obj2 = DATABASE_MAPPING.get(obj2._meta.app_label, "default")
        if db_obj1 == db_obj2:
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        迁移时确保 app 只出现在对应数据库。
        """
        if app_label in DATABASE_MAPPING:
            return DATABASE_MAPPING[app_label] == db
        # 未在映射表里的 app 默认走 default 数据库
        return db == "default"
