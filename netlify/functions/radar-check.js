exports.handler = async (event) => {
  if (event.httpMethod !== 'POST') {
    return { statusCode: 405, body: 'Method not allowed' };
  }

  try {
    const { answers, freeText } = JSON.parse(event.body);

    // Pull recent archive for pattern matching
    let archiveContext = '';
    try {
      const archiveRes = await fetch('https://scamradar.com.au/archive.json');
      const archive = await archiveRes.json();
      const recent = archive
        .sort((a, b) => new Date(b.first_seen || b.date) - new Date(a.first_seen || a.date))
        .slice(0, 30)
        .map(a => `- ${a.category}: ${a.title}`)
        .join('\n');
      archiveContext = recent;
    } catch (e) {
      archiveContext = '(archive unavailable)';
    }

    const userScenario = `
Contact method: ${answers.contact}
Claimed identity: ${answers.identity}
What they wanted: ${answers.ask}
Urgency/pressure used: ${answers.urgency}
Additional details: ${freeText || '(none)'}
`.trim();

    const systemPrompt = `You are Radar Check, ScamRadar AU's scam analysis system. A user has described a suspicious interaction. Analyse it for red flags and respond ONLY with a JSON object, no markdown fences, no preamble.

The JSON must have this exact shape:
{
  "risk_level": "HIGH" | "MEDIUM" | "LOW",
  "scam_type": "short label, e.g. Bank impersonation",
  "red_flags": ["concise red flag 1", "concise red flag 2", "..."],
  "matches_recent_pattern": true | false,
  "matching_pattern_summary": "one short sentence if matches_recent_pattern is true, else empty string",
  "what_to_do": ["action 1", "action 2", "action 3"],
  "summary": "2-3 sentence plain English explanation"
}

Rules:
- ERR TOWARDS HIGH RISK. If anything is suspicious, rate HIGH or MEDIUM. Only rate LOW if there is genuinely nothing concerning.
- Compare to the recent archive patterns below. If the scenario clearly matches one, set matches_recent_pattern to true and write a one-sentence summary.
- Red flags should be specific to this scenario, not generic.
- "what_to_do" should be concrete actions, not vague advice.
- Recent Australian scam patterns from our archive:
${archiveContext}`;

    const apiRes = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': process.env.ANTHROPIC_API_KEY,
        'anthropic-version': '2023-06-01'
      },
      body: JSON.stringify({
        model: 'claude-haiku-4-5-20251001',
        max_tokens: 800,
        system: systemPrompt,
        messages: [{ role: 'user', content: userScenario }]
      })
    });

    const data = await apiRes.json();
    const text = (data.content || []).map(b => b.text || '').join('');
    const match = text.match(/\{[\s\S]*\}/);
    if (!match) throw new Error('No JSON in response');
    const result = JSON.parse(match[0]);

    return {
      statusCode: 200,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(result)
    };
  } catch (e) {
    return {
      statusCode: 500,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ error: e.message })
    };
  }
};