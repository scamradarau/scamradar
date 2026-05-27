import anthropic
import json
import re
from datetime import datetime

# Load existing content.json, remove expired community alerts
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
 
client = anthropic.Anthropic()

response = client.messages.create(
    model="claude-haiku-4-5-20251001",
    max_tokens=1500,
    tools=[{"type": "web_search_20250305", "name": "web_search"}],
    system="""You are a scam intelligence analyst for Australia.
Search for the latest Australian scam alerts from official sources
(scamwatch.gov.au, accc.gov.au, asic.gov.au, afp.gov.au), Australian
news outlets, and Reddit (r/australia, r/AusFinance, r/scams).
Use at most 5 web searches total.
Return ONLY a raw JSON array, no markdown, no fences, no preamble.
Each object must have: id (unique string), title (original 2-3 sentence
summary max 300 chars, your own words), source (Scamwatch|ACCC|ASIC|AFP|News|Social),
category (Investment|Impersonation|Phishing|Romance|Crypto|Employment|Shopping|Other),
severity (HIGH|MEDIUM|LOW), date (ISO format with actual date and time), breaking (true|false).
For social media sourced reports, never name a specific company or individual,
describe the scam method only, and default to MEDIUM or LOW severity unless
corroborated by an official source.
Return 10-12 items. Write original summaries only.""",
    messages=[{
        "role": "user",
        "content": f"Search for the latest Australian scam alerts today {datetime.now().strftime('%B %Y')}."
    }]
)

text = "".join(block.text for block in response.content if hasattr(block, 'text'))
match = re.search(r'\[[\s\S]*\]', text)

if match:
    new_alerts = json.loads(match.group())
    community_alerts = [a for a in existing if a.get('source') == 'Community']
    final_alerts = community_alerts + new_alerts

    with open('content.json', 'w') as f:
        json.dump(final_alerts, f, indent=2)
    print(f"✅ content.json updated with {len(final_alerts)} alerts")

    # --- ARCHIVE: keep a growing history of every alert ---
    try:
        with open('archive.json', 'r') as f:
            archive = json.load(f)
    except:
        archive = []

    seen_titles = {a.get('title') for a in archive}
    today_iso = datetime.now().isoformat()

    for alert in final_alerts:
        if alert.get('title') not in seen_titles:
            entry = dict(alert)
            entry['first_seen'] = today_iso
            archive.append(entry)
            seen_titles.add(alert.get('title'))

    with open('archive.json', 'w') as f:
        json.dump(archive, f, indent=2)
    print(f"✅ archive.json now holds {len(archive)} total alerts")
else:
    print("❌ No valid JSON found in response")