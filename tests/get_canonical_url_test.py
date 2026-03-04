import re
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

def get_canonical_url(url):
    parsed = urlparse(url)

    LANG_QUERY_KEYS = {'lang', 'hl', 'language', 'locale', 'l', 'ln', 'lingua'}
    LANG_CODE_PATTERN = re.compile(r'^(it|en|de|fr|es)$', re.IGNORECASE)

    # ── 1. Subdomain ──────────────────────────────────────────────────────────
    host = parsed.netloc.lower()
    host = re.sub(r':443$', '', host)
    host = re.sub(r':80$',  '', host)
    parts = host.split('.')
    if LANG_CODE_PATTERN.match(parts[0]):
        host = '.'.join(parts[1:])

    # ── 2. Path segments ──────────────────────────────────────────────────────
    segments = parsed.path.split('/')
    segments = [s for s in segments if s and not LANG_CODE_PATTERN.match(s)]
    path = '/' + '/'.join(segments) if segments else '/'

    # ── 3. File extension / underscore language suffix ────────────────────────
    path = re.sub(r'\.(it|en|de|fr|es)(\.[a-zA-Z]+)$', r'\2', path, flags=re.IGNORECASE)
    path = re.sub(r'_(it|en|de|fr|es)(\.[a-zA-Z]+)$',  r'\2', path, flags=re.IGNORECASE)

    # ── 4. Query parameters ───────────────────────────────────────────────────
    q_params = parse_qsl(parsed.query, keep_blank_values=True)
    filtered = [(k, v) for k, v in q_params if k.lower() not in LANG_QUERY_KEYS]
    new_query = urlencode(sorted(filtered))

    # ── 5. Fragment / hash ────────────────────────────────────────────────────
    fragment = parsed.fragment
    fragment = re.sub(r'[#!]*\/?(it|en|de|fr|es)\/?$',                         '',    fragment, flags=re.IGNORECASE)
    fragment = re.sub(r'(lang|hl|language|locale|l|ln)=(it|en|de|fr|es)(&|$)', r'\3', fragment, flags=re.IGNORECASE)
    fragment = re.sub(r'(lang|hl|language|locale|l|ln)=\s*(&|$)',              '',    fragment, flags=re.IGNORECASE)  # cleanup orfani
    fragment = fragment.strip('&#/!')

    return urlunparse((parsed.scheme, host, path, parsed.params, new_query, fragment))


# ── TEST SUITE ────────────────────────────────────────────────────────────────

test_groups = [
    {
        "label": "GROUP 1 — units.it (no subdomain)",
        "base": "https://units.it/ateneo",
        "cases": [
            ("https://en.units.it/ateneo",          "Subdomain"),
            ("https://units.it/ateneo?lang=it",     "Query param: lang"),
            ("https://units.it:443/ateneo?hl=es",   "Port + Query param: hl"),
            ("https://units.it/en/ateneo/",         "Trailing slash + Subdirectory"),
        ],
    },
    {
        "label": "GROUP 2 — portale.units.it",
        "base": "https://portale.units.it/ateneo",
        "cases": [
            ("https://en.portale.units.it/ateneo",              "Subdomain"),
            ("https://portale.units.it/ateneo?lang=it",         "Query param: lang"),
            ("https://portale.units.it:443/ateneo?hl=es",       "Port + Query param: hl"),
            ("https://portale.units.it/en/ateneo/",             "Trailing slash + Subdirectory"),
            ("https://portale.units.it/ateneo?language=fr",     "Query param: language"),
            ("https://portale.units.it/ateneo?locale=de",       "Query param: locale"),
            ("https://portale.units.it/ateneo?l=it",            "Query param: l"),
            ("https://portale.units.it/ateneo?ln=en",           "Query param: ln"),
            ("https://portale.units.it/ateneo/en/",             "Lang at end of path"),
            ("https://portale.units.it/ateneo#lang=it",         "Fragment: lang param"),
            ("https://portale.units.it/ateneo#!/it/",           "Fragment: hash-bang path"),
            ("https://portale.units.it/ateneo?id=5&lang=it",    "Lang mixed with real params — expects ?id=5")
        ],
    },
    {
        "label": "GROUP 3 — file suffix (each has its own expected canonical)",
        "base": None,  # checked individually
        "cases": [
            ("https://portale.units.it/pagina.en.html",  "File extension suffix"),
            ("https://portale.units.it/document_fr.pdf", "Filename underscore suffix"),
        ],
        "expected": [
            "https://portale.units.it/pagina.html",
            "https://portale.units.it/document.pdf",
        ],
    },
]

all_passed = True

for group in test_groups:
    print(f"\n{'─'*100}")
    print(f"  {group['label']}")
    print(f"{'─'*100}")
    print(f"  {'ORIGINAL URL':<55} | {'CANONICAL RESULT':<45} | STATUS")
    print(f"  {'─'*53} | {'─'*43} | ──────")

    canonicals = []
    for i, (url, desc) in enumerate(group["cases"]):
        canonical = get_canonical_url(url)
        canonicals.append(canonical)

        # Determine expected value
        if group["base"] is None:
            expected = group["expected"][i]
        elif "id=5" in url:
            expected = group["base"] + "?id=5"
        else:
            expected = group["base"]

        ok = canonical == expected
        if not ok:
            all_passed = False
        status = "✅" if ok else f"❌ expected: {expected}"
        print(f"  {url:<55} | {canonical:<45} | {status}")

print(f"\n{'═'*100}")
if all_passed:
    print("  ✅  ALL TESTS PASSED")
else:
    print("  ❌  SOME TESTS FAILED")
print(f"{'═'*100}\n")