import hashlib
import re


def extract_base_product_name(name: str) -> str:
    parts = name.rsplit("_", 2)
    if len(parts) >= 3 and parts[-1].isdigit() and parts[-2].isdigit():
        return "_".join(parts[:-2])
    return name


def thumbnail_filename_for_product(name: str) -> str:
    base_name = extract_base_product_name(name)
    slug = re.sub(r"[^a-z0-9]+", "-", base_name.lower()).strip("-")
    slug = slug[:32] or "product"
    digest = hashlib.sha1(base_name.encode("utf-8")).hexdigest()[:10]
    return f"{slug}-{digest}.jpg"
