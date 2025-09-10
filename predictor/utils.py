import json
import joblib
import os
import pandas as pd
from catboost import CatBoostRegressor
from django.conf import settings


class ModelService:
    def __init__(self):
        models_dir = settings.MODEL_DIR
        meta_path = os.path.join(models_dir, 'metadata.json')
        with open(meta_path, 'r', encoding='utf-8') as f:
            meta = json.load(f)
        self.feature_cols = meta['feature_cols']
        self.cat_features = meta.get('cat_features', [])
        self.num_features = meta.get('num_features', [])
        self.model_version = meta.get('model_version', [])
        self.model_path = os.path.join(models_dir, os.path.basename(meta['model_path']))
        self.pipeline_path = os.path.join(models_dir, os.path.basename(meta['num_pipeline_path']))


        # load model and pipeline
        self.model = CatBoostRegressor()
        self.model.load_model(self.model_path)
        # pipeline may be None if not used
        if os.path.exists(self.pipeline_path):
            self.num_pipeline = joblib.load(self.pipeline_path)
        else:
            self.num_pipeline = None


    def preprocess(self, df: pd.DataFrame):
        missing = [c for c in self.feature_cols if c not in df.columns]
        if missing:
            raise ValueError(f"Missing features: {missing}")
        df = df[self.feature_cols].copy()
        for c in self.cat_features:
            df[c] = df[c].fillna('NA').astype(str)
        if self.num_pipeline and self.num_features:
            df[self.num_features] = self.num_pipeline.transform(df[self.num_features])
        return df


    def predict(self, df: pd.DataFrame):
        X = self.preprocess(df)
        preds = self.model.predict(X)
        return preds




_model_service = None


def get_model_service():
    global _model_service
    if _model_service is None:
        _model_service = ModelService()
    return _model_service