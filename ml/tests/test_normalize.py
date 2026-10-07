from uvera_ml.serving.normalize import normalize_text


def test_clean_messages_unchanged():
    for t in ["Congratulations! You won Tk 50,000. Send Tk 3,000 fee to 01XXXXXXXXX",
              "আপনার বিকাশ অ্যাকাউন্টে ৫০,০০০ টাকা পুরস্কার জিতেছেন",
              "Bhai taka pathao, ami C008170 wallet e Tk3000 dibo", "Code 482913 kauke diben na"]:
        assert normalize_text(t) == t


def test_disguises_removed():
    assert normalize_text("pr​ize") == "prize"
    assert normalize_text("раyment") == "payment"  # Cyrillic look-alikes
    assert normalize_text("you w.o.n a p.r.i.z.e") == "you won a prize"
    assert normalize_text("you w0n a pr1ze") == "you won a prize"
    assert normalize_text("priiiize") == "priize"


def test_bengali_joiners_kept():
    t = "র‍য"
    assert normalize_text(t) == t
