import random

VERBS = [
    ("be", "was/were", "been", "быть"),
    ("bear", "bore", "born", "нести, рождать"),
    ("beat", "beat", "beaten", "бить"),
    ("become", "became", "become", "становиться"),
    ("begin", "began", "begun", "начинать"),
    ("bend", "bent", "bent", "гнуть"),
    ("bet", "bet", "bet", "держать пари"),
    ("bind", "bound", "bound", "связывать"),
    ("bite", "bit", "bitten", "кусать"),
    ("bleed", "bled", "bled", "кровоточить"),
    ("blow", "blew", "blown", "дуть"),
    ("break", "broke", "broken", "ломать"),
    ("breed", "bred", "bred", "разводить"),
    ("bring", "brought", "brought", "приносить"),
    ("build", "built", "built", "строить"),
    ("burn", "burnt/burned", "burnt/burned", "гореть, жечь"),
    ("burst", "burst", "burst", "взрываться"),
    ("buy", "bought", "bought", "покупать"),
    ("catch", "caught", "caught", "ловить"),
    ("choose", "chose", "chosen", "выбирать"),
    ("come", "came", "come", "приходить"),
    ("cost", "cost", "cost", "стоить"),
    ("creep", "crept", "crept", "ползать"),
    ("cut", "cut", "cut", "резать"),
    ("deal", "dealt", "dealt", "иметь дело"),
    ("dig", "dug", "dug", "копать"),
    ("do", "did", "done", "делать"),
    ("draw", "drew", "drawn", "рисовать, тащить"),
    ("dream", "dreamt/dreamed", "dreamt/dreamed", "мечтать, видеть сны"),
    ("drink", "drank", "drunk", "пить"),
    ("drive", "drove", "driven", "водить, ехать"),
    ("eat", "ate", "eaten", "есть"),
    ("fall", "fell", "fallen", "падать"),
    ("feed", "fed", "fed", "кормить"),
    ("feel", "felt", "felt", "чувствовать"),
    ("fight", "fought", "fought", "бороться, драться"),
    ("find", "found", "found", "находить"),
    ("flee", "fled", "fled", "убегать, спасаться"),
    ("fly", "flew", "flown", "летать"),
    ("forbid", "forbade", "forbidden", "запрещать"),
    ("forget", "forgot", "forgotten", "забывать"),
    ("forgive", "forgave", "forgiven", "прощать"),
    ("freeze", "froze", "frozen", "замерзать"),
    ("get", "got", "got/gotten", "получать"),
    ("give", "gave", "given", "давать"),
    ("go", "went", "gone", "идти"),
    ("grow", "grew", "grown", "расти"),
    ("hang", "hung", "hung", "вешать, висеть"),
    ("have", "had", "had", "иметь"),
    ("hear", "heard", "heard", "слышать"),
    ("hide", "hid", "hidden", "прятать"),
    ("hit", "hit", "hit", "ударять"),
    ("hold", "held", "held", "держать"),
    ("hurt", "hurt", "hurt", "ранить, болеть"),
    ("keep", "kept", "kept", "хранить, держать"),
    ("kneel", "knelt", "knelt", "стоять на коленях"),
    ("know", "knew", "known", "знать"),
    ("lay", "laid", "laid", "класть"),
    ("lead", "led", "led", "вести"),
    ("lean", "leant/leaned", "leant/leaned", "опираться"),
    ("learn", "learnt/learned", "learnt/learned", "учить"),
    ("leave", "left", "left", "оставлять, уходить"),
    ("lend", "lent", "lent", "одалживать"),
    ("let", "let", "let", "позволять"),
    ("lie", "lay", "lain", "лежать"),
    ("light", "lit", "lit", "зажигать"),
    ("lose", "lost", "lost", "терять"),
    ("make", "made", "made", "делать, создавать"),
    ("mean", "meant", "meant", "значить"),
    ("meet", "met", "met", "встречать"),
    ("pay", "paid", "paid", "платить"),
    ("put", "put", "put", "класть"),
    ("quit", "quit", "quit", "бросать"),
    ("read", "read", "read", "читать"),
    ("ride", "rode", "ridden", "ездить верхом"),
    ("ring", "rang", "rung", "звонить"),
    ("rise", "rose", "risen", "подниматься"),
    ("run", "ran", "run", "бежать"),
    ("say", "said", "said", "сказать"),
    ("see", "saw", "seen", "видеть"),
    ("seek", "sought", "sought", "искать"),
    ("sell", "sold", "sold", "продавать"),
    ("send", "sent", "sent", "посылать"),
    ("set", "set", "set", "устанавливать"),
    ("shake", "shook", "shaken", "трясти"),
    ("shine", "shone", "shone", "сиять"),
    ("shoot", "shot", "shot", "стрелять"),
    ("show", "showed", "shown", "показывать"),
    ("shut", "shut", "shut", "закрывать"),
    ("sing", "sang", "sung", "петь"),
    ("sink", "sank", "sunk", "тонуть"),
    ("sit", "sat", "sat", "сидеть"),
    ("sleep", "slept", "slept", "спать"),
    ("slide", "slid", "slid", "скользить"),
    ("smell", "smelt/smelled", "smelt/smelled", "пахнуть, нюхать"),
    ("speak", "spoke", "spoken", "говорить"),
    ("spell", "spelt/spelled", "spelt/spelled", "писать по буквам"),
    ("spend", "spent", "spent", "тратить"),
    ("spill", "spilt/spilled", "spilt/spilled", "проливать"),
    ("split", "split", "split", "раскалывать"),
    ("spread", "spread", "spread", "распространять"),
    ("stand", "stood", "stood", "стоять"),
    ("steal", "stole", "stolen", "красть"),
    ("stick", "stuck", "stuck", "приклеивать"),
    ("sting", "stung", "stung", "жалить"),
    ("strike", "struck", "struck", "ударять, бастовать"),
    ("swear", "swore", "sworn", "клясться"),
    ("sweep", "swept", "swept", "подметать"),
    ("swim", "swam", "swum", "плавать"),
    ("swing", "swung", "swung", "качаться"),
    ("take", "took", "taken", "брать"),
    ("teach", "taught", "taught", "учить, обучать"),
    ("tear", "tore", "torn", "рвать"),
    ("tell", "told", "told", "рассказывать"),
    ("think", "thought", "thought", "думать"),
    ("throw", "threw", "thrown", "бросать"),
    ("understand", "understood", "understood", "понимать"),
    ("wake", "woke", "woken", "просыпаться"),
    ("wear", "wore", "worn", "носить (одежду)"),
    ("weep", "wept", "wept", "плакать"),
    ("win", "won", "won", "выигрывать"),
    ("wind", "wound", "wound", "заводить, наматывать"),
    ("write", "wrote", "written", "писать"),
]

PAGE_SIZE = 25


def pages() -> int:
    return (len(VERBS) + PAGE_SIZE - 1) // PAGE_SIZE


def format_verb(verb: tuple[str, str, str, str]) -> str:
    return f"{verb[0]} — {verb[1]} — {verb[2]} ({verb[3]})"


def page(number: int) -> str:
    chunk = VERBS[number * PAGE_SIZE:(number + 1) * PAGE_SIZE]
    lines = [f"Неправильные глаголы, стр. {number + 1}/{pages()}", "V1 — V2 (Past) — V3 (Participle)", ""]
    return "\n".join(lines + [format_verb(v) for v in chunk])


def find(query: str) -> list[tuple[str, str, str, str]]:
    key = query.strip().casefold()
    return [v for v in VERBS if any(key in part.casefold().split("/") for part in v[:3]) or key in v[3].casefold()]


def random_verb() -> int:
    return random.randrange(len(VERBS))


def check(index: int, answer: str) -> bool:
    verb = VERBS[index]
    parts = answer.replace(",", " ").replace("—", " ").replace("-", " ").split()
    if len(parts) != 2:
        return False
    return parts[0].casefold() in verb[1].split("/") and parts[1].casefold() in verb[2].split("/")
