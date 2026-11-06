# Gustaf – Alexa-skill för Shoppinglistan

Röststyrd butler som lägger till varor på den gemensamma listan:
*"Alexa, ask butler Gustav to add eggs to Ica Maxi"* eller *"Alexa, open butler Gustav"*.

Kedjan: Alexa-skill → AWS Lambda (`lambda_function.py`) → Claude Haiku tolkar
frasen (vara, butik, antal) → skriver till samma Supabase-rad som appens
"Gemensam"-synk.

## Återskapa

**AWS Lambda**
- Region: Europe (Ireland) `eu-west-1` (Alexa kan bara anropa Lambda i
  N. Virginia, Ireland, Oregon och Tokyo – inte Stockholm).
- Runtime: Python 3.14, kod från `lambda_function.py` (bara standardbiblioteket,
  ingen paketering behövs).
- Timeout: 10 sek.
- Miljövariabler: `ANTHROPIC_API_KEY`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`,
  `SHARE_CODE` (de tre sista = fälten under ⚙ i appen).
- Trigger: Alexa, med Skill ID verification påslagen.

**Alexa Developer Console**
- Custom skill, English (US), "Provision your own".
- Interaction Model → JSON Editor: `interaction_model.json`.
- Endpoint: Lambda-funktionens ARN i Default Region.
- Starta med "open" eller "start" – inte "talk to", som Alexa tolkar som ett
  samtal till en kontakt.

Felsökning: Lambda → Monitor → CloudWatch logs visar `heard` (vad Alexa
uppfattade) och `parsed` (vad Claude gjorde av det) för varje anrop.
