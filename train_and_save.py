import json
import joblib
import numpy as np
import pandas as pd
from catboost import CatBoostRegressor
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler


MODELS_DIR = './models'


if __name__ == '__main__':
    df = pd.read_csv('C:/Users/HP/PycharmProjects/Capacity_Prediction/dataset/pack_data/03HPB0BT0001EYF7S0000035.csv')


    feature_cols = [col for col in df.columns
    if col not in ['电芯条码', '单体电压', '电芯实际位置', '累计时间', '时间', '电芯OCV4时间']]


    cat_features = [c for c in feature_cols if df[c].dtype == 'object']
    num_features = [c for c in feature_cols if c not in cat_features]


    unique_cells = df['电芯条码'].unique()
    np.random.seed(42)
    train_cells = np.random.choice(unique_cells, size=min(100, len(unique_cells)), replace=False)


    train_df = df[df['电芯条码'].isin(train_cells)].copy()
    X_train = train_df[feature_cols]
    y_train = train_df['单体电压']


    # 数值预处理 pipeline（示例）
    num_pipeline = Pipeline([
    ('imputer', SimpleImputer(strategy='median')),
    ('scaler', StandardScaler())
    ])
    if num_features:
        X_train[num_features] = num_pipeline.fit_transform(X_train[num_features])


    model = CatBoostRegressor(iterations=500,
                              learning_rate=0.05,
                              depth=6,
                              loss_function='RMSE',
                              verbose=100)
    model.fit(X_train, y_train, cat_features=cat_features)


    # 保存
    model.save_model(f"{MODELS_DIR}/catboost_model.cbm")
    joblib.dump(num_pipeline, f"{MODELS_DIR}/num_pipeline.joblib")


    meta = {
    'feature_cols': feature_cols,
    'cat_features': cat_features,
    'num_features': num_features,
    'model_path': 'models/catboost_model.cbm',
    'num_pipeline_path': 'models/num_pipeline.joblib',
    'model_version': 'v1'
    }
    with open(f"{MODELS_DIR}/metadata.json", 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


    print('模型与元数据已保存到 models/')