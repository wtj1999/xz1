# predictor/tests.py
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
import io
import pandas as pd

class PredictorAPITest(TestCase):
    def setUp(self):
        """初始化测试客户端"""
        self.client = APIClient()

    def test_health_endpoint(self):
        """测试 /api/health/"""
        response = self.client.get("/api/health/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("status", response.json())
        self.assertEqual(response.json()["status"], "ok")

    def test_single_predict(self):
        """测试单条预测 /api/predict/"""
        payload = {
            "data": {
                "工步序号": 1,
                "电压": 3.2197,
                "电阻": 0.382,
                "负短电压": 2,
                "K值": 0,
                "来料分容标识": 2,
                "来料化成容量": 0,
                "来料电芯K值": 0.75562,
                "来料内阻4": 0.411,
                "来料V2壳压": 2.27123,
                "来料V3壳压": 2.3065,
                "来料电芯厚度": 40.197,
                "来料V2电压": 3.24784,
                "来料V3电压": 3.2424,
                "来料电芯电压5": 3.2197,
                "来料电芯重量": 1111.7,
                "来料电容数据": 55891,
                "来料二注保液量": 204.65,
                "来料Dcir": 1.652,
                "来料V2内阻": 0.399,
                "累计时间_秒": 1
            }
        }
        response = self.client.post("/api/predict/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("prediction", response.json())
        result = response.json()
        print(result)

    def test_batch_predict(self):
            """测试批量预测 /api/predict/batch/"""
            payload = {
                "data": [
                    {"工步序号": 1, "电压": 3.2197, "电阻": 0.382, "负短电压": 2, "K值": 0, "来料分容标识": 2, "来料化成容量": 0, "来料电芯K值": 0.75562, "来料内阻4": 0.411,
                "来料V2壳压": 2.27123, "来料V3壳压": 2.3065, "来料电芯厚度": 40.197, "来料V2电压": 3.24784, "来料V3电压": 3.2424, "来料电芯电压5": 3.2197, "来料电芯重量": 1111.7,
                "来料电容数据": 55891, "来料二注保液量": 204.65, "来料Dcir": 1.652, "来料V2内阻": 0.399, "累计时间_秒": 1},
                    {"工步序号": 1, "电压": 3.2197, "电阻": 0.382, "负短电压": 2, "K值": 0, "来料分容标识": 2,
                     "来料化成容量": 0, "来料电芯K值": 0.75562, "来料内阻4": 0.411,
                     "来料V2壳压": 2.27123, "来料V3壳压": 2.3065, "来料电芯厚度": 40.197, "来料V2电压": 3.24784,
                     "来料V3电压": 3.2424, "来料电芯电压5": 3.2197, "来料电芯重量": 1111.7,
                     "来料电容数据": 55891, "来料二注保液量": 204.65, "来料Dcir": 1.652, "来料V2内阻": 0.399,
                     "累计时间_秒": 1},
                ]
            }
            response = self.client.post("/api/predict/batch/", payload, format="json")
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIn("predictions", response.json())
            self.assertEqual(len(response.json()["predictions"]), 2)
            result = response.json()
            print(result)
    def test_file_predict(self):
        """测试文件上传预测 /api/predict/file/"""
        # 构造一个 CSV 文件（内存中生成）
        df = pd.DataFrame([
            {"特征1": 1.0, "特征2": "A", "特征3": 2.0},
            {"特征1": 1.1, "特征2": "B", "特征3": 2.2},
        ])
        csv_buf = io.StringIO()
        df.to_csv(csv_buf, index=False)
        csv_buf.seek(0)

        response = self.client.post(
            "/api/predict/file/",
            {"file": csv_buf},
            format="multipart"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("predictions", response.json())
        self.assertEqual(len(response.json()["predictions"]), 2)
