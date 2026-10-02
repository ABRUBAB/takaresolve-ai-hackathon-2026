"""Synthetic scam / legit message corpus (Bangla, Banglish, English).

Two independent "style families": A is used for training, B is held out for testing (different wording and
structure), so the classifier cannot pass the test by memorising templates. Sources:
  1. seed templates + slot filling + noise (always available, offline)
  2. Gemini-generated messages (when GEMINI_API_KEY is set), with family-specific style prompts
Every message is machine-generated and fictional. No real people, numbers or brands.
"""
from __future__ import annotations

import random

import pandas as pd

SCAM = ["otp_reversal_counter", "fake_customer_care", "prize_lottery", "investment_group", "gold_jar_offer", "refund_government"]
LEGIT = ["payment_note", "bill_reminder", "family_request", "shop_promo", "official_otp_notice", "delivery_update"]
CLASSES = SCAM + ["legit"]
LANGS = ["bangla", "banglish", "english"]

# (class, language, family) -> template. Slots: {amount} {fee} {number} {name} {wallet} {code} {date} {time} {shop}
T = {
    # ---------------- scam, family A
    ("otp_reversal_counter", "english", "A"): "Sorry brother, I sent {amount} Tk to your number by mistake. Please send it back or tell me the code that just came to your phone.",
    ("otp_reversal_counter", "bangla", "A"): "ভাই, ভুল করে আপনার নম্বরে {amount} টাকা চলে গেছে। দয়া করে ফেরত পাঠান, অথবা এইমাত্র যে কোডটা গেছে সেটা বলুন।",
    ("otp_reversal_counter", "banglish", "A"): "Vai vul kore apnar number e {amount} taka chole gese. Plz ferot pathan, na hole je code ta gese ota bolen.",
    ("fake_customer_care", "english", "A"): "Dear customer, your {wallet} account will be blocked today. Call {number} and share the verification code to keep it active.",
    ("fake_customer_care", "bangla", "A"): "প্রিয় গ্রাহক, আপনার {wallet} অ্যাকাউন্ট আজ বন্ধ হয়ে যাবে। চালু রাখতে {number} নম্বরে কল করে ভেরিফিকেশন কোড দিন।",
    ("fake_customer_care", "banglish", "A"): "Priyo grahok, apnar {wallet} account aj block hobe. Chalu rakhte {number} e call kore verification code din.",
    ("prize_lottery", "english", "A"): "Congratulations! You won {amount} Tk in the lucky draw. Send {fee} Tk processing fee to {number} to receive it.",
    ("prize_lottery", "bangla", "A"): "অভিনন্দন! লটারিতে আপনি {amount} টাকা জিতেছেন। টাকা পেতে {number} নম্বরে {fee} টাকা প্রসেসিং ফি পাঠান।",
    ("prize_lottery", "banglish", "A"): "Ovinondon! Lucky draw te apni {amount} taka jitesen. Taka pete {number} e {fee} taka processing fee pathan.",
    ("investment_group", "english", "A"): "Join our online earning group. Invest {fee} Tk today and get {amount} Tk in 7 days. Profit is guaranteed.",
    ("investment_group", "bangla", "A"): "অনলাইনে আয়ের গ্রুপে যোগ দিন। আজ {fee} টাকা বিনিয়োগ করুন, ৭ দিনে পাবেন {amount} টাকা। লাভ নিশ্চিত।",
    ("investment_group", "banglish", "A"): "Online income group e join korun. Aj {fee} taka invest korle 7 dine paben {amount} taka. Profit 100% sure.",
    ("gold_jar_offer", "english", "A"): "A spiritual healer found a gold jar for your family. Send {fee} Tk for the ritual today or the blessing will be lost.",
    ("gold_jar_offer", "bangla", "A"): "একজন কবিরাজ আপনার পরিবারের জন্য সোনার কলস পেয়েছেন। আজই অনুষ্ঠানের খরচ {fee} টাকা না পাঠালে সব হারিয়ে যাবে।",
    ("gold_jar_offer", "banglish", "A"): "Ekjon kobiraj apnar paribar er jonno shonar kolosh peyesen. Aj {fee} taka na pathale shob hariye jabe.",
    ("refund_government", "english", "A"): "Your government allowance of {amount} Tk is pending. Send {fee} Tk service charge to {number} to release it today.",
    ("refund_government", "bangla", "A"): "আপনার সরকারি ভাতার {amount} টাকা আটকে আছে। আজই ছাড় পেতে {number} নম্বরে {fee} টাকা সার্ভিস চার্জ পাঠান।",
    ("refund_government", "banglish", "A"): "Apnar sorkari vatar {amount} taka atke ase. Aj chharte {number} e {fee} taka service charge pathan.",
    # ---------------- scam, family B (held-out style)
    ("otp_reversal_counter", "english", "B"): "hello?? {amount} taka went to u wrongly from my side 🙏 just read me the 6 digit msg pls, my boss will kill me",
    ("otp_reversal_counter", "bangla", "B"): "আপা প্লিজ রাগ করবেন না, দোকান থেকে {amount} টাকা ভুলে আপনার কাছে গেছে। মেসেজে যে নম্বরটা আসছে শুধু ওইটা পড়ে শোনান।",
    ("otp_reversal_counter", "banglish", "B"): "apa rag koiren na, dokan theke {amount} tk vule apnar kache gese... msg e je number ashse ota shudhu pore shonan",
    ("fake_customer_care", "english", "B"): "[{wallet} SUPPORT] Suspicious login detected!!! Verify within 30 min by replying with your PIN, else funds will be frozen.",
    ("fake_customer_care", "bangla", "B"): "আমি {wallet} অফিস থেকে বলছি। আপনার একাউন্টে সমস্যা ধরা পড়েছে, ঠিক করতে পিন নম্বরটা বলুন, নাহলে টাকা আটকে যাবে।",
    ("fake_customer_care", "banglish", "B"): "ami {wallet} office theke bolchi, apnar account e problem, thik korte PIN ta bolen naile taka atke jabe",
    ("prize_lottery", "english", "B"): "🎉 U R today's mega winner!! claim ur {amount} Tk + smartphone. tiny delivery charge {fee} Tk only, send now to agent {number}",
    ("prize_lottery", "bangla", "B"): "মোবাইল কোম্পানির ১০ম বর্ষপূর্তি উপলক্ষে আপনার নম্বর {amount} টাকা পুরস্কার পেয়েছে! ডেলিভারি চার্জ {fee} টাকা দিলেই পাবেন।",
    ("prize_lottery", "banglish", "B"): "mobile company r anniversary te apnar number {amount} tk puroshkar paise!! delivery charge {fee} tk dilei paben",
    ("investment_group", "english", "B"): "Sir my cousin doubled his money in 5 days with our crypto team. Minimum {fee} Tk. Admin {name} will add you. Seats limited!",
    ("investment_group", "bangla", "B"): "আমাদের টেলিগ্রাম টিমে মাত্র {fee} টাকা দিয়ে শুরু করুন, প্রতিদিন কমিশন। আমার মামা গত মাসে {amount} টাকা তুলেছেন।",
    ("investment_group", "banglish", "B"): "amader telegram team e matro {fee} tk diye start korun, protidin commission, amar mama gotomash e {amount} tk tulse",
    ("gold_jar_offer", "english", "B"): "Baba says your house has hidden treasure. Do not tell anyone. Pay {fee} Tk for the special prayer by tonight.",
    ("gold_jar_offer", "bangla", "B"): "বাবা বলেছেন আপনার বাড়ির নিচে গুপ্তধন আছে। কাউকে বলবেন না। আজ রাতের মধ্যে বিশেষ দোয়ার জন্য {fee} টাকা দিন।",
    ("gold_jar_offer", "banglish", "B"): "baba boleche apnar barir niche guptodhon ase. kauke bolben na. aj raate special doar jonno {fee} tk den",
    ("refund_government", "english", "B"): "Office notice: your stipend file is approved. Final step - deposit {fee} Tk file fee to officer {name} ({number}) to get {amount} Tk.",
    ("refund_government", "bangla", "B"): "উপবৃত্তির টাকা ছাড়ের জন্য আপনার নাম তালিকায় আছে। অফিসার {name}-কে {fee} টাকা ফাইল খরচ দিলে {amount} টাকা পাবেন।",
    ("refund_government", "banglish", "B"): "upobrittir taka charer list e apnar naam ase. officer {name} ke {fee} tk file khoroch dile {amount} tk paben",
    # ---------------- legit, family A
    ("payment_note", "english", "A"): "Sent {amount} Tk for this month's rent. Please confirm when you get it.",
    ("payment_note", "bangla", "A"): "এই মাসের ভাড়া {amount} টাকা পাঠালাম। পেলে জানিও।",
    ("payment_note", "banglish", "A"): "Ei maser bhara {amount} taka pathalam. Pele janio.",
    ("bill_reminder", "english", "A"): "Reminder: your electricity bill of {amount} Tk is due on {date}. Pay from the app's Pay Bill menu to avoid a late fee.",
    ("bill_reminder", "bangla", "A"): "স্মরণ করিয়ে দিচ্ছি: আপনার বিদ্যুৎ বিল {amount} টাকা, শেষ তারিখ {date}। দেরি ফি এড়াতে অ্যাপের পে বিল থেকে পরিশোধ করুন।",
    ("bill_reminder", "banglish", "A"): "Reminder: apnar biddut bill {amount} taka, shesh tarikh {date}. App er Pay Bill theke din.",
    ("family_request", "english", "A"): "Amma, please send {amount} Tk for my books this week. Exams start on Sunday.",
    ("family_request", "bangla", "A"): "আম্মা, এই সপ্তাহে বই কেনার জন্য {amount} টাকা পাঠাও। রবিবার থেকে পরীক্ষা।",
    ("family_request", "banglish", "A"): "Amma ei shoptahe boi kinar jonno {amount} taka pathao. Robibar theke porikkha.",
    ("shop_promo", "english", "A"): "Eid offer at {shop}: 10% off on all items until {date}. Pay with QR at the counter.",
    ("shop_promo", "bangla", "A"): "{shop}-এ ঈদ অফার: {date} পর্যন্ত সব পণ্যে ১০% ছাড়। কাউন্টারে কিউআর দিয়ে পেমেন্ট করুন।",
    ("shop_promo", "banglish", "A"): "{shop} e Eid offer: {date} porjonto shob product e 10% chhar. Counter e QR diye pay korun.",
    ("official_otp_notice", "english", "A"): "Your OTP is {code}. Never share it with anyone, not even our staff. We will never call you for it.",
    ("official_otp_notice", "bangla", "A"): "আপনার ওটিপি {code}। এটি কাউকে দেবেন না, আমাদের কর্মীদেরও না। আমরা কখনো ফোন করে কোড চাই না।",
    ("official_otp_notice", "banglish", "A"): "Apnar OTP {code}. Karo shathe share korben na, amader staff keo na.",
    ("delivery_update", "english", "A"): "Your parcel will arrive today between {time}. Cash on delivery: {amount} Tk.",
    ("delivery_update", "bangla", "A"): "আপনার পার্সেল আজ {time}-এর মধ্যে পৌঁছাবে। ক্যাশ অন ডেলিভারি: {amount} টাকা।",
    ("delivery_update", "banglish", "A"): "Apnar parcel aj {time} er moddhe pouchabe. Cash on delivery {amount} taka.",
    # ---------------- legit, family B (held-out style)
    ("payment_note", "english", "B"): "bro sent ur share for the trip, {amount} tk. check pls 👍",
    ("payment_note", "bangla", "B"): "দোস্ত, পিকনিকের চাঁদা {amount} টাকা দিলাম, দেখে নিস।",
    ("payment_note", "banglish", "B"): "dost picnic er chada {amount} tk dilam, dekhe nis",
    ("bill_reminder", "english", "B"): "Gas bill for {date}: {amount} Tk. You can pay it any time before the due date from your own app.",
    ("bill_reminder", "bangla", "B"): "গ্যাস বিল বাকি আছে {amount} টাকা। নিজের অ্যাপ থেকে {date}-এর আগে দিয়ে দিন।",
    ("bill_reminder", "banglish", "B"): "gas bill baki {amount} tk. nijer app theke {date} er age diye din",
    ("family_request", "english", "B"): "Bhaiya can u send {amount} for Ammu's medicine? pharmacy closes at 10",
    ("family_request", "bangla", "B"): "ভাইয়া, আম্মুর ওষুধের জন্য {amount} টাকা লাগবে, ফার্মেসি দশটায় বন্ধ হবে।",
    ("family_request", "banglish", "B"): "bhaiya ammur oshudh er jonno {amount} tk lagbe, pharmacy 10 tay bondho",
    ("shop_promo", "english", "B"): "New arrivals at {shop}!! buy 2 get 1 free this weekend only, visit us 🛍️",
    ("shop_promo", "bangla", "B"): "{shop}-এ নতুন কালেকশন এসেছে! এই সপ্তাহে দুইটা কিনলে একটা ফ্রি।",
    ("shop_promo", "banglish", "B"): "{shop} e notun collection ashse! ei week e duita kinle ekta free",
    ("official_otp_notice", "english", "B"): "{code} is your login code. It expires in 5 minutes. If you did not try to log in, ignore this message.",
    ("official_otp_notice", "bangla", "B"): "{code} আপনার লগইন কোড, ৫ মিনিটে মেয়াদ শেষ। আপনি চেষ্টা না করলে মেসেজটি উপেক্ষা করুন।",
    ("official_otp_notice", "banglish", "B"): "{code} apnar login code, 5 minute e meyad shesh. apni try na korle msg ta ignore korun",
    ("delivery_update", "english", "B"): "Rider here, I'm near your gate, {amount} tk COD for the order. pls come down",
    ("delivery_update", "bangla", "B"): "আমি ডেলিভারি থেকে বলছি, গেটের সামনে আছি। অর্ডারের {amount} টাকা ক্যাশে দিবেন।",
    ("delivery_update", "banglish", "B"): "ami delivery theke bolchi, gate er shamne asi. order er {amount} tk cash e diben",
}

NAMES = ["Rahim", "Karim", "Shila", "Mitu", "Rony", "Jahid", "Sumi", "Tanvir", "Rupa", "Hasan"]
WALLETS = ["your wallet", "PayDesk", "TakaGo", "e-Wallet"]
SHOPS = ["Rupali Store", "Nabil Fashion", "Moon Pharmacy", "City Mart", "Shapla Bazar"]
EMOJI = ["🙏", "😊", "‼️", "✅", "💰", "📞", "⚠️"]
BN_DIGITS = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")


def _fill(t: str, rng: random.Random, lang: str) -> str:
    amount = rng.choice([500, 1000, 1500, 2000, 2500, 3000, 5000, 7500, 10000, 15000, 25000, 50000])
    fee = rng.choice([200, 300, 500, 750, 1000, 1500, 2000])
    s = t.format(amount=f"{amount:,}", fee=f"{fee:,}", number="01" + "".join(rng.choice("3456789") for _ in range(2)) + "XXXXXXX",
                 name=rng.choice(NAMES), wallet=rng.choice(WALLETS), code=str(rng.randint(100000, 999999)),
                 date=f"{rng.randint(1, 28)}/{rng.randint(1, 12)}", time=rng.choice(["2-5 pm", "10 am-1 pm", "4-8 pm"]),
                 shop=rng.choice(SHOPS))
    if lang == "bangla" and rng.random() < 0.5:
        s = s.translate(BN_DIGITS)
    return s


def _noise(s: str, rng: random.Random) -> str:
    if rng.random() < 0.25:
        s = s + " " + rng.choice(EMOJI)
    if rng.random() < 0.15 and len(s) > 20:
        i = rng.randint(5, len(s) - 5)
        s = s[:i] + s[i + 1:]  # typo: dropped character
    if rng.random() < 0.10:
        s = s.upper() if rng.random() < 0.3 else s.lower()
    if rng.random() < 0.15:
        s = s.replace(".", "..").replace("।", "।।")
    return s


def template_corpus(per_template: int = 40, seed: int = 42) -> pd.DataFrame:
    rng = random.Random(seed)
    rows = []
    for (cls, lang, fam), t in T.items():
        for _ in range(per_template):
            label = cls if cls in SCAM else "legit"
            rows.append({"text": _noise(_fill(t, rng, lang), rng), "label": label, "subtype": cls, "language": lang,
                         "family": fam, "source": "template", "group": f"tpl:{cls}:{lang}:{fam}"})
    return pd.DataFrame(rows).drop_duplicates("text").reset_index(drop=True)


DESCRIPTIONS = {
    "otp_reversal_counter": "a person claims they sent money to the reader by mistake and asks them to send it back or read out a code (OTP)",
    "fake_customer_care": "someone pretends to be mobile-wallet customer care and says the account will be blocked unless the reader shares a PIN/OTP or calls a number",
    "prize_lottery": "a fake prize or lottery win that asks the reader to pay a small fee first",
    "investment_group": "an online earning/investment group promising fast guaranteed profit for a deposit",
    "gold_jar_offer": "a fake spiritual healer claims hidden gold/treasure and asks for money for a ritual",
    "refund_government": "a fake government allowance/stipend/refund that requires a service fee first",
    "payment_note": "an ordinary note sent with a normal money transfer (rent, shared costs, repayment)",
    "bill_reminder": "a normal utility bill reminder that tells the user to pay from their own app (no phone numbers to call)",
    "family_request": "a real family member asking for money for an everyday need (books, medicine, groceries)",
    "shop_promo": "a normal shop promotion or discount message",
    "official_otp_notice": "a genuine one-time-password message that warns the user never to share the code",
    "delivery_update": "a normal parcel delivery update with cash on delivery",
}
STYLE = {
    "A": "Typical SMS style: short (1-3 sentences), clear, mostly standard spelling.",
    "B": "Very different style from typical SMS templates: chat messages, call-script notes or social media DMs, with "
         "informal tone, occasional typos, emojis, abbreviations and Bangla-English code-mixing. Vary structure strongly.",
}
LANG_DESC = {"bangla": "Bangla written in Bengali script", "banglish": "Bangla written in Latin letters (Banglish)",
             "english": "simple English as used in Bangladesh"}
SYSTEM = ("You generate SYNTHETIC, fictional training data for a scam-detection classifier used to PROTECT customers of a "
          "mobile financial service in Bangladesh. Never use real company or brand names, real people or real phone numbers; "
          "use placeholder numbers like 01XXXXXXXXX and fictional names. Amounts are in Taka.")


def gemini_corpus(gemini, n_per_call: int = 50, calls_per_cell: int = 3, seed: int = 42, log_every: int = 10) -> pd.DataFrame:
    """Generate messages for every (subtype, language, family) cell. Failures are skipped and counted."""
    rows, cells, done = [], [(c, lg, f) for c in SCAM + LEGIT for lg in LANGS for f in ("A", "B")], 0
    for cls, lang, fam in cells:
        for k in range(calls_per_cell):
            prompt = (f"Write {n_per_call} different, realistic but fictional messages in {LANG_DESC[lang]}. "
                      f"Each message: {DESCRIPTIONS[cls]}. {STYLE[fam]} Variation seed: {seed}-{k}. "
                      f"Return a JSON list of strings only.")
            try:
                msgs = gemini.json(prompt, list[str], temperature=1.0, system=SYSTEM)
            except Exception as e:  # noqa: BLE001
                print(f"skip {cls}/{lang}/{fam}#{k}: {str(e)[:120]}")
                continue
            for m in msgs:
                if isinstance(m, str) and 8 <= len(m) <= 400:
                    rows.append({"text": m.strip(), "label": cls if cls in SCAM else "legit", "subtype": cls, "language": lang,
                                 "family": fam, "source": "gemini", "group": f"gem:{cls}:{lang}:{fam}:{k}"})
            done += 1
            if done % log_every == 0:
                print(f"{done} calls done, {len(rows)} messages")
    return pd.DataFrame(rows).drop_duplicates("text").reset_index(drop=True) if rows else pd.DataFrame(
        columns=["text", "label", "subtype", "language", "family", "source", "group"])


def load_uci_sms(path: str | None = None) -> pd.DataFrame:
    """UCI SMS Spam Collection (English, CC BY 4.0) for an EXTERNAL sanity test only (spam ~ scam-like vs ham)."""
    import io
    import urllib.request
    import zipfile
    from pathlib import Path

    candidates = [path] if path else [
        "/kaggle/input/sms-spam-collection-dataset/spam.csv",
        "/kaggle/input/sms-spam-collection/SMSSpamCollection",
    ]
    for p in candidates:
        if p and Path(p).exists():
            if p.endswith(".csv"):
                df = pd.read_csv(p, encoding="latin-1")[["v1", "v2"]].rename(columns={"v1": "y", "v2": "text"})
            else:
                df = pd.read_csv(p, sep="\t", header=None, names=["y", "text"], quoting=3)
            return df.assign(label=lambda d: (d["y"] == "spam").astype(int))[["text", "label"]]
    url = "https://archive.ics.uci.edu/static/public/228/sms+spam+collection.zip"
    with urllib.request.urlopen(url, timeout=60) as r:
        z = zipfile.ZipFile(io.BytesIO(r.read()))
    df = pd.read_csv(z.open("SMSSpamCollection"), sep="\t", header=None, names=["y", "text"], quoting=3)
    return df.assign(label=lambda d: (d["y"] == "spam").astype(int))[["text", "label"]]
