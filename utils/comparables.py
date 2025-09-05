# utils/comparables.py
import os, re, requests
from typing import List, Dict, Optional
from urllib.parse import quote_plus
from bs4 import BeautifulSoup

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/121.0 Safari/537.36"
    )
}

# More flexible price regex
PRICE_RE = re.compile(r"(₹\s?[0-9,.KkMm]+|\b[0-9]{4,7}\b)")

def _parse_price(text: str) -> Optional[int]:
    """Parse string and return integer price."""
    if not text:
        return None
    m = PRICE_RE.search(text)
    if not m:
        return None
    val = m.group(0).replace("₹", "").replace(",", "").strip().lower()

    try:
        if val.endswith("k"):
            return int(float(val[:-1]) * 1000)
        if val.endswith("m"):
            return int(float(val[:-1]) * 1_000_000)
        if "lakh" in val:
            num = re.sub(r"[^\d.]", "", val)
            return int(float(num) * 100000)
        return int(float(val))
    except Exception:
        return None


def _fetch_olx(query: str, location: Optional[str] = None, max_results: int = 5) -> List[Dict]:
    """Scrape OLX directly for comparables."""
    out = []
    q = quote_plus(query)
    url = f"https://www.olx.in/items/q-{q}" if not location else f"https://www.olx.in/items/q-{q}-in-{quote_plus(location)}"

    try:
        resp = requests.get(url, headers=_HEADERS, timeout=8)
        if resp.status_code != 200:
            return out
        soup = BeautifulSoup(resp.text, "html.parser")
        seen = set()

        # OLX ad containers (multiple fallbacks)
        for card in soup.select("a[data-aut-id='itemBox'], li.EIR5N"):
            if len(out) >= max_results:
                break
            title = card.get_text(" ", strip=True)
            href = card.get("href") or url
            href_full = href if href.startswith("http") else "https://www.olx.in" + href
            price_tag = card.find(string=re.compile(r"₹"))
            price_val = _parse_price(price_tag or "")
            if price_val:
                key = (title, price_val)
                if key not in seen:
                    seen.add(key)
                    out.append({"site": "OLX", "title": title, "price": price_val, "url": href_full})

        return out[:max_results]
    except Exception as e:
        print("⚠️ OLX fetch error:", e)
        return out


def _search_with_serpapi(query: str, max_results: int = 8) -> List[Dict]:
    """Search online using SerpAPI (Google + Shopping)."""
    out = []
    key = os.getenv("SERPAPI_API_KEY")
    if not key:
        return out
    try:
        from serpapi import GoogleSearch
    except ImportError:
        print("⚠️ Install google-search-results to use SerpAPI")
        return out

    # Organic search
    params = {"engine": "google", "q": query, "num": max_results, "api_key": key, "hl": "en", "gl": "in"}
    try:
        search = GoogleSearch(params)
        results = search.get_dict()
        if "organic_results" in results:
            for r in results["organic_results"][:max_results]:
                title, link = r.get("title"), r.get("link")
                snippet = r.get("snippet") or ""
                price = _parse_price(title or "") or _parse_price(snippet)
                site = "web"
                if link:
                    if "olx." in link:
                        site = "OLX"
                    elif "cashify" in link:
                        site = "Cashify"
                    else:
                        try:
                            site = link.split("/")[2]
                        except Exception:
                            site = "web"
                out.append({"site": site, "title": title, "price": price, "url": link})

        # Shopping results
        shop_params = {"engine": "google_shopping", "q": query, "api_key": key, "hl": "en", "gl": "in"}
        shop_search = GoogleSearch(shop_params).get_dict()
        if "shopping_results" in shop_search:
            for r in shop_search["shopping_results"][:max_results]:
                price = None
                if "extracted_price" in r:
                    price = int(float(r["extracted_price"]))
                else:
                    price = _parse_price(str(r.get("price", "")))

                out.append({
                    "site": r.get("source") or "Google Shopping",
                    "title": r.get("title"),
                    "price": price,
                    "url": r.get("link"),
                })
    except Exception as e:
        print("⚠️ SerpAPI error:", e)
    return out


def get_comparables(title: str, location: Optional[str] = None, max_results: int = 6) -> List[Dict]:
    """Get comparable listings from SerpAPI (preferred) or OLX fallback."""
    query = f"{title} {location}" if location else title
    comps = _search_with_serpapi(query, max_results=max_results)
    if comps:
        comps_sorted = sorted(
            comps,
            key=lambda r: (0 if (r.get("site") and str(r["site"]).lower() in ("olx", "cashify")) else 1,
                           -int(r.get("price") or 0))
        )
        return comps_sorted[:max_results]

    return _fetch_olx(title, location=location, max_results=max_results)
