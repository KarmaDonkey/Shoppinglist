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

## Automatisk deploy

`.github/workflows/deploy-gustaf.yml` laddar upp `lambda_function.py` till
Lambda varje gång filen ändras på `main` (går också att köra för hand under
Actions → Deploy Gustaf → Run workflow). GitHub loggar in i AWS med OIDC –
inga AWS-nycklar sparas. Engångsinställning:

1. **IAM → Identity providers → Add provider**: OpenID Connect,
   URL `https://token.actions.githubusercontent.com`, audience `sts.amazonaws.com`.
2. **IAM → Roles → Create role → Web identity**: den providern, audience
   `sts.amazonaws.com`, GitHub organization `KarmaDonkey`, repository
   `Shoppinglist`, branch `main`. Hoppa över färdiga policyer, döp rollen till
   t.ex. `gustaf-deploy`.
3. På rollen: **Add permissions → Create inline policy → JSON**, med
   funktionens ARN (finns överst på Lambda-sidan) i stället för `FUNKTIONENS-ARN`:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [{
       "Effect": "Allow",
       "Action": ["lambda:UpdateFunctionCode", "lambda:GetFunctionConfiguration", "lambda:InvokeFunction"],
       "Resource": "FUNKTIONENS-ARN"
     }]
   }
   ```
4. **GitHub → repot → Settings → Secrets and variables → Actions → New
   repository secret**: `AWS_ROLE_ARN` = rollens ARN, `LAMBDA_FUNCTION_NAME` =
   funktionens namn.

Varje deploy avslutas med ett rökprov (en LaunchRequest, som bara hälsar och
inte rör listan).
