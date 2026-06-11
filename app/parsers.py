"""
Local recipe parsers used as a fallback when the Nextcloud API can't import a URL.

Flow:
  1. Try Nextcloud API (client.import_recipe)
  2. On failure, fetch the page ourselves with a browser UA
  3. Try generic JSON-LD (Schema.org) — covers most modern recipe sites
  4. Try site-specific HTML parser if one exists for this hostname
  5. Raise ValueError if nothing worked
"""

import json
import re
import requests
from urllib.parse import urlparse

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-GB,en;q=0.5",
}

# Registry of hostname fragments → parser functions
# Each function receives (html: str, url: str) and returns dict | None
_SITE_PARSERS: dict[str, callable] = {}


def _register(*hostnames):
    def decorator(fn):
        for h in hostnames:
            _SITE_PARSERS[h] = fn
        return fn
    return decorator


# ── Public entry point ────────────────────────────────────────────────────────

def parse_recipe_from_url(url: str, verify_ssl: bool = True) -> dict:
    """
    Fetch url and parse a recipe from it.
    Returns a Schema.org Recipe dict ready for CookbookClient.create_recipe().
    Raises ValueError if no recipe could be extracted.
    """
    resp = requests.get(url, headers=_HEADERS, timeout=20, verify=verify_ssl)
    resp.raise_for_status()
    html = resp.text

    host = urlparse(url).hostname or ""

    # Generic JSON-LD first — catches most modern recipe sites
    result = _parse_json_ld(html, url)
    if result:
        return result

    # Site-specific HTML fallback
    for fragment, parser in _SITE_PARSERS.items():
        if fragment in host:
            result = parser(html, url)
            if result:
                return result
            break

    raise ValueError(
        f"Could not find a recipe on this page.\n"
        f"The site '{host}' may not be supported."
    )


# ── Generic JSON-LD parser ────────────────────────────────────────────────────

def _parse_json_ld(html: str, url: str = "") -> dict | None:
    """Extract the first Schema.org Recipe from any JSON-LD blocks on the page."""
    pattern = re.compile(
        r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        re.DOTALL | re.IGNORECASE,
    )
    for m in pattern.finditer(html):
        try:
            blob = json.loads(m.group(1).strip())
        except json.JSONDecodeError:
            continue
        node = _find_recipe_node(blob)
        if node:
            return _normalise_json_ld(node, url)
    return None


def _find_recipe_node(blob) -> dict | None:
    """Recursively locate a Recipe node inside a JSON-LD blob."""
    if isinstance(blob, list):
        for item in blob:
            r = _find_recipe_node(item)
            if r:
                return r
    elif isinstance(blob, dict):
        t = blob.get("@type", "")
        types = t if isinstance(t, list) else [t]
        if "Recipe" in types:
            return blob
        if "@graph" in blob:
            return _find_recipe_node(blob["@graph"])
    return None


def _text(v) -> str:
    """Best-effort extraction of a plain string from a Schema.org value."""
    if isinstance(v, str):
        return v.strip()
    if isinstance(v, dict):
        return (v.get("text") or v.get("name") or "").strip()
    if isinstance(v, list):
        return _text(v[0]) if v else ""
    return str(v).strip() if v is not None else ""


def _normalise_json_ld(d: dict, source_url: str = "") -> dict:
    """Convert a raw Schema.org Recipe dict to the format Nextcloud Cookbook expects."""
    # Instructions
    raw_inst = d.get("recipeInstructions", [])
    if isinstance(raw_inst, str):
        instructions = [
            {"@type": "HowToStep", "text": s.strip()}
            for s in re.split(r"\n+", raw_inst) if s.strip()
        ]
    else:
        instructions = []
        for step in (raw_inst if isinstance(raw_inst, list) else [raw_inst]):
            if isinstance(step, str) and step.strip():
                instructions.append({"@type": "HowToStep", "text": step.strip()})
            elif isinstance(step, dict):
                if step.get("@type") == "HowToSection":
                    for s in step.get("itemListElement", []):
                        t = _text(s)
                        if t:
                            instructions.append({"@type": "HowToStep", "text": t})
                else:
                    t = _text(step)
                    if t:
                        instructions.append({"@type": "HowToStep", "text": t})

    # Image
    img = d.get("image", "")
    if isinstance(img, list):
        img = img[0] if img else ""
    if isinstance(img, dict):
        img = img.get("url", "")

    # Category and keywords
    cat = d.get("recipeCategory", "")
    if isinstance(cat, list):
        cat = cat[0] if cat else ""
    kw = d.get("keywords", "")
    if isinstance(kw, list):
        kw = ", ".join(kw)

    # Tools
    tools_raw = d.get("tool", [])
    if isinstance(tools_raw, str):
        tools_raw = [t.strip() for t in tools_raw.split(",") if t.strip()]
    tools = [_text(t) for t in tools_raw if _text(t)]

    return {
        "@context": "http://schema.org",
        "@type": "Recipe",
        "name": _text(d.get("name", "")),
        "description": _text(d.get("description", "")),
        "url": source_url or d.get("url", ""),
        "image": str(img),
        "recipeYield": str(d.get("recipeYield", "") or ""),
        "prepTime": str(d.get("prepTime", "") or ""),
        "cookTime": str(d.get("cookTime", "") or ""),
        "totalTime": str(d.get("totalTime", "") or ""),
        "recipeCategory": str(cat),
        "keywords": str(kw),
        "recipeIngredient": [_text(i) for i in d.get("recipeIngredient", [])],
        "recipeInstructions": instructions,
        "tool": tools,
        "nutrition": d.get("nutrition") or {},
    }


# ── Site-specific parsers ─────────────────────────────────────────────────────

@_register("jamesmartinchef")
def _parse_james_martin(html: str, url: str) -> dict | None:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")

    # ── Title ─────────────────────────────────────────────────────────────────
    el = soup.select_one("h4.recipe-introduction-title")
    if not el:
        return None
    name = el.get_text(strip=True)

    # ── Image — stored in data-image on the photo wrapper ────────────────────
    img = ""
    photo = soup.select_one("div.recipe-introduction-photo[data-image]")
    if photo:
        img = photo.get("data-image", "")

    # ── Description ───────────────────────────────────────────────────────────
    description = ""
    el = soup.select_one("div.recipe-introduction-description")
    if el:
        description = el.get_text(" ", strip=True)

    # ── Category ──────────────────────────────────────────────────────────────
    category = ""
    el = soup.select_one("div.recipe-introduction-categories a")
    if el:
        category = el.get_text(strip=True)

    # ── Serves ────────────────────────────────────────────────────────────────
    recipe_yield = ""
    el = soup.select_one("div.serves span")
    if el:
        recipe_yield = el.get_text(strip=True)

    # Scope to the desktop version to avoid picking up the duplicate mobile section
    desktop = soup.select_one("div.recipe-content.desktop") or soup

    # ── Ingredients — each .single-ingredient may have a title + a <ul> ──────
    ingredients = []
    for group in desktop.select("div.single-ingredient"):
        title_el = group.select_one("div.title")
        group_title = title_el.get_text(strip=True) if title_el else ""
        for li in group.select("div.content li"):
            text = li.get_text(" ", strip=True)
            if text:
                if group_title:
                    ingredients.append(f"{group_title}: {text}")
                else:
                    ingredients.append(text)

    # ── Method — steps are in <p> or <li> inside .recipe-description .content ──
    instructions = []
    content = desktop.select_one("div.recipe-description div.content")
    if content:
        steps = content.select("p") or content.select("li")
        if not steps:
            # JS-rendered pages may put the HTML only in the data attribute
            raw_html = content.get("data-rbds_content_content", "")
            if raw_html:
                inner = BeautifulSoup(raw_html, "html.parser")
                steps = inner.select("p") or inner.select("li")
        for step in steps:
            text = step.get_text(" ", strip=True)
            if text:
                instructions.append({"@type": "HowToStep", "text": text})

    if not ingredients and not instructions:
        return None

    return {
        "@context": "http://schema.org",
        "@type": "Recipe",
        "name": name,
        "description": description,
        "url": url,
        "image": img,
        "recipeYield": recipe_yield,
        "prepTime": "",
        "cookTime": "",
        "totalTime": "",
        "recipeCategory": category,
        "keywords": "",
        "recipeIngredient": ingredients,
        "recipeInstructions": instructions,
        "tool": [],
        "nutrition": {},
    }
