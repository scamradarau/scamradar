import anthropic
import json
import re
from datetime import datetime

# Load existing content.json and remove expired community alerts
try:
    with open('content.json', 'r') as f:
        existing = json.load(f)
except:
    existing = []

now = datetime.now()
existing = [
    a for a in existing
    if not (
        a.get('source') == 'Community' and
        a.get('expires') and
        datetime.fromisoformat(a['expires']) < now
    )
]

# Fetch new alerts from Anthropic
client = anthropic.Anthropic()

response = client.messages.create(
    model="claude-opus-4-5",
    max_tokens=1500,
    tools=[{"type": "web_search_20250305", "name": "web_search"}],
    system="""You are a scam intelligence analyst for Australia. 
Search for the latest Australian scam alerts from scamwatch.gov.au, 
accc.gov.au, asic.gov.au, afp.gov.au and Australian news outlets today.
Return ONLY a raw JSON array, no markdown, no fences, no preamble.
Each object must have: id (unique string), title (original 1-2 sentence 
summary max 130 chars, your own words), source (Scamwatch|ACCC|ASIC|AFP|News), 
category (Investment|Impersonation|Phishing|Romance|Crypto|Employment|Shopping|Other), 
severity (HIGH|MEDIUM|LOW), date (e.g. May 2026), breaking (true|false).
Return 10-12 items. Write original summaries only.""",
    messages=[{
        "role": "user",
        "content": f"Search for the latest Australian scam alerts and fraud warnings today {datetime.now().strftime('%B %Y')}. Include results from scamwatch.gov.au, accc.gov.au, asic.gov.au and major Australian news."
    }]
)

# Extract text from response
text = "".join(block.text for block in response.content if hasattr(block, 'text'))

# Find JSON array in response
match = re.search(r'\[[\s\S]*\]', text)
if match:
    new_alerts = json.loads(match.group())

    # Keep unexpired community alerts and add new AI alerts
    community_alerts = [a for a in existing if a.get('source') == 'Community']
    final_alerts = community_alerts + new_alerts

    with open('content.json', 'w') as f:
        json.dump(final_alerts, f, indent=2)
    print(f"✅ Updated content.json with {len(final_alerts)} alerts")
else:
    print("❌ No valid JSON found in response")