$root = $PSScriptRoot

Write-Host ""
Write-Host "=== Lernportal einrichten ===" -ForegroundColor Cyan
Write-Host ""

# ============================================================
# Ordnerstruktur
# ============================================================

$folders = @(
    "inhalte",
    "inhalte\klasse7",
    "inhalte\klasse8",
    "inhalte\klasse9",
    "inhalte\klasse10",
    "inhalte\sek2",
    "docs"
)

foreach ($folder in $folders) {
    $path = Join-Path $root $folder

    if (!(Test-Path $path)) {
        New-Item -ItemType Directory -Path $path | Out-Null
        Write-Host "Erstellt: $folder"
    }
}

# ============================================================
# README-Dateien, damit leere Klassenordner in Git bleiben
# ============================================================

$classes = @(
    "klasse7",
    "klasse8",
    "klasse9",
    "klasse10",
    "sek2"
)

foreach ($class in $classes) {

    $readme = Join-Path $root "inhalte\$class\.gitkeep"

    if (!(Test-Path $readme)) {
        New-Item -ItemType File -Path $readme | Out-Null
    }
}

# ============================================================
# build.py erzeugen
# ============================================================

$buildPy = @'
from pathlib import Path
import shutil
import re
import html
import os


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "inhalte"
OUTPUT = ROOT / "docs"
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
# Titel einer HTML-Datei auslesen
# ============================================================

def get_html_title(path):
    try:
        text = path.read_text(encoding="utf-8")

        match = re.search(
            r"<title[^>]*>(.*?)</title>",
            text,
            flags=re.IGNORECASE | re.DOTALL
        )

        if match:
            title = re.sub(r"<[^>]+>", "", match.group(1))
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
# Navbar und CSS in Lernseite einsetzen
# ============================================================

def process_html(source_file, output_file):

    text = source_file.read_text(
        encoding="utf-8",
        errors="replace"
    )

    out_dir = output_file.parent

    css_link = relative_url(out_dir, OUTPUT / "kurse.css")
    portal_link = relative_url(out_dir, OUTPUT / "index.html")

    # Zurueck = Index des aktuellen Lernbereichs
    back_link = "index.html"

    stylesheet = (
        f'<link rel="stylesheet" href="{css_link}" '
        f'data-lernportal-style>'
    )

    navbar = f'''
<nav class="lp-navbar">
    <a class="lp-back" href="{back_link}">← Zurück</a>
    <a class="lp-home" href="{portal_link}">Lernportal</a>
</nav>
'''

    # CSS einfügen
    if re.search(r"</head\s*>", text, flags=re.IGNORECASE):

        text = re.sub(
            r"</head\s*>",
            stylesheet + "\n</head>",
            text,
            count=1,
            flags=re.IGNORECASE
        )

    else:
        text = stylesheet + "\n" + text

    # Navbar direkt nach body
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

        target_output = OUTPUT / path_so_far.relative_to(SOURCE) / "index.html"

        link = relative_url(
            current_output_dir,
            target_output
        )

        crumbs.append(
            f'<a href="{link}">{html.escape(pretty_name(part))}</a>'
        )

    return '<span class="lp-separator">›</span>'.join(crumbs)


# ============================================================
# Indexseite eines Ordners
# ============================================================

def create_index(source_dir, output_dir):

    relative = source_dir.relative_to(SOURCE)

    if relative.parts:
        title = pretty_name(relative.parts[-1])
    else:
        title = "Lernportal"

    folders = sorted(
        [
            item for item in source_dir.iterdir()
            if item.is_dir()
            and not item.name.startswith(".")
        ],
        key=lambda x: pretty_name(x.name).lower()
    )

    html_files = sorted(
        [
            item for item in source_dir.iterdir()
            if item.is_file()
            and item.suffix.lower() in (".html", ".htm")
            and item.stem.lower() != "index"
        ],
        key=lambda x: get_html_title(x).lower()
    )

    cards = []

    # Unterordner
    for folder in folders:

        cards.append(f'''
<a class="lp-card lp-folder" href="{folder.name}/">
    <span class="lp-card-text">
        <span class="lp-card-title">{html.escape(pretty_name(folder.name))}</span>
        <span class="lp-card-subtitle">Lernbereich</span>
    </span>
    <span class="lp-arrow">→</span>
</a>
''')

    # HTML-Seiten
    for page in html_files:

        title_page = get_html_title(page)

        cards.append(f'''
<a class="lp-card lp-page" href="{page.name}">
    <span class="lp-card-text">
        <span class="lp-card-title">{html.escape(title_page)}</span>
        <span class="lp-card-subtitle">Lernseite</span>
    </span>
    <span class="lp-arrow">→</span>
</a>
''')

    if not cards:
        cards.append(
            '<p class="lp-empty">Hier sind noch keine Lerninhalte hinterlegt.</p>'
        )

    css_link = relative_url(
        output_dir,
        OUTPUT / "kurse.css"
    )

    crumb = breadcrumb(
        source_dir,
        output_dir
    )

    document = f'''<!DOCTYPE html>
<html lang="de">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">

    <title>{html.escape(title)}</title>

    <link rel="stylesheet" href="{css_link}">
</head>

<body class="lp-index-page">

    <main class="lp-container">

        <nav class="lp-breadcrumb">
            {crumb}
        </nav>

        <header class="lp-header">
            <h1>{html.escape(title)}</h1>
        </header>

        <section class="lp-menu">
            {''.join(cards)}
        </section>

    </main>

</body>
</html>
'''

    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    (output_dir / "index.html").write_text(
        document,
        encoding="utf-8"
    )


# ============================================================
# CSS für Lernportal-Oberfläche
# ============================================================

PORTAL_CSS = r'''

/* ==========================================================
   Lernportal Navigation
   ========================================================== */

.lp-index-page {
    margin: 0;
    background: #f7f8fa;
    color: #202124;
    font-family: Arial, Helvetica, sans-serif;
}

.lp-container {
    width: min(850px, calc(100% - 40px));
    margin: 50px auto;
}

.lp-header {
    margin: 25px 0 30px 0;
}

.lp-header h1 {
    margin: 0;
    color: #202124;
    font-size: clamp(30px, 5vw, 46px);
    font-weight: 650;
    letter-spacing: -0.03em;
}

.lp-breadcrumb {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    align-items: center;
    font-size: 14px;
    margin-bottom: 18px;
}

.lp-breadcrumb a {
    color: #5f6368;
    text-decoration: none;
}

.lp-breadcrumb a:hover {
    color: dodgerblue;
}

.lp-separator {
    color: #a5a8ad;
}

.lp-menu {
    display: grid;
    gap: 12px;
}

.lp-card {
    box-sizing: border-box;
    width: 100%;
    min-height: 78px;
    padding: 17px 20px;

    display: flex;
    align-items: center;
    justify-content: space-between;

    background: white;

    border: 1px solid #dedfe2;
    border-radius: 10px;

    color: #202124;
    text-decoration: none;

    transition:
        border-color 0.15s ease,
        transform 0.15s ease,
        box-shadow 0.15s ease;
}

.lp-card:hover {
    border-color: dodgerblue;
    transform: translateY(-1px);
    box-shadow: 0 3px 12px rgba(0,0,0,0.06);
}

.lp-card-text {
    display: flex;
    flex-direction: column;
    gap: 4px;
}

.lp-card-title {
    font-size: 18px;
    font-weight: 600;
}

.lp-card-subtitle {
    color: #777b80;
    font-size: 13px;
}

.lp-arrow {
    color: #8a8d91;
    font-size: 23px;
    margin-left: 20px;
}

.lp-card:hover .lp-arrow {
    color: dodgerblue;
}

.lp-empty {
    color: #777b80;
}


/* ==========================================================
   Eingespritzte Navbar auf Lernseiten
   ========================================================== */

.lp-navbar {
    box-sizing: border-box;

    width: 100%;
    min-height: 52px;

    margin: 0 0 24px 0;
    padding: 8px 14px;

    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 15px;

    background: #ffffff;

    border: 1px solid #dedfe2;
    border-radius: 8px;

    font-family: Arial, Helvetica, sans-serif;
    font-size: 14px;
}

.lp-navbar a {
    color: #3c4043;
    text-decoration: none;
    padding: 7px 10px;
    border-radius: 6px;
}

.lp-navbar a:hover {
    background: #f1f3f4;
    color: dodgerblue;
}

.lp-home {
    color: #777b80 !important;
}

@media (max-width: 600px) {

    .lp-container {
        width: min(100% - 24px, 850px);
        margin: 25px auto;
    }

    .lp-card {
        padding: 15px;
    }

    .lp-card-title {
        font-size: 16px;
    }
}
'''


# ============================================================
# Build
# ============================================================

print()
print("=== Lernportal wird gebaut ===")
print()

# docs jedes Mal sauber neu erzeugen
if OUTPUT.exists():
    shutil.rmtree(OUTPUT)

OUTPUT.mkdir(parents=True)


# Haupt-CSS kopieren
css_content = ""

if MAIN_CSS.exists():
    css_content = MAIN_CSS.read_text(
        encoding="utf-8",
        errors="replace"
    )
else:
    print("WARNUNG: kurse.css wurde nicht gefunden.")


(OUTPUT / "kurse.css").write_text(
    css_content + PORTAL_CSS,
    encoding="utf-8"
)


# Alle Dateien kopieren / HTML bearbeiten
for source_file in SOURCE.rglob("*"):

    relative = source_file.relative_to(SOURCE)
    output_file = OUTPUT / relative

    if source_file.is_dir():
        output_file.mkdir(
            parents=True,
            exist_ok=True
        )
        continue

    # versteckte Dateien wie .gitkeep nicht veröffentlichen
    if source_file.name.startswith("."):
        continue

    # index.html aus Quellen ignorieren:
    # Index wird automatisch erzeugt
    if (
        source_file.suffix.lower() in (".html", ".htm")
        and source_file.stem.lower() == "index"
    ):
        continue

    if source_file.suffix.lower() in (".html", ".htm"):

        process_html(
            source_file,
            output_file
        )

    else:

        output_file.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        shutil.copy2(
            source_file,
            output_file
        )


# Für jeden Ordner einen Index erzeugen
all_dirs = [SOURCE]

all_dirs.extend(
    sorted(
        [
            d for d in SOURCE.rglob("*")
            if d.is_dir()
            and not any(
                part.startswith(".")
                for part in d.relative_to(SOURCE).parts
            )
        ],
        key=lambda x: len(x.parts)
    )
)

for source_dir in all_dirs:

    output_dir = OUTPUT / source_dir.relative_to(SOURCE)

    create_index(
        source_dir,
        output_dir
    )


print()
print("Fertig.")
print(f"Website erzeugt in: {OUTPUT}")
print()
'@

Set-Content `
    -Path (Join-Path $root "build.py") `
    -Value $buildPy `
    -Encoding UTF8


# ============================================================
# Neues SYNC-Skript erzeugen
# ============================================================

$syncBat = @'
@echo off
cd /d "%~dp0"

echo ======================================
echo        Lernportal synchronisieren
echo ======================================
echo.

echo [1/5] Lade aktuelle Version von GitHub...
git pull
if errorlevel 1 goto error

echo.
echo [2/5] Erzeuge Website...
py build.py
if errorlevel 1 goto error

echo.
echo [3/5] Fuege Aenderungen hinzu...
git add .

echo.
set /p msg=Beschreibung der Aenderung: 
if "%msg%"=="" set msg=Lernportal aktualisiert

echo.
echo [4/5] Erstelle Commit...
git commit -m "%msg%"

echo.
echo [5/5] Lade zu GitHub hoch...
git push
if errorlevel 1 goto error

echo.
echo ======================================
echo Lernportal ist synchronisiert!
echo ======================================
echo.

pause
exit /b

:error

echo.
echo ======================================
echo FEHLER bei der Synchronisierung
echo ======================================
echo.
echo Bitte Fehlermeldung oben ansehen.
echo.

pause
'@

Set-Content `
    -Path (Join-Path $root "Lernportal-SYNC.bat") `
    -Value $syncBat `
    -Encoding ASCII


# ============================================================
# Erstes Build
# ============================================================

Write-Host ""
Write-Host "Erzeuge erste Website..." -ForegroundColor Cyan

Set-Location $root

py build.py

Write-Host ""
Write-Host "=========================================" -ForegroundColor Green
Write-Host "Lernportal wurde eingerichtet!" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Eigene Dateien kommen ab jetzt nach:"
Write-Host "  inhalte\klasse7"
Write-Host "  inhalte\klasse8"
Write-Host "  inhalte\klasse9"
Write-Host "  inhalte\klasse10"
Write-Host "  inhalte\sek2"
Write-Host ""
Write-Host "docs\ wird automatisch erzeugt."
Write-Host ""
Read-Host "Enter zum Beenden"