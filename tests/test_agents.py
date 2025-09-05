from agents.price_suggestor import PriceSuggestorAgent, ProductInput
from agents.chat_moderator import ChatModerationAgent

def test_price_suggestor_basic():
    agent = PriceSuggestorAgent()
    p = ProductInput(
        id=1,
        title='iPhone 12',
        category='Mobile',
        brand='Apple',
        condition='Good',
        age_months=24,
        asking_price=35000,
        location='Mumbai'
    )
    out = agent.suggest(p)
    assert 'fair_price_range' in out
    assert out['fair_price_range']['min'] <= out['fair_price_range']['max']

def test_chat_moderator_phone_and_spam():
    mod = ChatModerationAgent()
    msg = 'Call me at 9876543210. Send rs.5000 to paytm.'
    res = mod.moderate(msg)
    assert 'contains_phone' in res['labels'] or 'payment_request' in res['labels']
