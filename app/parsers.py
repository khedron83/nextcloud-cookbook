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
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return None

    soup = BeautifulSoup(html, "html.parser")

    # ── Title ─────────────────────────────────────────────────────────────────
    name = ""
    for sel in (".recipe-title", "h1.entry-title", ".entry-title", "h1"):
        el = soup.select_one(sel)
        if el:
            name = el.get_text(strip=True)
            break
    if not name:
        return None

    # ── Ingredients ───────────────────────────────────────────────────────────
    ingredients = []
    ingredient_selectors = [
        ".ingredients li",
        ".recipe-ingredients li",
        "[class*='ingredient'] li",
        ".recipe__ingredients li",
        ".wprm-recipe-ingredient",
    ]
    for sel in ingredient_selectors:
        items = soup.select(sel)
        if items:
            ingredients = [li.get_text(" ", strip=True) for li in items if li.get_text(strip=True)]
            break

    # ── Method ────────────────────────────────────────────────────────────────
    instructions = []
    method_selectors = [
        ".method li",
        ".recipe-method li",
        ".recipe-steps li",
        "[class*='method'] li",
        ".recipe__method li",
        ".wprm-recipe-instruction-text",
        ".instructions li",
    ]
    for sel in method_selectors:
        items = soup.select(sel)
        if items:
            instructions = [
                {"@type": "HowToStep", "text": li.get_text(" ", strip=True)}
                for li in items if li.get_text(strip=True)
            ]
            break

    # ── Description ───────────────────────────────────────────────────────────
    description = ""
    for sel in (".recipe-description", ".recipe-intro", ".entry-summary"):
        el = soup.select_one(sel)
        if el:
            description = el.get_text(" ", strip=True)
            break

    # ── Image ─────────────────────────────────────────────────────────────────
    img = ""
    for sel in (".recipe-hero img", ".recipe-image img", ".wp-post-image", ".entry-image img"):
        el = soup.select_one(sel)
        if el:
            img = el.get("src", "")
            break

    # ── Yield / Serves ────────────────────────────────────────────────────────
    recipe_yield = ""
    for sel in (".recipe-serves", ".recipe-yield", "[class*='serves']", "[class*='yield']"):
        el = soup.select_one(sel)
        if el:
            recipe_yield = el.get_text(strip=True)
            break

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
        "recipeCategory": "",
        "keywords": "",
        "recipeIngredient": ingredients,
        "recipeInstructions": instructions,
        "tool": [],
        "nutrition": {},
    }
