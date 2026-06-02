import anthropic
import json
import re
from datetime import datetime
def make_dedup_key(alert):
    """Generate a deduplication key based on the specific scam target/brand, not generic methods."""
    category = (alert.get('category') or '').lower().strip()
    title = (alert.get('title') or '').lower()

    # Only specific identifiable targets — brands, agencies, scam types
    # NOT generic delivery methods (sms, phone, phishing, etc.)
    specific_targets = [
        'ato', 'mygov', 'centrelink', 'medicare',
        'commonwealth bank', 'cba', 'nab', 'anz', 'westpac', 'ubank', 'macquarie', 'bendigo',
        'auspost', 'australia post',
        'telstra', 'optus', 'nbn',
        'qantas', 'virgin',
        'docusign', 'paypal', 'amazon', 'ebay', 'netflix',
        'revenue nsw', 'service nsw', 'transport nsw',
        'safe account', 'pig butchering', 'mule',
        'hi mum', 'wrong number',
        'age verification', 'under 16',
        'tax refund', 'toll', 'fine',
        'rug pull', 'defi', 'fake exchange',
        'romance scam', 'dating scam',
        'job scam', 'recruitment scam',
        'tinder swindler', 'investment seminar',
        'subpoena', 'arrest warrant'
    ]

    found = sorted({kw for kw in specific_targets if kw in title})

    # If we found specific targets, key on them. Otherwise fall back to category + first 40 chars of title.
    if found:
        return f"{category}::{':'.join(found)}"
    else:
        return f"{category}::{title[:40]}"
# Load existing content.json, remove expired community alerts
try:
    with open('content.json', 'r') as f:
        existing = json.load(f)
except:
    existing = []

now = datetime.now()

# Archive expiring community alerts before removing them
expiring_community = [
    a for a in existing
    if a.get('source') == 'Community' and a.get('expires')
    and datetime.fromisoformat(a['expires']) < now
]

if expiring_community:
    try:
        with open('archive.json', 'r') as f:
            archive_early = json.load(f)
    except:
        archive_early = []
    seen_early = {make_dedup_key(a) for a in archive_early}
for a in expiring_community:
    if make_dedup_key(a) not in seen_early:
        entry = dict(a)
        entry['first_seen'] = a.get('date', now.isoformat())
        archive_early.append(entry)
    with open('archive.json', 'w') as f:
        json.dump(archive_early, f, indent=2)
    print(f"✅ Archived {len(expiring_community)} expiring community alert(s)")

# Now remove expired community alerts from the live feed
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
    max_tokens=2500,
    tools=[{"type": "web_search_20250305", "name": "web_search"}],
    system="""You are a scam intelligence analyst for Australia.
Search for the latest Australian scam alerts from official sources
(scamwatch.gov.au, accc.gov.au, asic.gov.au, afp.gov.au), Australian
news outlets, and Reddit (r/australia, r/AusFinance, r/scams).
Use at most 5 web searches total.

Return ONLY a raw JSON array, no markdown, no fences, no preamble.

For each alert, write a substantive title (3-5 sentences, up to 500
chars) that includes:
- HOW the scam is delivered (channel, lure, typical script)
- WHO is being targeted
- WHAT the scammer is trying to extract (money, credentials, remote access)
- WHY this version is notable (new tactic, surge, official body
  involvement, big loss reported)

Avoid generic phrasing like 'scammers are targeting Australians' or
'be careful'. Write like a fraud analyst briefing a team: specific,
operational, useful.

Each object must have: id (unique string), title (as above),
source (Scamwatch|ACCC|ASIC|AFP|News|Social),
category (Investment|Impersonation|Phishing|Romance|Crypto|Employment|Shopping|Other),
severity (HIGH|MEDIUM|LOW), date (ISO format with actual date and time),
breaking (true|false).

For social media sourced reports, never name a specific company or
individual, describe the scam method only, and default to MEDIUM or
LOW severity unless corroborated by an official source.

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

    seen_keys = {make_dedup_key(a) for a in archive}
    today_iso = datetime.now().isoformat()

    for alert in final_alerts:
        key = make_dedup_key(alert)
        if key not in seen_keys:
            entry = dict(alert)
            entry['first_seen'] = today_iso
            archive.append(entry)
            seen_keys.add(key)

        with open('archive.json', 'w') as f:
            json.dump(archive, f, indent=2)
        print(f"✅ archive.json now holds {len(archive)} total alerts")
else:
    print("❌ No valid JSON found in response")