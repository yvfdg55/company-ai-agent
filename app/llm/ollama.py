"""Minimal Ollama client with strict grounded-answer instructions."""
from __future__ import annotations

import requests


class OllamaClient:
    def __init__(self, base_url: str = "http://127.0.0.1:11434", model: str = "qwen3:8b", timeout: int = 90):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def health(self) -> bool:
        try:
            response = requests.get(self.base_url + "/api/tags", timeout=5)
            return response.ok
        except requests.RequestException:
            return False

    def answer(self, question: str, context: list[dict]) -> str:
        system = (
            "أنت وكيل خدمة عملاء. استخدم سياق الشركة فقط. "
            "لا تخترع سعرًا أو مخزونًا أو سياسة. إذا لم توجد المعلومة فقل إنها غير متاحة "
            "وحول الحالة لموظف. لا تؤكد شراءً ولا تطلب بيانات بطاقة. أجب بلغة العميل."
        )
        payload = {
            "model": self.model,
            "stream": False,
            "options": {"temperature": 0.1, "num_predict": 500},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": f"سؤال العميل:\n{question}\n\nسياق الشركة الموثق:\n{context}"},
            ],
        }
        response = requests.post(self.base_url + "/api/chat", json=payload, timeout=self.timeout)
        response.raise_for_status()
        text = response.json().get("message", {}).get("content", "").strip()
        if not text:
            raise RuntimeError("Ollama returned an empty answer")
        return text
