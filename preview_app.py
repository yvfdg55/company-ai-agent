import logging
from pathlib import Path
from datetime import datetime

import gradio as gr
import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CompanyAgentAdvancedPreview")

CONFIG = {
    "OLLAMA_URL": "http://127.0.0.1:11434",
    "OLLAMA_MODEL": "qwen3:8b",
    "SOURCE_TYPE": "excel",
    "EXCEL_FILE": "company.xlsx",
    "GOOGLE_SHEET_ID": "",
    "GOOGLE_CREDENTIALS": "service_account.json",
    "WHATSAPP_TOKEN": "",
    "PHONE_NUMBER_ID": "",
    "WHATSAPP_VERIFY_TOKEN": "",
    "WHATSAPP_APP_SECRET": "",
    "WA_API_VERSION": "vXX.X",
    "MYSQL_HOST": "127.0.0.1",
    "MYSQL_PORT": 3306,
    "MYSQL_DATABASE": "company_agent",
    "MYSQL_USER": "company_agent",
}

STATE = {
    "whatsapp_status": "غير متصل - وضع المعاينة",
    "data_status": "بيانات تجريبية محمّلة",
    "last_action": "لم يتم تنفيذ إجراء بعد",
}

ENABLED_TOOLS = {
    "search_company": True,
    "calculate_product": True,
    "create_support_ticket": True,
    "save_order_draft": True,
    "customer_lookup": True,
    "inventory_check": True,
    "sales_report": True,
    "broadcast_preview": False,
}

PRODUCTS = [
    {"Product Name": "Product A", "Price": 120, "Stock": 25, "Category": "منتجات", "Updated": "اليوم"},
    {"Product Name": "Product B", "Price": 85, "Stock": 12, "Category": "منتجات", "Updated": "أمس"},
    {"Product Name": "خدمة الدعم المميز", "Price": 250, "Stock": "متاح", "Category": "خدمات", "Updated": "اليوم"},
    {"Product Name": "باقة الشركات", "Price": 900, "Stock": 4, "Category": "باقات", "Updated": "قبل يومين"},
]

CUSTOMERS = [
    {"phone": "01000000000", "name": "عميل تجريبي 1", "city": "القاهرة", "messages": 12, "last_seen": "اليوم"},
    {"phone": "01000000001", "name": "Test Customer", "city": "الإسكندرية", "messages": 7, "last_seen": "أمس"},
]

CUSTOM_CSS = """
.gradio-container { max-width: 1500px !important; margin: auto !important; font-family: Arial, sans-serif; }
#main-header { border-radius: 18px; padding: 24px; background: linear-gradient(120deg, #102a43, #2563a6 60%, #1d8a77); color: white; margin-bottom: 18px; }
#main-header h1 { color: white; font-size: 30px; margin-bottom: 6px; }
.metric-card { border-radius: 14px !important; padding: 12px; background: #f5f8fc; border: 1px solid #d9e2ec; }
.section-note { border-radius: 12px; padding: 12px; background: #fff8e1; }
footer { display: none !important; }
"""


def stats():
    return {"messages": 24, "customers": len(CUSTOMERS), "orders": 3, "tickets": 2, "products": len(PRODUCTS)}


def dashboard_html():
    s = stats()
    return f"""
    <div style='display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:14px;direction:rtl;'>
      <div class='metric-card'><h2>{s['messages']:,}</h2><p>رسائل اليوم</p></div>
      <div class='metric-card'><h2>{s['customers']:,}</h2><p>العملاء</p></div>
      <div class='metric-card'><h2>{s['orders']:,}</h2><p>طلبات قيد المراجعة</p></div>
      <div class='metric-card'><h2>{s['tickets']:,}</h2><p>تذاكر مفتوحة</p></div>
      <div class='metric-card'><h2>{s['products']:,}</h2><p>سجلات المنتجات</p></div>
    </div>
    """


def chat_with_agent(message, history):
    if not message or not message.strip():
        return "", history
    register_customer("DASHBOARD_TEST_CUSTOMER", "عميل لوحة التحكم")
    q = message.strip()
    low = q.lower()
    if "سعر" in q or "price" in low:
        answer = "سعر Product A هو 120. هذه نتيجة تجريبية من بيانات المعاينة."
    elif "مخزون" in q or "stock" in low or "متاح" in q:
        answer = "المخزون التجريبي: Product A = 25، Product B = 12، وباقة الشركات = 4."
    elif "عميل" in q or "customer" in low:
        answer = "يمكنك البحث عن العميل من تبويب العملاء باستخدام رقم الهاتف."
    elif "شكوى" in q or "ticket" in low or "support" in low:
        answer = "تم إنشاء تذكرة تجريبية PREVIEW-001 للمراجعة."
    elif "طلب" in q or "order" in low:
        answer = "تم حفظ طلب تجريبي للمراجعة، ولم يتم تأكيد أي شراء."
    elif "تقرير" in q or "report" in low:
        answer = "التقرير التجريبي: 24 رسالة، 3 طلبات قيد المراجعة، و2 تذكرة مفتوحة."
    else:
        answer = "مرحبًا! اسأل عن الأسعار أو المخزون أو العملاء أو الطلبات أو التقارير."
    history = history or []
    history.extend([{"role": "user", "content": q}, {"role": "assistant", "content": answer}])
    STATE["last_action"] = f"محادثة تجريبية: {q[:50]}"
    return "", history


def get_products():
    return pd.DataFrame(PRODUCTS)


def get_customers():
    return pd.DataFrame(CUSTOMERS)


def register_customer(phone, name="عميل جديد"):
    phone = str(phone or "").strip()
    if not phone:
        return False
    for customer in CUSTOMERS:
        if customer["phone"] == phone:
            customer["last_seen"] = "الآن"
            return False
    CUSTOMERS.append({
        "phone": phone,
        "name": name or "عميل جديد",
        "messages": 0,
        "last_seen": "الآن",
    })
    STATE["last_action"] = f"تم تسجيل عميل جديد: {phone}"
    return True


def search_tool(query):
    q = str(query or "").strip().lower()
    rows = [x for x in PRODUCTS if q in str(x).lower()]
    if not rows:
        rows = PRODUCTS[:3]
    STATE["last_action"] = f"بحث تجريبي عن: {q or 'الكل'}"
    return pd.DataFrame(rows)


def calculate_tool(product_name, quantity):
    try:
        qty = int(quantity)
    except Exception:
        return "الكمية يجب أن تكون رقمًا صحيحًا."
    if qty < 1 or qty > 10000:
        return "الكمية يجب أن تكون بين 1 و10000."
    for product in PRODUCTS:
        if product["Product Name"].casefold() == str(product_name).strip().casefold():
            total = product["Price"] * qty
            return f"المنتج: {product['Product Name']}\nسعر الوحدة: {product['Price']}\nالكمية: {qty}\nالإجمالي: {total}"
    return "المنتج غير موجود في البيانات التجريبية."


def inventory_tool():
    return pd.DataFrame([{k: p[k] for k in ("Product Name", "Stock", "Category")} for p in PRODUCTS])


def sales_report():
    return pd.DataFrame([
        {"date": "اليوم", "orders": 3, "revenue_preview": 845},
        {"date": "أمس", "orders": 2, "revenue_preview": 510},
        {"date": "قبل أمس", "orders": 4, "revenue_preview": 1120},
    ])


def upload_company_excel(file):
    if file is None:
        return "اختر ملف Excel أولًا."
    suffix = Path(str(file)).suffix.lower()
    if suffix not in {".xlsx", ".xlsm"}:
        return "صيغة الملف غير مدعومة."
    CONFIG["EXCEL_FILE"] = Path(str(file)).name
    CONFIG["SOURCE_TYPE"] = "excel"
    STATE["data_status"] = f"تم تحميل {CONFIG['EXCEL_FILE']} في وضع المعاينة"
    return "تم قبول الملف. في التشغيل الحقيقي سيتم تحديث البيانات وبناء الفهرس."


def connect_data_source(source_type, google_id, credentials):
    CONFIG["SOURCE_TYPE"] = source_type
    CONFIG["GOOGLE_SHEET_ID"] = google_id or ""
    CONFIG["GOOGLE_CREDENTIALS"] = credentials or "service_account.json"
    STATE["data_status"] = f"مصدر البيانات: {source_type} (معاينة)"
    return f"تم حفظ إعداد مصدر البيانات: {source_type}. لم يتم الاتصال الحقيقي في المعاينة."


def save_whatsapp_settings(token, phone_id, verify_token, app_secret, api_version):
    # Preview intentionally does not persist secrets or call Meta.
    CONFIG["PHONE_NUMBER_ID"] = phone_id or ""
    CONFIG["WA_API_VERSION"] = api_version or "vXX.X"
    STATE["whatsapp_status"] = "إعدادات تجريبية محفوظة في الذاكرة فقط"
    return "تم حفظ إعدادات المعاينة. لن يتم تخزين أو إرسال المفاتيح الحقيقية هنا."


def test_whatsapp_connection():
    return "اختبار تجريبي: ضع بيانات Meta الحقيقية في بيئة التشغيل ثم نفّذ اختبار الاتصال."


def apply_tool_permissions(search, calculate, support, orders, customer, inventory, report, broadcast):
    ENABLED_TOOLS.update({
        "search_company": search, "calculate_product": calculate,
        "create_support_ticket": support, "save_order_draft": orders,
        "customer_lookup": customer, "inventory_check": inventory,
        "sales_report": report, "broadcast_preview": broadcast,
    })
    return "تم تحديث صلاحيات الأدوات."


def start_whatsapp_ui():
    STATE["whatsapp_status"] = "وضع المعاينة فقط - WhatsApp غير متصل"
    return STATE["whatsapp_status"]


def stop_whatsapp_ui():
    STATE["whatsapp_status"] = "تم إيقاف وضع المعاينة"
    return STATE["whatsapp_status"]


def update_model(model):
    model = str(model).strip()
    if not model:
        return "اسم النموذج مطلوب."
    CONFIG["OLLAMA_MODEL"] = model
    return f"تم تغيير النموذج إلى {model} في المعاينة."


PREVIEW_EVENTS = [
    {"phone": "01000000000", "event_type": "product_view", "product_name": "Product A", "value": 1, "city": "القاهرة"},
    {"phone": "01000000000", "event_type": "order_created", "product_name": "Product A", "value": 120, "city": "القاهرة"},
    {"phone": "01000000001", "event_type": "product_view", "product_name": "Product B", "value": 1, "city": "الإسكندرية"},
    {"phone": "01000000001", "event_type": "support_ticket", "value": 1, "city": "الإسكندرية"},
    {"phone": "DASHBOARD_TEST_CUSTOMER", "event_type": "product_view", "value": 1, "city": "الجيزة"},
]


def mysql_preview_settings(host, port, database, user):
    CONFIG.update({"MYSQL_HOST": host or "127.0.0.1", "MYSQL_PORT": int(port or 3306), "MYSQL_DATABASE": database or "company_agent", "MYSQL_USER": user or "company_agent"})
    STATE["last_action"] = "تم حفظ إعدادات MySQL في الذاكرة فقط"
    return "تم حفظ الإعدادات للمعاينة. لن يتم الاتصال بقاعدة MySQL حقيقية من هذه الصفحة."


def preview_analytics(days=30):
    customers = pd.DataFrame(CUSTOMERS)
    events = pd.DataFrame(PREVIEW_EVENTS)
    products = pd.DataFrame(PRODUCTS)
    if customers.empty:
        empty = pd.DataFrame()
        return "لا توجد بيانات عملاء.", empty, empty, empty, empty, empty
    by_city = customers.groupby("city", dropna=False).agg(customers=("phone", "count"), messages=("messages", "sum")).reset_index().sort_values("customers", ascending=False)
    customer_table = customers[["phone", "name", "city", "messages", "last_seen"]].sort_values("messages", ascending=False)
    product_events = events[events["event_type"].isin(["product_view", "order_created"])].copy()
    product_table = products[["Product Name", "Category", "Price", "Stock", "Updated"]].copy()
    if product_events.empty:
        product_table["events"] = 0
        product_table["event_value"] = 0
    else:
        product_counts = product_events.groupby("product_name").agg(events=("event_type", "count"), event_value=("value", "sum")).reset_index()
        product_table = product_table.merge(product_counts, left_on="Product Name", right_on="product_name", how="left").drop(columns=["product_name"])
        product_table[["events", "event_value"]] = product_table[["events", "event_value"]].fillna(0)
    event_summary = events.groupby("event_type").agg(total=("phone", "count"), value=("value", "sum")).reset_index()
    time_table = pd.DataFrame([
        {"period": "اليوم", "messages": 24, "orders": 3, "tickets": 2, "peak": "10:00-12:00"},
        {"period": "أمس", "messages": 19, "orders": 2, "tickets": 1, "peak": "14:00-16:00"},
        {"period": "قبل أمس", "messages": 31, "orders": 4, "tickets": 3, "peak": "18:00-20:00"},
    ])
    total = len(customers)
    messages = int(customers["messages"].sum())
    recommendations = []
    if len(events[events["event_type"] == "product_view"]) > len(events[events["event_type"] == "order_created"]):
        recommendations.append("متابعة العملاء الذين شاهدوا المنتجات ولم ينشئوا طلبًا.")
    if len(events[events["event_type"] == "support_ticket"]) >= 1:
        recommendations.append("مراجعة تذاكر الدعم في الإسكندرية وتحسين الردود المتكررة.")
    if total and messages / total >= 8:
        recommendations.append("إعداد ردود تلقائية للأسئلة المتكررة لأن معدل التفاعل مرتفع.")
    if not recommendations:
        recommendations.append("الاستمرار في جمع البيانات؛ لا توجد إشارة حرجة في الفترة المحددة.")
    text = "تحليل تلقائي تجريبي\n" + "\n".join(f"- {item}" for item in recommendations)
    return text, customer_table, product_table, by_city, time_table, event_summary



PREVIEW_MONTHLY_SALES = pd.DataFrame([
    {"month": "2026-09", "orders": 8, "sales": 2140},
    {"month": "2026-10", "orders": 11, "sales": 3290},
    {"month": "2026-11", "orders": 9, "sales": 2475},
])
PREVIEW_PLACE_SALES = pd.DataFrame([
    {"place": "القاهرة", "orders": 12, "sales": 3860},
    {"place": "الإسكندرية", "orders": 8, "sales": 2140},
    {"place": "الجيزة", "orders": 5, "sales": 1905},
])
PREVIEW_CUSTOMER_PURCHASES = pd.DataFrame([
    {"phone": "01000000000", "customer": "عميل تجريبي 1", "orders": 6, "purchases": 1850},
    {"phone": "01000000001", "customer": "Test Customer", "orders": 2, "purchases": 420},
    {"phone": "DASHBOARD_TEST_CUSTOMER", "customer": "عميل لوحة التحكم", "orders": 1, "purchases": 250},
])


def admin_query(question, history):
    q = str(question or '').strip()
    if not q:
        return '', history
    low = q.casefold()
    total_customers = len(CUSTOMERS)
    top = PREVIEW_CUSTOMER_PURCHASES.sort_values(['purchases', 'orders'], ascending=False).iloc[0]
    top_place = PREVIEW_PLACE_SALES.sort_values('sales', ascending=False).iloc[0]
    total_sales = int(PREVIEW_MONTHLY_SALES['sales'].sum())
    recommendations = [
        'تابع العميل المميز بعرض مخصص للحفاظ عليه.',
        'ركز الحملات على القاهرة لأنها أعلى مكان في المبيعات.',
        'راقب نمو المبيعات شهريًا وراجع المنتجات ذات المشاهدات دون طلبات.',
    ]
    if any(x in q for x in ['اقتراح', 'توصي', 'إجراء', 'recommend', 'action']):
        answer = 'اقتراحات الإدارة:\n' + '\n'.join(f'- {x}' for x in recommendations)
    elif any(x in q for x in ['عدد العملاء', 'كم عميل', 'customers', 'customer count']):
        answer = f'عدد العملاء المسجلين حاليًا: {total_customers} عميل.'
    elif any(x in q for x in ['مميز', 'أعلى عميل', 'top customer', 'best customer']):
        answer = f"العميل المميز: {top['customer']}\nعدد طلباته: {int(top['orders'])}\nحجم مشترياته: {int(top['purchases']):,}"
    elif any(x in q for x in ['كل شهر', 'شهري', 'monthly', 'month']):
        answer = 'حجم المبيعات حسب الشهر:\n' + '\n'.join(f"- {r['month']}: {int(r['sales']):,} من {int(r['orders'])} طلبات" for _, r in PREVIEW_MONTHLY_SALES.iterrows())
    elif any(x in q for x in ['كل مكان', 'مكان', 'مدينة', 'place', 'city', 'location']):
        answer = 'حجم المبيعات حسب المكان:\n' + '\n'.join(f"- {r['place']}: {int(r['sales']):,} من {int(r['orders'])} طلبات" for _, r in PREVIEW_PLACE_SALES.iterrows())
        answer += f"\n\nأعلى مكان: {top_place['place']} بإجمالي {int(top_place['sales']):,}."
    elif any(x in q for x in ['إجمالي المبيعات', 'حجم المبيعات', 'total sales', 'sales']):
        answer = f'إجمالي المبيعات في البيانات التجريبية: {total_sales:,}.'
    else:
        answer = 'أستطيع الإجابة عن: عدد العملاء، العميل المميز وحجم مشترياته، أكثر مكان بيعًا، المبيعات الشهرية، المبيعات حسب المكان، والاقتراحات.'
    history = history or []
    history.extend([{'role': 'user', 'content': q}, {'role': 'assistant', 'content': answer}])
    STATE['last_action'] = f'سؤال إداري: {q[:60]}'
    return '', history

PREVIEW_ORDERS = pd.DataFrame([
    {"order_id": 1, "phone": "01000000000", "created_at": "2026-11-20T10:00:00Z", "amount": 850},
    {"order_id": 2, "phone": "01000000000", "created_at": "2026-10-18T12:00:00Z", "amount": 600},
    {"order_id": 3, "phone": "01000000001", "created_at": "2026-11-05T15:00:00Z", "amount": 420},
    {"order_id": 4, "phone": "DASHBOARD_TEST_CUSTOMER", "created_at": "2026-11-22T09:00:00Z", "amount": 250},
])
PREVIEW_ORDER_ITEMS = pd.DataFrame([
    {"order_id": 1, "product_name": "Product A"},
    {"order_id": 1, "product_name": "Product B"},
    {"order_id": 2, "product_name": "Product A"},
    {"order_id": 3, "product_name": "Product B"},
])


def marketing_recommendation_preview():
    try:
        from recommendation_engine import recommendation_report
        report = recommendation_report(PREVIEW_ORDERS, PREVIEW_ORDER_ITEMS, pd.DataFrame(PREVIEW_EVENTS), pd.DataFrame(PRODUCTS))
        rfm = report["rfm"].copy()
        actions = pd.DataFrame(report["actions"])
        rules = report["association_rules"].copy()
        if not actions.empty:
            actions["approval_required"] = actions["approval_required"].map({True: "نعم", False: "لا"})
        summary = "تم تشغيل RFM وتقسيم العملاء وتوقع الشراء وخطر التسرب وقواعد المنتجات المرتبطة.\n"
        summary += "الحملات لا تُرسل تلقائيًا؛ كل إجراء يحتاج موافقة بشرية."
        return summary, rfm, rules, actions
    except Exception as error:
        return f"تعذر تشغيل محرك التوصيات: {error}", pd.DataFrame(), pd.DataFrame(), pd.DataFrame()


with gr.Blocks(title="Company AI Agent Advanced Preview") as demo:
    gr.HTML("""<div id='main-header' dir='rtl'><h1>🤖 مركز التحكم المتقدم بالوكيل الذكي</h1><p>Company AI Agent Advanced Control Center</p><span>معاينة آمنة ببيانات تجريبية — لا توجد اتصالات حقيقية</span></div>""")
    with gr.Tab("📊 الرئيسية"):
        dashboard_view = gr.HTML(value=dashboard_html())
        refresh_dashboard = gr.Button("🔄 تحديث الإحصائيات", variant="primary")
        refresh_dashboard.click(dashboard_html, outputs=dashboard_view)
        with gr.Row():
            start_btn = gr.Button("▶ تشغيل واتساب", variant="primary")
            stop_btn = gr.Button("■ إيقاف واتساب", variant="stop")
        whatsapp_status = gr.Textbox(label="حالة الاتصال", value=STATE["whatsapp_status"], interactive=False)
        start_btn.click(start_whatsapp_ui, outputs=whatsapp_status)
        stop_btn.click(stop_whatsapp_ui, outputs=whatsapp_status)
        gr.Markdown("### حالة النظام\nالمعاينة تعمل ببيانات تجريبية. قبل الإنتاج أضف Ollama وMeta ومصدر البيانات من تبويب الإعدادات.")
    with gr.Tab("🧑‍💼 محادثة الإدارة"):
        gr.Markdown("## اسأل الوكيل عن أداء الشركة")
        gr.Markdown("يمكنك السؤال بالعربية أو الإنجليزية عن العملاء، المبيعات، الأماكن، الوقت، والاقتراحات التشغيلية.")
        admin_chatbot = gr.Chatbot(label="مساعد الإدارة", height=460)
        with gr.Row():
            admin_input = gr.Textbox(label="سؤال الإدارة", placeholder="كم عدد العملاء؟ من العميل المميز؟ ما أكثر مكان به بيع؟", scale=5)
            admin_send = gr.Button("اسأل", variant="primary", scale=1)
        admin_send.click(admin_query, [admin_input, admin_chatbot], [admin_input, admin_chatbot])
        admin_input.submit(admin_query, [admin_input, admin_chatbot], [admin_input, admin_chatbot])
        gr.Markdown("### جداول مرجعية للإدارة")
        gr.Dataframe(value=PREVIEW_CUSTOMER_PURCHASES, label="العملاء والمشتريات", interactive=False)
        gr.Dataframe(value=PREVIEW_MONTHLY_SALES, label="المبيعات الشهرية", interactive=False)
        gr.Dataframe(value=PREVIEW_PLACE_SALES, label="المبيعات حسب المكان", interactive=False)
    with gr.Tab("💬 المحادثات"):
        chatbot = gr.Chatbot(label="Company AI Assistant", height=480)
        with gr.Row():
            message_input = gr.Textbox(placeholder="اكتب سؤالك بالعربية أو الإنجليزية...", label="رسالتك", scale=5)
            send_btn = gr.Button("إرسال", variant="primary", scale=1)
        send_btn.click(chat_with_agent, [message_input, chatbot], [message_input, chatbot])
        message_input.submit(chat_with_agent, [message_input, chatbot], [message_input, chatbot])
    with gr.Tab("🎯 التوصيات التسويقية"):
        gr.Markdown("## توصيات تسويقية مبنية على بيانات المبيعات")
        gr.Markdown("RFM، تقسيم العملاء، المنتجات المرتبطة، احتمال الشراء، خطر التسرب، وإجراءات مقترحة بدرجة ثقة. الإرسال يحتاج موافقة بشرية.")
        rec_btn = gr.Button("تشغيل محرك التوصيات", variant="primary")
        rec_summary = gr.Textbox(label="حالة التحليل", lines=3)
        rec_rfm = gr.Dataframe(label="RFM وتقسيم العملاء", interactive=False)
        rec_rules = gr.Dataframe(label="المنتجات التي تُشترى معًا", interactive=False)
        rec_actions = gr.Dataframe(label="الإجراءات التسويقية المقترحة", interactive=False)
        rec_btn.click(marketing_recommendation_preview, outputs=[rec_summary, rec_rfm, rec_rules, rec_actions])
    with gr.Tab("🔧 الأدوات"):
        gr.Markdown("## أدوات تشغيلية إضافية")
        with gr.Row():
            search_query = gr.Textbox(label="بحث في بيانات الشركة", placeholder="Product A")
            search_btn = gr.Button("بحث", variant="primary")
        search_table = gr.Dataframe(label="نتائج البحث", interactive=False)
        search_btn.click(search_tool, search_query, search_table)
        with gr.Row():
            product_name = gr.Textbox(label="اسم المنتج", value="Product A")
            quantity = gr.Number(label="الكمية", value=2, precision=0)
            calc_btn = gr.Button("حساب الإجمالي", variant="primary")
        calc_result = gr.Textbox(label="نتيجة الحساب", lines=5)
        calc_btn.click(calculate_tool, [product_name, quantity], calc_result)
        inventory_btn = gr.Button("فحص المخزون")
        inventory_table = gr.Dataframe(label="المخزون", interactive=False)
        inventory_btn.click(inventory_tool, outputs=inventory_table)
        report_btn = gr.Button("تقرير المبيعات التجريبي")
        report_table = gr.Dataframe(label="التقرير", interactive=False)
        report_btn.click(sales_report, outputs=report_table)
    with gr.Tab("📁 البيانات"):
        gr.Markdown("## مصادر البيانات")
        source_type = gr.Radio(["excel", "google_sheets"], value="excel", label="مصدر البيانات")
        excel_upload = gr.File(label="ملف Excel", file_types=[".xlsx", ".xlsm"], type="filepath")
        google_id = gr.Textbox(label="Google Sheet ID")
        google_credentials = gr.Textbox(label="ملف الاعتماديات", value="service_account.json")
        connect_btn = gr.Button("حفظ مصدر البيانات", variant="primary")
        data_status = gr.Textbox(label="حالة المصدر", value=STATE["data_status"])
        connect_btn.click(connect_data_source, [source_type, google_id, google_credentials], data_status)
        upload_btn = gr.Button("رفع وتحديث Excel", variant="primary")
        upload_status = gr.Textbox(label="نتيجة الرفع")
        upload_btn.click(upload_company_excel, excel_upload, upload_status)
    with gr.Tab("👥 العملاء"):
        gr.Markdown("## بحث وإدارة العملاء")
        customer_search = gr.Textbox(label="رقم الهاتف أو الاسم")
        customer_btn = gr.Button("بحث عن عميل", variant="primary")
        customer_table = gr.Dataframe(value=get_customers(), label="العملاء", interactive=False)
        customer_btn.click(lambda q: get_customers()[get_customers().astype(str).apply(lambda row: row.str.contains(q or "", case=False).any(), axis=1)], customer_search, customer_table)
        customer_refresh = gr.Button("تحديث سجل العملاء")
        customer_refresh.click(get_customers, outputs=customer_table)
    with gr.Tab("🧠 الصلاحيات"):
        toggles = [gr.Checkbox(label=x, value=ENABLED_TOOLS[k]) for x, k in [
            ("البحث", "search_company"), ("حساب الأسعار", "calculate_product"), ("تذاكر الدعم", "create_support_ticket"),
            ("الطلبات المبدئية", "save_order_draft"), ("بحث العملاء", "customer_lookup"), ("فحص المخزون", "inventory_check"),
            ("تقارير المبيعات", "sales_report"), ("البث الجماعي - معاينة", "broadcast_preview")]]
        permissions_btn = gr.Button("حفظ الصلاحيات", variant="primary")
        permissions_status = gr.Textbox(label="النتيجة")
        permissions_btn.click(apply_tool_permissions, toggles, permissions_status)
    with gr.Tab("📈 التحليلات والتوصيات"):
        gr.Markdown("## إحصاءات العملاء والأماكن والتحليل التلقائي")
        gr.Markdown("هذه النتائج تجريبية من بيانات المعاينة. في التشغيل الحقيقي تُقرأ من MySQL.")
        analytics_days = gr.Number(label="عدد الأيام", value=30, precision=0)
        analytics_btn = gr.Button("تشغيل التحليل", variant="primary")
        analytics_summary = gr.Textbox(label="التوصيات المقترحة", lines=6)
        customer_analytics_table = gr.Dataframe(label="جدول العملاء والتفاعل", interactive=False)
        product_analytics_table = gr.Dataframe(label="جدول المنتجات والأسعار والمخزون", interactive=False)
        city_table = gr.Dataframe(label="جدول العملاء حسب المكان", interactive=False)
        time_table = gr.Dataframe(label="جدول الوقت والذروة", interactive=False)
        event_table = gr.Dataframe(label="جدول الأحداث وسلوك العملاء", interactive=False)
        analytics_btn.click(preview_analytics, analytics_days, [analytics_summary, customer_analytics_table, product_analytics_table, city_table, time_table, event_table])
        gr.Markdown("## إعداد اتصال MySQL للتحليلات المركزية")
        with gr.Row():
            mysql_host = gr.Textbox(label="MYSQL_HOST", value=CONFIG["MYSQL_HOST"])
            mysql_port = gr.Number(label="MYSQL_PORT", value=CONFIG["MYSQL_PORT"], precision=0)
        with gr.Row():
            mysql_database = gr.Textbox(label="MYSQL_DATABASE", value=CONFIG["MYSQL_DATABASE"])
            mysql_user = gr.Textbox(label="MYSQL_USER", value=CONFIG["MYSQL_USER"])
        mysql_save = gr.Button("حفظ إعدادات MySQL", variant="primary")
        mysql_status = gr.Textbox(label="الحالة")
        mysql_save.click(mysql_preview_settings, [mysql_host, mysql_port, mysql_database, mysql_user], mysql_status)

    with gr.Tab("⚙️ الإعدادات والتكاملات"):
        gr.Markdown("## إعدادات Ollama")
        model_name = gr.Textbox(label="اسم نموذج Ollama", value=CONFIG["OLLAMA_MODEL"])
        model_btn = gr.Button("تحديث النموذج", variant="primary")
        model_status = gr.Textbox(label="النتيجة")
        model_btn.click(update_model, model_name, model_status)
        gr.Markdown("## WhatsApp Cloud API\nأدخل القيم هنا عند تشغيل النسخة الحقيقية. المعاينة لا تحفظ الأسرار ولا تتصل بـ Meta.")
        token = gr.Textbox(label="WHATSAPP_TOKEN", type="password")
        phone_id = gr.Textbox(label="PHONE_NUMBER_ID")
        verify_token = gr.Textbox(label="WHATSAPP_VERIFY_TOKEN", type="password")
        app_secret = gr.Textbox(label="WHATSAPP_APP_SECRET", type="password")
        api_version = gr.Textbox(label="WA_API_VERSION", value="vXX.X")
        save_wa = gr.Button("حفظ إعدادات WhatsApp", variant="primary")
        wa_status = gr.Textbox(label="حالة الإعدادات")
        save_wa.click(save_whatsapp_settings, [token, phone_id, verify_token, app_secret, api_version], wa_status)
        test_wa = gr.Button("اختبار اتصال WhatsApp")
        test_wa_status = gr.Textbox(label="نتيجة الاختبار")
        test_wa.click(test_whatsapp_connection, outputs=test_wa_status)
        gr.JSON(value={"Provider": "Ollama", "Model": CONFIG["OLLAMA_MODEL"], "Data Source": CONFIG["SOURCE_TYPE"], "WhatsApp Port": 5000, "Mode": "Preview"}, label="Configuration")


demo.queue(default_concurrency_limit=4)
demo.launch(server_name="127.0.0.1", server_port=7860, share=False, quiet=True, theme=gr.themes.Soft(primary_hue="blue", secondary_hue="slate", neutral_hue="slate"), css=CUSTOM_CSS)
