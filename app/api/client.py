import requests
from requests.auth import HTTPBasicAuth
from typing import Optional


class CookbookAPIError(Exception):
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class CookbookClient:
    def __init__(self, base_url: str, username: str, password: str, verify_ssl: bool = True):
        self.base_url = base_url.rstrip("/")
        self._username = username
        self._session = requests.Session()
        self._session.auth = HTTPBasicAuth(username, password)
        self._session.verify = verify_ssl
        self._session.headers.update({
            "OCS-APIREQUEST": "true",
            "Accept": "application/json",
        })

    def _url(self, path: str) -> str:
        return f"{self.base_url}/index.php/apps/cookbook{path}"

    def _get(self, path: str, **kwargs) -> requests.Response:
        resp = self._session.get(self._url(path), **kwargs)
        self._check(resp)
        return resp

    def _post(self, path: str, **kwargs) -> requests.Response:
        resp = self._session.post(self._url(path), **kwargs)
        self._check(resp)
        return resp

    def _put(self, path: str, **kwargs) -> requests.Response:
        resp = self._session.put(self._url(path), **kwargs)
        self._check(resp)
        return resp

    def _delete(self, path: str, **kwargs) -> requests.Response:
        resp = self._session.delete(self._url(path), **kwargs)
        self._check(resp)
        return resp

    def _check(self, resp: requests.Response):
        if not resp.ok:
            try:
                msg = resp.json().get("msg", resp.text)
            except Exception:
                msg = resp.text or f"HTTP {resp.status_code}"
            raise CookbookAPIError(msg, resp.status_code)

    # ── API methods ───────────────────────────────────────────────────────────

    def get_api_version(self) -> dict:
        return self._get("/api/version").json()

    def get_recipes(self) -> list[dict]:
        return self._get("/api/v1/recipes").json()

    def get_recipe(self, recipe_id: int) -> dict:
        return self._get(f"/api/v1/recipes/{recipe_id}").json()

    def create_recipe(self, data: dict) -> dict:
        return self._post("/api/v1/recipes", json=data).json()

    def update_recipe(self, recipe_id: int, data: dict) -> dict:
        return self._put(f"/api/v1/recipes/{recipe_id}", json=data).json()

    def delete_recipe(self, recipe_id: int) -> None:
        self._delete(f"/api/v1/recipes/{recipe_id}")

    def import_recipe(self, url: str) -> dict:
        return self._post("/api/v1/import", data={"url": url}).json()

    def import_recipe_with_fallback(self, url: str) -> dict:
        """Try Nextcloud API import; on failure parse locally and create the recipe."""
        try:
            return self.import_recipe(url)
        except CookbookAPIError:
            pass
        from app.parsers import parse_recipe_from_url
        data = parse_recipe_from_url(url, verify_ssl=bool(self._session.verify))
        recipe_id = self.create_recipe(data)
        # create_recipe returns a bare integer ID; normalise for _on_imported
        if isinstance(recipe_id, int):
            return {"id": recipe_id}
        return recipe_id

    def search_recipes(self, query: str) -> list[dict]:
        return self._get(f"/api/v1/search/{query}").json()

    def get_categories(self) -> list:
        result = self._get("/api/v1/categories").json()
        return result if isinstance(result, list) else []

    def get_category_recipes(self, category: str) -> list[dict]:
        from urllib.parse import quote
        return self._get(f"/api/v1/category/{quote(category, safe='')}").json()

    def get_keywords(self) -> list:
        result = self._get("/api/v1/keywords").json()
        return result if isinstance(result, list) else []

    def get_recipe_image(self, recipe_id: int, size: str = "full") -> bytes:
        resp = self._session.get(
            self._url(f"/api/v1/recipes/{recipe_id}/image"),
            params={"size": size},
        )
        self._check(resp)
        return resp.content

    def rename_category(self, old_name: str, new_name: str) -> None:
        self._put(f"/api/v1/category/{old_name}", json={"name": new_name})

    def reindex(self) -> None:
        self._post("/api/v1/reindex")

    # ── WebDAV meal plan sync ─────────────────────────────────────────────────

    def _dav_url(self, path: str) -> str:
        return f"{self.base_url}/remote.php/dav/files/{self._username}/{path}"

    def get_meal_plan(self) -> list[dict]:
        """Fetch meal plan JSON from Nextcloud WebDAV. Returns [] if not found."""
        try:
            resp = self._session.get(self._dav_url("Cookbook/meal_plan.json"))
            if resp.status_code == 404:
                return []
            self._check(resp)
            return resp.json().get("entries", [])
        except Exception:
            return []

    def save_meal_plan(self, entries: list[dict]) -> None:
        """Push meal plan JSON to Nextcloud WebDAV."""
        import json as _json
        # Ensure Cookbook/ directory exists
        try:
            self._session.request("MKCOL", self._dav_url("Cookbook/"))
        except Exception:
            pass
        data = _json.dumps({"version": 1, "entries": entries})
        resp = self._session.put(
            self._dav_url("Cookbook/meal_plan.json"),
            data=data,
            headers={"Content-Type": "application/json"},
        )
        self._check(resp)
