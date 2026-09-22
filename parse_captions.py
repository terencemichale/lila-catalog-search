import json
import re
import xml.etree.ElementTree as ET

from paths import catalog_root

ROOT = catalog_root()
OUTPUT = ROOT / "products.json"
EXCEL_FILE = ROOT / "lila_fabrics_my_posts.xls"

FIELD_PATTERNS = {
    "price": [
        re.compile(r"^\s*price\s*:\s*(.+?)\s*$", re.IGNORECASE),
        re.compile(r"^\s*price\s+(.+?)\s*$", re.IGNORECASE),
    ],
    "material": [
        re.compile(r"^\s*material\s*:\s*(.+?)\s*$", re.IGNORECASE),
    ],
    "length": [
        re.compile(r"^\s*saree\s+length\s*:\s*(.+?)\s*$", re.IGNORECASE),
        re.compile(r"^\s*length\s*:\s*(.+?)\s*$", re.IGNORECASE),
    ],
    "care": [
        re.compile(r"^\s*washing\s+care\s*:\s*(.+?)\s*$", re.IGNORECASE),
        re.compile(r"^\s*wash(?:ing)?\s+care\s*:\s*(.+?)\s*$", re.IGNORECASE),
        re.compile(r"^\s*care\s*:\s*(.+?)\s*$", re.IGNORECASE),
    ],
}

CONTACT_PATTERN = re.compile(r"\+[\d]{10,}")

def load_ig_urls() -> dict:
    if not EXCEL_FILE.exists():
        return {}
    tree = ET.parse(str(EXCEL_FILE))
    root = tree.getroot()
    ns = {'x': 'urn:schemas-microsoft-com:office:spreadsheet'}
    folder_to_url = {}
    for ws in root.findall('x:Worksheet', ns):
        table = ws.find('x:Table', ns)
        if table is None:
            continue
        rows = table.findall('x:Row', ns)
        folder_row_idx = None
        url_row_idx = None
        for i, row in enumerate(rows):
            cells = row.findall('x:Cell', ns)
            if not cells:
                continue
            first_data = cells[0].find('x:Data', ns)
            if first_data is None or first_data.text is None:
                continue
            if first_data.text == 'Folder Name':
                folder_row_idx = i
            elif first_data.text == 'Post URL':
                url_row_idx = i
        if folder_row_idx is not None and url_row_idx is not None:
            folder_row = rows[folder_row_idx]
            url_row = rows[url_row_idx]
            folder_cells = folder_row.findall('x:Cell', ns)
            url_cells = url_row.findall('x:Cell', ns)
            for fc, uc in zip(folder_cells[1:], url_cells[1:]):
                fdata = fc.find('x:Data', ns)
                udata = uc.find('x:Data', ns)
                if fdata is not None and fdata.text and udata is not None and udata.text:
                    folder_to_url[fdata.text] = udata.text
    return folder_to_url

def parse_caption(txt: str) -> dict:
    result = {}
    for line in txt.split("\n"):
        line = line.strip()
        for field_name, patterns in FIELD_PATTERNS.items():
            if field_name in result:
                continue
            for pattern in patterns:
                match = pattern.match(line)
                if match:
                    result[field_name] = match.group(1).strip()
                    break
        if "contact" not in result and ("whatsapp" in line.lower() or "telegram" in line.lower()):
            match = CONTACT_PATTERN.search(line)
            if match:
                result["contact"] = match.group()
    return result

def main() -> None:
    """Build the catalog only when explicitly invoked as a script."""
    ig_urls = load_ig_urls()
    print(f"Loaded {len(ig_urls)} IG URLs from Excel")
    
    products = []
    for folder in sorted(ROOT.iterdir()):
        if not folder.is_dir():
            continue
        caption_file = folder / "caption.txt"
        if caption_file.exists():
            txt = caption_file.read_text(encoding="utf-8")
            data = parse_caption(txt)
            data["folder"] = folder.name
            if folder.name in ig_urls:
                data["ig_url"] = ig_urls[folder.name]
            products.append(data)
    
    OUTPUT.write_text(json.dumps(products, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Written {len(products)} products to {OUTPUT}")


if __name__ == "__main__":
    main()
