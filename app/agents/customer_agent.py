"""First company agent: controlled customer-response agent."""
from __future__ import annotations

from typing import Any, Iterable

from ..audit import AuditLog
from ..config import Settings
from ..data.company import CompanyDataStore
from ..llm.ollama import OllamaClient
from ..models import IncomingMessage
from ..tool_registry import ToolRegistry
from ..tools.customer_actions import create_support_ticket, save_order_draft
from ..tools.products import calculate_product, search_products


class CustomerAgent:
    """Small, testable customer agent; model orchestration can be added later."""

    def __init__(self, products: Iterable[dict[str, Any]], audit: AuditLog, llm: OllamaClient | None = None):
        self.products = list(products)
        self.audit = audit
        self.llm = llm
        self.tools = ToolRegistry(audit)
        self.tools.register("search_products", lambda query: search_products(self.products, query))
        self.tools.register("calculate_product", lambda product_name, quantity: calculate_product(self.products, product_name, quantity))
        self.tools.register("create_support_ticket", lambda phone, subject, details: create_support_ticket(phone, subject, details))
        self.tools.register("save_order_draft", lambda phone, details: save_order_draft(phone, details))

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> "CustomerAgent":
        settings = settings or Settings()
        settings.validate()
        store = CompanyDataStore(excel_file=settings.company_data_file)
        store.load_excel()
        validation = store.validate()
        if not validation["ok"]:
            raise ValueError("Company data validation failed: " + "; ".join(validation["errors"]))
        llm = OllamaClient(settings.ollama_url, settings.ollama_model)
        return cls(store.all(), AuditLog(settings.database), llm=llm)

    def respond(self, message: IncomingMessage) -> str:
        text = message.text.strip()
        low = text.casefold()
        if not text:
            return "من فضلك اكتب سؤالك أو طلبك."
        if any(word in low for word in ["شكوى", "مشكلة", "دعم", "support", "ticket"]):
            result = self.tools.call("create_support_ticket", actor="customer_agent", phone=message.phone, subject="طلب دعم من العميل", details=text)
            return "تم تسجيل طلب الدعم للمراجعة البشرية." if result.ok else f"تعذر تسجيل طلب الدعم: {result.error}"
        if any(word in low for word in ["طلب", "order", "شراء"]):
            result = self.tools.call("save_order_draft", actor="customer_agent", phone=message.phone, details=text)
            return "تم حفظ مسودة الطلب للمراجعة، ولم يتم تأكيد الشراء." if result.ok else f"تعذر حفظ مسودة الطلب: {result.error}"
        if any(word in low for word in ["سعر", "price", "منتج", "product", "متاح"]):
            result = self.tools.call("search_products", actor="customer_agent", phone=message.phone, query=text)
            if not result.data.get("products"):
                return "لم أجد منتجًا مطابقًا في بيانات الشركة."
            names = [str(row.get("Product Name", row.get("product_name", ""))) for row in result.data["products"][:5]]
            return "المنتجات المطابقة في بيانات الشركة: " + ", ".join(name for name in names if name)
        if self.llm and self.llm.health():
            context = self.products[:20]
            try:
                return self.llm.answer(text, context)
            except Exception:
                pass
        return "أستطيع مساعدتك في المنتجات والأسعار أو تسجيل طلب دعم أو حفظ مسودة طلب للمراجعة."
