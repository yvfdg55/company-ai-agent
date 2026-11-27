import hashlib
import hmac

from app.channels.whatsapp import WhatsAppChannel
from app.data.company import CompanyDataStore


def test_company_store_searches_tokens():
    store = CompanyDataStore([{"Product Name": "Product A", "Price": 10}])
    assert store.search("ما سعر Product A")


def test_whatsapp_signature_and_parse():
    channel = WhatsAppChannel("token", "phone-id", "secret")
    raw = b'{"object":"whatsapp_business_account"}'
    signature = "sha256=" + hmac.new(b"secret", raw, hashlib.sha256).hexdigest()
    assert channel.verify_signature(raw, signature)
    body = {"object": "whatsapp_business_account", "entry": [{"changes": [{"value": {"metadata": {"phone_number_id": "phone-id"}, "messages": [{"id": "m1", "from": "201", "type": "text", "text": {"body": "hello"}}]}}]}]}
    assert channel.parse_messages(body)[0].phone == "201"
