from rest_framework import serializers
from .utils import get_model_service

class SinglePredictSerializer(serializers.Serializer):
    """
    接受一个 record: {"data": {"feature1": value1, ...}}
    - 校验 required features（基于模型 metadata）
    - 简单做类型转换：数值型 -> float，类别型 -> str
    """
    data = serializers.DictField(child=serializers.JSONField(), required=True)

    def validate_data(self, value):
        svc = get_model_service()
        # svc.feature_cols 是训练时的列顺序（metadata）
        required = svc.feature_cols
        missing = [c for c in required if c not in value]
        if missing:
            raise serializers.ValidationError(f"Missing features: {missing}")
        # 类型转换（不改变原 dict，返回新的 dict）
        cleaned = {}
        for c in required:
            v = value.get(c)
            if c in svc.num_features:
                # 数值列：尽量转换为 float，出错则提示
                try:
                    # 允许 None/'' -> 报错，视需求可改为填充默认值
                    cleaned[c] = float(v)
                except Exception:
                    raise serializers.ValidationError({c: f"Expect numeric value for {c}, got {v}"})
            else:
                # 类别列：保证为字符串
                cleaned[c] = '' if v is None else str(v)
        return cleaned

class BatchPredictSerializer(serializers.Serializer):
    """
    接受一个 list of records: {"data": [ {...}, {...} ]}
    """
    data = serializers.ListField(
        child=serializers.DictField(child=serializers.JSONField()),
        required=True,
        allow_empty=False
    )

    def validate_data(self, value):
        svc = get_model_service()
        required = svc.feature_cols
        cleaned_list = []
        errors = {}
        for idx, rec in enumerate(value):
            missing = [c for c in required if c not in rec]
            if missing:
                errors[idx] = {'missing': missing}
                continue
            cleaned = {}
            rec_errors = {}
            for c in required:
                v = rec.get(c)
                if c in svc.num_features:
                    try:
                        cleaned[c] = float(v)
                    except Exception:
                        rec_errors[c] = f"Expect numeric value for {c}, got {v}"
                else:
                    cleaned[c] = '' if v is None else str(v)
            if rec_errors:
                errors[idx] = rec_errors
            else:
                cleaned_list.append(cleaned)
        if errors:
            raise serializers.ValidationError(errors)
        return cleaned_list