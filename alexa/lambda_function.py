import json, os, random, urllib.request

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_ANON_KEY"]
SHARE_CODE = os.environ["SHARE_CODE"]
FALLBACK_STORE = "Osorterat"
SB_HEADERS = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}",
              "content-type": "application/json"}

def speak(text, end=True, reprompt=None):
    resp = {"shouldEndSession": end}
    if text:
        resp["outputSpeech"] = {"type": "PlainText", "text": text}
    if reprompt and not end:
        resp["reprompt"] = {"outputSpeech": {"type": "PlainText", "text": reprompt}}
    return {"version": "1.0", "response": resp}

def ask(text, reprompt="What shall I add to the list?"):
    return speak(text, end=False, reprompt=reprompt)

def lambda_handler(event, context):
    req = event["request"]
    if req["type"] == "LaunchRequest":
        return ask(random.choice([
            "Gustaf at your service. What shall I add to the list?",
            "Good day. Gustaf here. What may I add for you?",
            "You rang? What shall I put on the list?",
        ]))
    if req["type"] != "IntentRequest":
        return speak("")
    name = req["intent"]["name"]
    if name == "AddItemIntent":
        phrase = req["intent"].get("slots", {}).get("Phrase", {}).get("value")
        if not phrase:
            return ask("I beg your pardon, what shall I add?")
        try:
            return add_from_phrase(phrase)
        except Exception as e:
            print("Error:", repr(e))
            return speak("Terribly sorry, something went wrong on my end. Do try again in a moment.")
    if name == "AMAZON.HelpIntent":
        return ask("Simply tell me what you need and where. For example: add milk to Ica Maxi.")
    if name == "AMAZON.FallbackIntent":
        return ask("I'm afraid I can only help with the shopping list. Try saying: add milk to Ica Maxi.")
    return speak(random.choice(["Very good.", "As you wish.", "At your service, as always."]))

def add_from_phrase(phrase):
    data = load_list()
    stores = data["activeTrip"]["stores"]
    parsed = extract_item(phrase, [s["name"] for s in stores], known_items(data))
    print(json.dumps({"heard": phrase, "parsed": parsed}, ensure_ascii=False))
    if not parsed or not parsed.get("item"):
        return ask("My apologies, I didn't quite catch that. Could you say it again?")
    item = parsed["item"]
    store = next((s for s in stores if s["name"] == parsed.get("store")), None)
    if store is None:
        store = next((s for s in stores if s["name"].lower() == FALLBACK_STORE.lower()), None)
        if store is None:
            store = {"id": os.urandom(6).hex(), "name": FALLBACK_STORE, "items": [], "catOrder": []}
            stores.append(store)
        if parsed.get("heard_store"):
            message = (f"I'm afraid I couldn't find a shop called {parsed['heard_store']}, "
                       f"so I've put {item} under {FALLBACK_STORE} for now.")
        else:
            message = f"Very good. {item} has been added to {FALLBACK_STORE}."
    else:
        message = random.choice([
            f"Very good. {item} has been added to {store['name']}.",
            f"Certainly. I've put {item} on the {store['name']} list.",
            f"Consider it done. {item}, for {store['name']}.",
            f"Of course. {item} is on the list for {store['name']}.",
        ])
    store["items"].append({
        "id": os.urandom(6).hex(), "t": item, "qty": parsed.get("qty"),
        "cat": None, "by": "Gustaf", "d": False
    })
    save_list(data)
    return speak(message)

def known_items(data):
    names = []
    for trip in [data["activeTrip"]] + data.get("archive", []):
        for s in trip.get("stores", []):
            for it in s.get("items", []):
                t = (it.get("t") or "").strip()
                if t and t not in names:
                    names.append(t)
    return names[:300]

def extract_item(phrase, store_names, item_names):
    system = (
        "You turn a voice command into a shopping-list entry for a Swedish family.\n"
        "The text comes from Alexa's speech recognition, which is set to ENGLISH even though "
        "the family often says Swedish words. So Swedish words arrive as English-sounding "
        "nonsense (e.g. 'cannon bullar' or 'kernel bowler' for 'kanelbullar', 'flash' for "
        "'fläsk', 'feel mjolk' for 'filmjölk'). Work out what the person most plausibly said.\n"
        f"Existing stores: {json.dumps(store_names, ensure_ascii=False)}\n"
        f"Items this family has bought before: {json.dumps(item_names, ensure_ascii=False)}\n"
        "Respond with ONLY JSON: {\"store\": string|null, \"heard_store\": string|null, "
        "\"item\": string, \"qty\": string|null}.\n"
        "- store: copied EXACTLY from the existing stores list - the one the user most "
        "plausibly meant (store names are often misheard too, e.g. 'Ikea Maxi' for 'ICA Maxi'). "
        "Use null if no store was mentioned or none is a plausible match. Never invent a store name.\n"
        "- heard_store: the store name as you heard it, or null if none was mentioned.\n"
        "- item: if what was heard sounds like one of the items bought before, use that exact "
        "spelling. Otherwise the Swedish name of the grocery item with a capital first letter "
        "(e.g. 'milk' -> 'Mjölk', 'cinnamon buns' -> 'Kanelbullar').\n"
        "- qty: the quantity if one was said, else null."
    )
    body = json.dumps({
        "model": "claude-haiku-5-5",
        "max_tokens": 300,
        "system": system,
        "messages": [{"role": "user", "content": phrase}],
    }).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages", data=body, method="POST",
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2026-10-21",
            "content-type": "application/json",
        })
    result = json.loads(urllib.request.urlopen(req).read())
    text = "".join(b["text"] for b in result["content"] if b["type"] == "text")
    try:
        return json.loads(text)
    except ValueError:
        return None

def load_list():
    req = urllib.request.Request(
        f"{SUPABASE_URL}/rest/v1/lists?id=eq.{SHARE_CODE}&select=data", headers=SB_HEADERS)
    return json.loads(urllib.request.urlopen(req).read())[0]["data"]

def save_list(data):
    body = json.dumps({"data": data}).encode()
    req = urllib.request.Request(
        f"{SUPABASE_URL}/rest/v1/lists?id=eq.{SHARE_CODE}", data=body, method="PATCH",
        headers={**SB_HEADERS, "Prefer": "return=minimal"})
    urllib.request.urlopen(req)
