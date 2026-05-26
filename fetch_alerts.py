import anthropic
import json
import re
from datetime import datetime

client = anthropic.Anthropic()

response = client.messages.create(
    model="claude-opus-4-5",
    max_tokens=1500,
    tools=[{"type": "web_search_20250305", "name": "web_search"}],
    system="""You are a scam intelligence analyst for Australia. 
Search for the latest Australian scam alerts from linkedin, facebook, instagram, scamwatch.gov.au, 
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
    alerts = json.loads(match.group())
    with open('content.json', 'w') as f:
        json.dump(alerts, f, indent=2)
    print(f"✅ Updated content.json with {len(alerts)} alerts")
else:
    print("❌ No valid JSON found in response")