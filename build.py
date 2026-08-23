from pathlib import Path
import shutil
import re
import html
import os
import json


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "inhalte"
OUTPUT = ROOT / "hosted_website"
MAIN_CSS = ROOT / "kurse.css"


# ============================================================
# Anzeigenamen
# ============================================================

SPECIAL_NAMES = {
    "klasse7": "Klasse 7",
    "klasse8": "Klasse 8",
    "klasse9": "Klasse 9",
    "klasse10": "Klasse 10",
    "sek2": "Sekundarstufe II",
}


def pretty_name(name):
    stem = Path(name).stem

    if stem in SPECIAL_NAMES:
        return SPECIAL_NAMES[stem]

    stem = stem.replace("-", " ")
    stem = stem.replace("_", " ")

    return stem[:1].upper() + stem[1:]


# ============================================================
# Sortierung der Ordner
# ============================================================

def folder_sort_key(path):
    order = {
        "klasse7": 1,
        "klasse8": 2,
        "klasse9": 3,
        "klasse10": 4,
        "sek2": 5,
    }

    if path.name in order:
        return (0, order[path.name])

    return (1, pretty_name(path.name).lower())


# ============================================================
# Titel einer HTML-Datei auslesen
# ============================================================

def get_html_title(path):
    try:
        text = path.read_text(
            encoding="utf-8",
            errors="replace"
        )

        match = re.search(
            r"<title[^>]*>(.*?)</title>",
            text,
            flags=re.IGNORECASE | re.DOTALL
        )

        if match:
            title = re.sub(
                r"<[^>]+>",
                "",
                match.group(1)
            )

            title = html.unescape(title).strip()

            if title:
                return title

    except Exception:
        pass

    return pretty_name(path.name)


# ============================================================
# Relative URL erzeugen
# ============================================================

def relative_url(from_dir, target):
    rel = os.path.relpath(target, from_dir)
    return rel.replace("\\", "/")


# ============================================================
# Standalone-HTML-Seite bearbeiten
# ============================================================

def process_html(source_file, output_file):
    text = source_file.read_text(
        encoding="utf-8",
        errors="replace"
    )

    out_dir = output_file.parent

    css_link = relative_url(
        out_dir,
        OUTPUT / "kurse.css"
    )

    portal_link = relative_url(
        out_dir,
        OUTPUT / "index.html"
    )

    back_link = "index.html"

    stylesheet = (
        f'<link rel="stylesheet" '
        f'href="{css_link}" '
        f'data-lernportal-style>'
    )

    navbar = f'''
<nav class="lp-navbar">
    <a class="lp-back" href="{back_link}">&larr; Zur&uuml;ck</a>
    <a class="lp-home" href="{portal_link}">Lernportal</a>
</nav>
'''

    # CSS-Link vor </head> einfügen
    if re.search(
        r"</head\s*>",
        text,
        flags=re.IGNORECASE
    ):
        text = re.sub(
            r"</head\s*>",
            stylesheet + "\n</head>",
            text,
            count=1,
            flags=re.IGNORECASE
        )
    else:
        text = stylesheet + "\n" + text

    # Navbar direkt nach <body>
    body_match = re.search(
        r"<body[^>]*>",
        text,
        flags=re.IGNORECASE
    )

    if body_match:
        pos = body_match.end()

        text = (
            text[:pos]
            + "\n"
            + navbar
            + text[pos:]
        )
    else:
        text = navbar + text

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    output_file.write_text(
        text,
        encoding="utf-8"
    )


# ============================================================
# Breadcrumb erzeugen
# ============================================================

def breadcrumb(current_source_dir, current_output_dir):
    relative = current_source_dir.relative_to(SOURCE)

    crumbs = []

    home_link = relative_url(
        current_output_dir,
        OUTPUT / "index.html"
    )

    crumbs.append(
        f'<a href="{home_link}">Lernportal</a>'
    )

    path_so_far = SOURCE

    for part in relative.parts:
        path_so_far = path_so_far / part

        target_output = (
            OUTPUT
            / path_so_far.relative_to(SOURCE)
            / "index.html"
        )

        link = relative_url(
            current_output_dir,
            target_output
        )

        crumbs.append(
            f'<a href="{link}">'
            f'{html.escape(pretty_name(part))}'
            f'</a>'
        )

    return (
        '<span class="lp-separator">'
        '&rsaquo;'
        '</span>'
    ).join(crumbs)



# ============================================================
# PDF-Hilfsfunktionen
# ============================================================

def is_learning_file(path):
    return (
        path.is_file()
        and path.suffix.lower() in (".html", ".htm", ".pdf")
        and not (
            path.suffix.lower() in (".html", ".htm")
            and path.stem.lower() == "index"
        )
    )


def learning_title(path):
    if path.suffix.lower() in (".html", ".htm"):
        return get_html_title(path)
    return pretty_name(path.name)


def pdf_wrapper_name(path):
    return f"{path.stem}-pdf.html"


def learning_output_path(source_file):
    relative = source_file.relative_to(SOURCE)
    if source_file.suffix.lower() == ".pdf":
        return OUTPUT / relative.parent / pdf_wrapper_name(source_file)
    return OUTPUT / relative


def learning_href(source_file, current_output_dir):
    return relative_url(current_output_dir, learning_output_path(source_file))


def create_pdf_viewer(source_pdf, output_pdf):
    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_pdf, output_pdf)

    wrapper = output_pdf.parent / pdf_wrapper_name(source_pdf)
    css_link = relative_url(wrapper.parent, OUTPUT / "kurse.css")
    pdf_link = output_pdf.name
    title = learning_title(source_pdf)

    document = f"""<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(title)}</title>
    <link rel="stylesheet" href="{css_link}">
</head>
<body class="lp-pdf-page">
    <main class="lp-pdf-shell">
        <nav class="lp-pdf-navbar">
            <a class="lp-nav-back" href="index.html" aria-label="Zurück" title="Zurück">&larr;</a>
            <div class="lp-pdf-title">{html.escape(title)}</div>
            <a class="lp-pdf-download" href="{html.escape(pdf_link)}" download>
                <span aria-hidden="true">&#8681;</span>
                <span>PDF herunterladen</span>
            </a>
        </nav>

        <div class="lp-pdf-viewer">
            <iframe
                src="{html.escape(pdf_link)}#view=FitH"
                title="{html.escape(title)}"
                loading="eager"
            ></iframe>
            <p class="lp-pdf-fallback">
                Falls das PDF hier nicht angezeigt wird,
                <a href="{html.escape(pdf_link)}">öffne es direkt</a>.
            </p>
        </div>
    </main>
</body>
</html>
"""
    wrapper.write_text(document, encoding="utf-8")


# ============================================================
# Globaler Suchindex
# ============================================================

def build_search_index(current_output_dir):
    entries = []

    for page in SOURCE.rglob("*"):
        if not is_learning_file(page):
            continue

        if "img" in [
            part.lower()
            for part in page.relative_to(SOURCE).parts
        ]:
            continue

        relative_source = page.relative_to(SOURCE)
        url = learning_href(page, current_output_dir)
        title = learning_title(page)

        location_parts = [
            pretty_name(part)
            for part in relative_source.parts[:-1]
            if part.lower() != "img"
        ]
        location = " › ".join(location_parts)

        entries.append({
            "title": title,
            "url": url,
            "location": location,
        })

    entries.sort(
        key=lambda item: (
            item["title"].lower(),
            item["location"].lower()
        )
    )
    return entries


# ============================================================
# Indexseite eines Ordners erzeugen
# ============================================================

def create_index(source_dir, output_dir):
    relative = source_dir.relative_to(SOURCE)

    if relative.parts:
        title = pretty_name(relative.parts[-1])
    else:
        title = "Lernportal"

    folders = sorted(
        [
            item
            for item in source_dir.iterdir()
            if item.is_dir()
            and not item.name.startswith(".")
            and item.name.lower() != "img"
        ],
        key=folder_sort_key
    )

    page_files = sorted(
        [
            item
            for item in source_dir.iterdir()
            if is_learning_file(item)
        ],
        key=lambda x: learning_title(x).lower()
    )

    cards = []

    # Auf Klassenebene: Lernbereiche als Überschriften,
    # darunter die enthaltenen HTML-Seiten.
    if len(relative.parts) == 1:
        for folder in folders:
            folder_pages = sorted(
                [
                    item
                    for item in folder.iterdir()
                    if is_learning_file(item)
                ],
                key=lambda x: learning_title(x).lower()
            )

            section_parts = [
                f'''
<div class="lp-section">
    <h2 class="lp-section-title">{html.escape(pretty_name(folder.name))}</h2>
    <div class="lp-section-pages">
'''
            ]

            if folder_pages:
                for page in folder_pages:
                    title_page = learning_title(page)
                    page_href = learning_href(page, output_dir)
                    section_parts.append(
                        f'''
<a class="lp-card lp-page" href="{page_href}">
    <span class="lp-card-text">
        <span class="lp-card-title">{html.escape(title_page)}</span>
    </span>
    <span class="lp-arrow">&rarr;</span>
</a>
'''
                    )
            else:
                section_parts.append(
                    '''
<div class="lp-section-empty">
    Noch keine Lernseiten hinterlegt.
</div>
'''
                )

            section_parts.append(
                '''
    </div>
</div>
'''
            )
            cards.append("".join(section_parts))

    else:
        for folder in folders:
            cards.append(
                f'''
<a class="lp-card lp-folder" href="{folder.name}/">
    <span class="lp-card-text">
        <span class="lp-card-title">{html.escape(pretty_name(folder.name))}</span>
    </span>
    <span class="lp-arrow">&rarr;</span>
</a>
'''
            )

        for page in page_files:
            title_page = learning_title(page)
            page_href = learning_href(page, output_dir)
            cards.append(
                f'''
<a class="lp-card lp-page" href="{page_href}">
    <span class="lp-card-text">
        <span class="lp-card-title">{html.escape(title_page)}</span>
    </span>
    <span class="lp-arrow">&rarr;</span>
</a>
'''
            )

    if not cards:
        cards.append(
            '''
<div class="lp-empty">
    <span class="lp-empty-title">Noch keine Lerninhalte</span>
    <span class="lp-empty-text">
        In diesem Bereich sind aktuell noch keine Seiten hinterlegt.
    </span>
</div>
'''
        )

    css_link = relative_url(
        output_dir,
        OUTPUT / "kurse.css"
    )

    crumb = breadcrumb(
        source_dir,
        output_dir
    )

    search_entries = build_search_index(
        output_dir
    )

    search_json = json.dumps(
        search_entries,
        ensure_ascii=False
    )

    document = f"""<!DOCTYPE html>
<html lang="de">

<head>
    <meta charset="UTF-8">
    <meta
        name="viewport"
        content="width=device-width, initial-scale=1.0"
    >
    <title>{html.escape(title)}</title>
    <link rel="stylesheet" href="{css_link}">
</head>

<body class="lp-index-page">

    <main class="lp-container">

        <nav class="lp-topbar">

            <a
                class="lp-nav-back"
                href="#"
                onclick="history.back(); return false;"
                aria-label="Zurück"
                title="Zurück"
            >
                &larr;
            </a>

            <div class="lp-global-search">
                <div class="lp-search-controls">
                    <input
                        class="lp-search"
                        id="lp-search"
                        type="search"
                        placeholder="Lerninhalte suchen ..."
                        aria-label="Lerninhalte suchen"
                        autocomplete="off"
                    >
                    <button
                        class="lp-search-button"
                        id="lp-search-button"
                        type="button"
                        aria-label="Suchen"
                        title="Suchen"
                    >
                        &#128269;
                    </button>
                </div>

                <div
                    class="lp-search-results"
                    id="lp-search-results"
                    hidden
                ></div>
            </div>

        </nav>

        <nav
            class="lp-breadcrumb"
            aria-label="Pfad"
        >
            {crumb}
        </nav>

        <header class="lp-header">
            <h1>{html.escape(title)}</h1>
        </header>

        <section class="lp-menu">
            {''.join(cards)}
        </section>

    </main>

<script>
const searchIndex = {search_json};

const searchInput = document.getElementById("lp-search");
const searchButton = document.getElementById("lp-search-button");
const searchResults = document.getElementById("lp-search-results");

function escapeHtml(value) {{
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}}

function renderSearchResults() {{
    const query = searchInput.value.trim().toLowerCase();

    if (!query) {{
        searchResults.innerHTML = "";
        searchResults.hidden = true;
        return;
    }}

    const matches = searchIndex
        .filter(item => {{
            const haystack = (
                item.title + " " + item.location
            ).toLowerCase();

            return haystack.includes(query);
        }})
        .slice(0, 15);

    if (matches.length === 0) {{
        searchResults.innerHTML =
            '<div class="lp-search-empty">Keine Lerninhalte gefunden.</div>';
        searchResults.hidden = false;
        return;
    }}

    searchResults.innerHTML = matches
        .map(item => {{
            const location = item.location
                ? '<span class="lp-result-location">'
                    + escapeHtml(item.location)
                    + '</span>'
                : '';

            return (
                '<a class="lp-search-result" href="'
                + escapeHtml(item.url)
                + '">'
                + '<span class="lp-result-title">'
                + escapeHtml(item.title)
                + '</span>'
                + location
                + '<span class="lp-result-arrow">&rarr;</span>'
                + '</a>'
            );
        }})
        .join("");

    searchResults.hidden = false;
}}

if (searchInput && searchButton && searchResults) {{
    searchInput.addEventListener("input", renderSearchResults);

    searchButton.addEventListener("click", function () {{
        searchInput.focus();
        renderSearchResults();
    }});

    searchInput.addEventListener("keydown", function (event) {{
        if (event.key === "Escape") {{
            searchResults.hidden = true;
            searchInput.blur();
        }}

        if (event.key === "Enter" && !searchResults.hidden) {{
            const first = searchResults.querySelector(".lp-search-result");
            if (first) {{
                first.click();
            }}
        }}
    }});

    document.addEventListener("click", function (event) {{
        if (!event.target.closest(".lp-global-search")) {{
            searchResults.hidden = true;
        }}
    }});
}}
</script>

</body>
</html>
"""

    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    (output_dir / "index.html").write_text(
        document,
        encoding="utf-8"
    )


# ============================================================
# Lernportal CSS
# Wird zusätzlich an deine kurse.css angehängt
# ============================================================

PORTAL_CSS = r'''

/* ==========================================================
   LERNPORTAL
   ========================================================== */


/* ==========================================================
   Grundlayout
   ========================================================== */

.lp-index-page {
    margin: 0;

    background: #f6f7f9;
    color: #1f2328;

    font-family:
        Arial,
        Helvetica,
        sans-serif;
}


.lp-container {
    width: min(
        980px,
        calc(100% - 40px)
    );

    margin:
        48px
        auto
        70px
        auto;
}




/* ==========================================================
   Obere Lernportal-Navigation
   ========================================================== */



.lp-topbar {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 18px;
}

.lp-nav-back {
    box-sizing: border-box;
    width: 42px;
    height: 42px;
    flex: 0 0 42px;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0;
    border: 1px solid #dfe2e6;
    border-radius: 9px;
    background: #ffffff;
    color: #4b5056;
    text-decoration: none;
    font-size: 20px;
    line-height: 1;
}

.lp-nav-back:hover {
    color: dodgerblue;
    border-color: #b8d8ff;
    background: #fbfdff;
}

.lp-global-search {
    position: relative;
    margin-left: auto;
    width: min(100%, 500px);
}

.lp-search-controls {
    display: flex;
    align-items: center;
    width: 100%;
    gap: 8px;
}

.lp-search {
    box-sizing: border-box;
    flex: 1 1 auto;
    min-width: 0;
    height: 42px;
    padding: 0 14px;
    border: 1px solid #dfe2e6;
    border-radius: 9px;
    background: #ffffff;
    color: #202124;
    font: inherit;
    font-size: 14px;
    outline: none;
}

.lp-search:focus {
    border-color: dodgerblue;
    box-shadow: 0 0 0 3px rgba(30, 144, 255, 0.10);
}

.lp-search::placeholder {
    color: #969ba1;
}

.lp-search-button {
    box-sizing: border-box;
    width: 42px;
    height: 42px;
    flex: 0 0 42px;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0;
    border: 1px solid #dfe2e6;
    border-radius: 9px;
    background: #ffffff;
    color: #4b5056;
    font-size: 17px;
    line-height: 1;
    cursor: pointer;
}

.lp-search-button:hover {
    color: dodgerblue;
    border-color: #b8d8ff;
    background: #fbfdff;
}

.lp-search-results {
    position: absolute;
    top: 50px;
    right: 0;
    z-index: 100;
    width: 100%;
    max-height: 430px;
    overflow-y: auto;
    box-sizing: border-box;
    padding: 8px;
    background: #ffffff;
    border: 1px solid #e0e3e7;
    border-radius: 12px;
    box-shadow: 0 12px 30px rgba(0, 0, 0, 0.12);
}

.lp-search-result {
    position: relative;
    display: flex;
    flex-direction: column;
    gap: 4px;
    box-sizing: border-box;
    width: 100%;
    padding: 12px 42px 12px 13px;
    border-radius: 9px;
    color: #202124;
    text-decoration: none;
}

.lp-search-result + .lp-search-result {
    margin-top: 3px;
}

.lp-search-result:hover {
    background: #f3f6f9;
}

.lp-result-title {
    display: block;
    color: #202124;
    font-size: 14px;
    font-weight: 650;
    line-height: 1.35;
}

.lp-result-location {
    display: block;
    color: #8a8f96;
    font-size: 12px;
    font-weight: 400;
    line-height: 1.35;
}

.lp-result-arrow {
    position: absolute;
    right: 14px;
    top: 50%;
    transform: translateY(-50%);
    color: #9aa0a6;
    font-size: 18px;
}

.lp-search-result:hover .lp-result-arrow {
    color: dodgerblue;
}

.lp-search-empty {
    padding: 14px 12px;
    color: #858a91;
    font-size: 14px;
    text-align: center;
}

@media (max-width: 650px) {
    .lp-topbar {
        align-items: flex-start;
    }

    .lp-global-search {
        width: 100%;
    }

    .lp-search-results {
        width: min(500px, calc(100vw - 24px));
    }
}

/* ==========================================================
   PDF-Ansicht
   ========================================================== */

.lp-pdf-page {
    margin: 0;
    background: #f6f7f9;
    color: #1f2328;
    font-family: Arial, Helvetica, sans-serif;
}

.lp-pdf-shell {
    width: min(1180px, calc(100% - 28px));
    margin: 18px auto 32px auto;
}

.lp-pdf-navbar {
    display: grid;
    grid-template-columns: 42px minmax(0, 1fr) auto;
    align-items: center;
    gap: 12px;
    margin-bottom: 12px;
}

.lp-pdf-title {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-size: 16px;
    font-weight: 650;
}

.lp-pdf-download {
    box-sizing: border-box;
    min-height: 42px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    padding: 0 14px;
    border: 1px solid #dfe2e6;
    border-radius: 9px;
    background: #ffffff;
    color: #4b5056;
    text-decoration: none;
    font-size: 14px;
}

.lp-pdf-download:hover {
    color: dodgerblue;
    border-color: dodgerblue;
}

.lp-pdf-viewer {
    overflow: hidden;
    background: #ffffff;
    border: 1px solid #e0e3e7;
    border-radius: 12px;
}

.lp-pdf-viewer iframe {
    display: block;
    width: 100%;
    height: 78vh;
    min-height: 620px;
    border: 0;
}

.lp-pdf-fallback {
    margin: 0;
    padding: 12px 16px;
    color: #70757d;
    font-size: 13px;
}

@media (max-width: 650px) {
    .lp-pdf-navbar {
        grid-template-columns: 42px minmax(0, 1fr);
    }

    .lp-pdf-download {
        grid-column: 1 / -1;
        justify-self: stretch;
    }

    .lp-pdf-viewer iframe {
        min-height: 520px;
        height: 72vh;
    }
}

/* ==========================================================
   Breadcrumb
   ========================================================== */

.lp-breadcrumb {
    display: flex;
    flex-wrap: wrap;
    align-items: center;

    gap: 8px;

    margin-bottom: 22px;

    font-size: 14px;
    color: #7a7f87;
}


.lp-breadcrumb a {
    color: #6a7078;
    text-decoration: none;
}


.lp-breadcrumb a:hover {
    color: dodgerblue;
}


.lp-separator {
    color: #b3b7bd;
}


/* ==========================================================
   Kopfbereich
   ========================================================== */

.lp-header {
    margin-bottom: 34px;
}


.lp-header h1 {
    margin: 0 0 10px 0;

    color: #1f2328;

    font-size:
        clamp(
            32px,
            5vw,
            48px
        );

    font-weight: 700;

    letter-spacing: -0.035em;
}


.lp-header p {
    margin: 0;

    max-width: 700px;

    color: #70757d;

    font-size: 16px;

    line-height: 1.6;

    padding: 0;
}


/* ==========================================================
   Menü
   ========================================================== */

.lp-menu {
    display: grid;

    grid-template-columns:
        repeat(
            2,
            minmax(0, 1fr)
        );

    gap: 16px;
}



.lp-section {
    grid-column: 1 / -1;
    margin-bottom: 24px;
}

.lp-section-title {
    margin: 0 0 14px 2px;
    padding-bottom: 9px;
    border-bottom: 1px solid #dde1e5;
    color: #30343a;
    font-size: 22px;
    font-weight: 650;
}

.lp-section-pages {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 16px;
}

.lp-section-empty {
    color: #858a91;
    font-size: 14px;
    padding: 8px 2px;
}

.lp-disabled {
    opacity: 0.45;
    pointer-events: none;
}

@media (max-width: 720px) {
    .lp-section-pages {
        grid-template-columns: 1fr;
    }
}


/* ==========================================================
   Karten
   ========================================================== */

.lp-card {
    box-sizing: border-box;

    min-height: 105px;

    padding:
        22px
        24px;

    display: flex;

    align-items: center;
    justify-content: space-between;

    gap: 20px;

    background: #ffffff;

    border:
        1px
        solid
        #e0e3e7;

    border-radius: 14px;

    color: #1f2328;

    text-decoration: none;

    transition:
        transform 0.15s ease,
        border-color 0.15s ease,
        box-shadow 0.15s ease,
        background-color 0.15s ease;
}


.lp-card:hover {
    transform: translateY(-2px);

    border-color: #b8d8ff;

    box-shadow:
        0
        8px
        24px
        rgba(0, 0, 0, 0.07);

    background: #fbfdff;
}


.lp-card-text {
    display: flex;

    flex-direction: column;

    gap: 7px;

    min-width: 0;
}


.lp-card-title {
    color: #202124;

    font-size: 19px;

    font-weight: 650;

    line-height: 1.25;
}


.lp-card-subtitle {
    color: #8a8f96;

    font-size: 13px;

    line-height: 1.4;
}


/* ==========================================================
   Pfeil rechts
   ========================================================== */

.lp-arrow {
    flex:
        0
        0
        auto;

    display: flex;

    align-items: center;
    justify-content: center;

    width: 36px;
    height: 36px;

    border-radius: 50%;

    background: #f1f3f5;

    color: #777c82;

    font-size: 20px;

    transition:
        background-color 0.15s ease,
        color 0.15s ease,
        transform 0.15s ease;
}


.lp-card:hover .lp-arrow {
    background: #e7f2ff;

    color: dodgerblue;

    transform:
        translateX(2px);
}


/* ==========================================================
   Lernbereiche
   ========================================================== */

.lp-folder {
    border-left:
        4px
        solid
        dodgerblue;
}


/* ==========================================================
   Lernseiten
   ========================================================== */

.lp-page {
    border-left:
        4px
        solid
        #c9ccd1;
}


/* ==========================================================
   Leere Bereiche
   ========================================================== */

.lp-empty {
    grid-column:
        1 / -1;

    box-sizing: border-box;

    padding: 28px;

    display: flex;

    flex-direction: column;

    gap: 7px;

    background: #ffffff;

    border:
        1px
        dashed
        #cfd3d8;

    border-radius: 14px;

    text-align: center;
}


.lp-empty-title {
    color: #44484e;

    font-size: 17px;

    font-weight: 600;
}


.lp-empty-text {
    color: #858a91;

    font-size: 14px;
}


/* ==========================================================
   Navbar auf Lernseiten
   ========================================================== */

.lp-navbar {
    box-sizing: border-box;

    width: 100%;

    min-height: 54px;

    margin:
        0
        0
        28px
        0;

    padding:
        9px
        12px;

    display: flex;

    align-items: center;
    justify-content: space-between;

    gap: 16px;

    background: #ffffff;

    border:
        1px
        solid
        #e0e3e7;

    border-radius: 10px;

    font-family:
        Arial,
        Helvetica,
        sans-serif;

    font-size: 14px;
}


.lp-navbar a {
    color: #444a50;

    text-decoration: none;

    padding:
        8px
        11px;

    border-radius: 7px;

    transition:
        background-color 0.15s ease,
        color 0.15s ease;
}


.lp-navbar a:hover {
    background: #f1f3f5;

    color: dodgerblue;
}


.lp-home {
    color: #777c82 !important;
}


/* ==========================================================
   Mobile
   ========================================================== */

@media (max-width: 720px) {

    .lp-container {
        width:
            min(
                calc(100% - 24px),
                980px
            );

        margin:
            28px
            auto
            50px
            auto;
    }


    .lp-menu {
        grid-template-columns: 1fr;
    }


    .lp-card {
        min-height: 90px;

        padding: 18px;
    }


    .lp-card-title {
        font-size: 17px;
    }


    .lp-header {
        margin-bottom: 26px;
    }


    .lp-navbar {
        margin-bottom: 20px;
    }
}
'''


# ============================================================
# BUILD
# ============================================================

print()
print("====================================")
print("        Lernportal Build")
print("====================================")
print()


# ============================================================
# Prüfen, ob inhalte existiert
# ============================================================

if not SOURCE.exists():
    print(
        "FEHLER: Der Ordner 'inhalte' wurde nicht gefunden."
    )

    raise SystemExit(1)


# ============================================================
# docs neu erzeugen
# ============================================================

if OUTPUT.exists():
    print(
        "Entferne alten docs-Ordner..."
    )

    shutil.rmtree(OUTPUT)


OUTPUT.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# CSS erzeugen
# ============================================================

css_content = ""

if MAIN_CSS.exists():
    print(
        "Lade kurse.css..."
    )

    css_content = MAIN_CSS.read_text(
        encoding="utf-8",
        errors="replace"
    )

else:
    print(
        "WARNUNG: kurse.css wurde nicht gefunden."
    )


(
    OUTPUT
    / "kurse.css"
).write_text(
    css_content
    + "\n"
    + PORTAL_CSS,
    encoding="utf-8"
)


# ============================================================
# Dateien verarbeiten
# ============================================================

print(
    "Verarbeite Lerninhalte..."
)


for source_file in SOURCE.rglob("*"):

    relative = source_file.relative_to(SOURCE)

    output_file = OUTPUT / relative

    # Ordner anlegen
    if source_file.is_dir():
        output_file.mkdir(
            parents=True,
            exist_ok=True
        )

        continue

    # versteckte Dateien ignorieren
    if source_file.name.startswith("."):
        continue

    # vorhandene index.html ignorieren
    if (
        source_file.suffix.lower()
        in (".html", ".htm")
        and source_file.stem.lower()
        == "index"
    ):
        continue

    # HTML-Dateien bearbeiten
    if (
        source_file.suffix.lower()
        in (".html", ".htm")
    ):
        process_html(
            source_file,
            output_file
        )

    # PDFs kopieren und eine Viewer-Seite mit Navbar erzeugen
    elif source_file.suffix.lower() == ".pdf":
        create_pdf_viewer(
            source_file,
            output_file
        )

    # alle anderen Dateien kopieren
    else:
        output_file.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        shutil.copy2(
            source_file,
            output_file
        )


# ============================================================
# Indexseiten erzeugen
# ============================================================

print(
    "Erzeuge Navigation..."
)


all_dirs = [SOURCE]


all_dirs.extend(
    sorted(
        [
            directory
            for directory
            in SOURCE.rglob("*")

            if directory.is_dir()

            and not any(
                part.startswith(".")
                or part.lower() == "img"
                for part
                in directory.relative_to(SOURCE).parts
            )
        ],

        key=lambda x: len(x.parts)
    )
)


for source_dir in all_dirs:

    output_dir = (
        OUTPUT
        / source_dir.relative_to(SOURCE)
    )

    create_index(
        source_dir,
        output_dir
    )


# ============================================================
# Fertig
# ============================================================

print()
print("====================================")
print("        Build abgeschlossen")
print("====================================")
print()

print(
    "Website wurde erzeugt unter:"
)

print(
    OUTPUT
)

print()