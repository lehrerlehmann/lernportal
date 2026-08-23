from pathlib import Path
import base64
import mimetypes
import re
import shutil


ROOT = Path(__file__).resolve().parent

SOURCE = ROOT / "inhalte"
OUTPUT = ROOT / "standalone"
MASTER_CSS = ROOT / "kurse.css"


# ============================================================
# Hilfsfunktionen
# ============================================================

def is_external_url(url):
    url = url.strip().lower()

    return (
        url.startswith("http://")
        or url.startswith("https://")
        or url.startswith("//")
        or url.startswith("data:")
        or url.startswith("#")
        or url.startswith("mailto:")
        or url.startswith("javascript:")
    )


def clean_url(url):
    """
    Entfernt Query-String und Fragment für den Dateizugriff.
    Beispiel:
    img/bild.png?v=2#test
    -> img/bild.png
    """
    return url.split("#", 1)[0].split("?", 1)[0]


def file_to_data_uri(path):
    """
    Wandelt eine Datei in eine data:-URI um.
    """

    if not path.exists() or not path.is_file():
        return None

    mime_type, _ = mimetypes.guess_type(path.name)

    if mime_type is None:
        mime_type = "application/octet-stream"

    data = path.read_bytes()

    encoded = base64.b64encode(data).decode("ascii")

    return f"data:{mime_type};base64,{encoded}"


# ============================================================
# Bilder innerhalb von CSS einbetten
# ============================================================

def embed_css_images(css_text, css_directory):

    pattern = re.compile(
        r'url\(\s*(["\']?)(.*?)\1\s*\)',
        flags=re.IGNORECASE
    )

    def replace(match):

        quote = match.group(1)
        url = match.group(2).strip()

        if is_external_url(url):
            return match.group(0)

        # CSS-Fonts usw. ebenfalls zulassen.
        # Alles Lokale kann grundsätzlich eingebettet werden.
        clean = clean_url(url)

        file_path = (css_directory / clean).resolve()

        data_uri = file_to_data_uri(file_path)

        if data_uri is None:
            print(
                f"  WARNUNG: CSS-Datei nicht gefunden: {file_path}"
            )
            return match.group(0)

        return f'url("{data_uri}")'

    return pattern.sub(replace, css_text)


# ============================================================
# <link rel="stylesheet"> einbetten
# ============================================================

def embed_linked_stylesheets(html_text, html_file):

    pattern = re.compile(
        r'<link\b([^>]*?)>',
        flags=re.IGNORECASE | re.DOTALL
    )

    def replace(match):

        entire_tag = match.group(0)
        attributes = match.group(1)

        if not re.search(
            r'rel\s*=\s*["\']?stylesheet["\']?',
            attributes,
            flags=re.IGNORECASE
        ):
            return entire_tag

        href_match = re.search(
            r'href\s*=\s*["\']([^"\']+)["\']',
            attributes,
            flags=re.IGNORECASE
        )

        if not href_match:
            return entire_tag

        href = href_match.group(1)

        if is_external_url(href):
            return entire_tag

        css_path = (
            html_file.parent
            / clean_url(href)
        ).resolve()

        if not css_path.exists():
            print(
                f"  WARNUNG: Stylesheet nicht gefunden: {css_path}"
            )
            return entire_tag

        css = css_path.read_text(
            encoding="utf-8",
            errors="replace"
        )

        css = embed_css_images(
            css,
            css_path.parent
        )

        return (
            "\n<style>\n"
            + css
            + "\n</style>\n"
        )

    return pattern.sub(
        replace,
        html_text
    )


# ============================================================
# Master-kurse.css einfügen
# ============================================================

def embed_master_css(html_text):

    if not MASTER_CSS.exists():
        print(
            "WARNUNG: kurse.css im Root wurde nicht gefunden."
        )
        return html_text

    css = MASTER_CSS.read_text(
        encoding="utf-8",
        errors="replace"
    )

    css = embed_css_images(
        css,
        MASTER_CSS.parent
    )

    style_block = (
        "\n<style data-standalone-master-css>\n"
        + css
        + "\n</style>\n"
    )

    if re.search(
        r"</head\s*>",
        html_text,
        flags=re.IGNORECASE
    ):

        return re.sub(
            r"</head\s*>",
            style_block + "</head>",
            html_text,
            count=1,
            flags=re.IGNORECASE
        )

    return style_block + html_text


# ============================================================
# <img src="..."> einbetten
# ============================================================

def embed_img_sources(html_text, html_file):

    pattern = re.compile(
        r'(<img\b[^>]*?\bsrc\s*=\s*)(["\'])(.*?)\2',
        flags=re.IGNORECASE | re.DOTALL
    )

    def replace(match):

        prefix = match.group(1)
        quote = match.group(2)
        src = match.group(3).strip()

        if is_external_url(src):
            return match.group(0)

        image_path = (
            html_file.parent
            / clean_url(src)
        ).resolve()

        data_uri = file_to_data_uri(image_path)

        if data_uri is None:
            print(
                f"  WARNUNG: Bild nicht gefunden: {image_path}"
            )
            return match.group(0)

        return (
            prefix
            + quote
            + data_uri
            + quote
        )

    return pattern.sub(
        replace,
        html_text
    )


# ============================================================
# srcset ebenfalls unterstützen
# ============================================================

def embed_srcset(html_text, html_file):

    pattern = re.compile(
        r'\bsrcset\s*=\s*(["\'])(.*?)\1',
        flags=re.IGNORECASE | re.DOTALL
    )

    def replace(match):

        quote = match.group(1)
        srcset = match.group(2)

        entries = []

        for item in srcset.split(","):

            parts = item.strip().split()

            if not parts:
                continue

            src = parts[0]
            descriptor = " ".join(parts[1:])

            if not is_external_url(src):

                image_path = (
                    html_file.parent
                    / clean_url(src)
                ).resolve()

                data_uri = file_to_data_uri(
                    image_path
                )

                if data_uri:
                    src = data_uri

            if descriptor:
                entries.append(
                    f"{src} {descriptor}"
                )
            else:
                entries.append(src)

        return (
            f'srcset={quote}'
            + ", ".join(entries)
            + quote
        )

    return pattern.sub(
        replace,
        html_text
    )


# ============================================================
# CSS in <style>...</style> bearbeiten
# ============================================================

def process_existing_style_blocks(html_text, html_file):

    pattern = re.compile(
        r'<style([^>]*)>(.*?)</style>',
        flags=re.IGNORECASE | re.DOTALL
    )

    def replace(match):

        attrs = match.group(1)
        css = match.group(2)

        css = embed_css_images(
            css,
            html_file.parent
        )

        return (
            f"<style{attrs}>"
            + css
            + "</style>"
        )

    return pattern.sub(
        replace,
        html_text
    )


# ============================================================
# Einzelne HTML-Datei erzeugen
# ============================================================

def make_standalone(source_file, output_file):

    print(
        f"Standalone: {source_file.relative_to(SOURCE)}"
    )

    html_text = source_file.read_text(
        encoding="utf-8",
        errors="replace"
    )

    # 1. bereits vorhandene externe/lokale CSS-Dateien einbetten
    html_text = embed_linked_stylesheets(
        html_text,
        source_file
    )

    # 2. Bilder in bestehenden <style>-Blöcken einbetten
    html_text = process_existing_style_blocks(
        html_text,
        source_file
    )

    # 3. zentrale kurse.css hinzufügen
    html_text = embed_master_css(
        html_text
    )

    # 4. normale Bilder einbetten
    html_text = embed_img_sources(
        html_text,
        source_file
    )

    # 5. responsive srcsets ebenfalls einbetten
    html_text = embed_srcset(
        html_text,
        source_file
    )

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    output_file.write_text(
        html_text,
        encoding="utf-8"
    )


# ============================================================
# img-Ordner in allen Lernbereichen erzeugen
# ============================================================

def create_image_folders():

    print()
    print("Prüfe img-Ordner...")

    # Erwartete Klassenordner
    class_names = {
        "klasse7",
        "klasse8",
        "klasse9",
        "klasse10",
        "sek2",
    }

    for class_dir in SOURCE.iterdir():

        if (
            not class_dir.is_dir()
            or class_dir.name not in class_names
        ):
            continue

        # Direkte Unterordner einer Klasse = Lernbereiche
        for learning_area in class_dir.iterdir():

            if (
                not learning_area.is_dir()
                or learning_area.name.startswith(".")
                or learning_area.name.lower() == "img"
            ):
                continue

            img_dir = learning_area / "img"

            if not img_dir.exists():

                img_dir.mkdir(
                    parents=True,
                    exist_ok=True
                )

                print(
                    f"  Erstellt: "
                    f"{img_dir.relative_to(ROOT)}"
                )


# ============================================================
# Build
# ============================================================

def main():

    print()
    print("========================================")
    print("       Standalone-Seiten erzeugen")
    print("========================================")
    print()

    if not SOURCE.exists():

        print(
            "FEHLER: Ordner 'inhalte' existiert nicht."
        )

        raise SystemExit(1)

    # img-Ordner automatisch ergänzen
    create_image_folders()

    # alten Output löschen
    if OUTPUT.exists():

        print()
        print("Lösche alten standalone-Ordner...")

        shutil.rmtree(OUTPUT)

    OUTPUT.mkdir(
        parents=True,
        exist_ok=True
    )

    print()
    print("Verarbeite HTML-Dateien...")
    print()

    count = 0

    for source_file in SOURCE.rglob("*"):

        if not source_file.is_file():
            continue

        if source_file.name.startswith("."):
            continue

        if source_file.suffix.lower() not in (
            ".html",
            ".htm"
        ):
            continue

        # automatisch erzeugte/alte Indexseiten nicht exportieren
        if source_file.stem.lower() == "index":
            continue

        relative = source_file.relative_to(
            SOURCE
        )

        output_file = OUTPUT / relative

        make_standalone(
            source_file,
            output_file
        )

        count += 1

    print()
    print("========================================")
    print("Fertig!")
    print("========================================")
    print()
    print(
        f"{count} Standalone-Seite(n) erzeugt."
    )
    print()
    print(
        f"Ausgabe: {OUTPUT}"
    )
    print()


if __name__ == "__main__":
    main()