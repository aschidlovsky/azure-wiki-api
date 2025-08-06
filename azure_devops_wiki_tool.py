import base64
import os
from typing import List, Dict, Optional, Any
import requests
from urllib.parse import quote

class AzureDevOpsWikiTool:
    def __init__(
        self,
        org: Optional[str] = None,
        project: Optional[str] = None,
        pat: Optional[str] = None,
        api_version: str = "7.1-preview.1",
    ) -> None:
        self.org = org or os.getenv("AZURE_DEVOPS_ORG")
        self.project = project or os.getenv("AZURE_DEVOPS_PROJECT")
        self.pat = pat or os.getenv("AZURE_DEVOPS_PAT")
        self.api_version = api_version

        if not self.org or not self.project or not self.pat:
            raise ValueError(
                "Organization, project, and PAT must all be provided via parameters or environment variables"
            )

        pat_bytes = f":{self.pat}".encode()
        self._headers = {
            "Authorization": "Basic " + base64.b64encode(pat_bytes).decode(),
        }

        self._base_url = (
            f"https://dev.azure.com/{self.org}/{self.project}/_apis/wiki"
        )

    def _request(self, method: str, url: str, **kwargs: Any) -> Dict[str, Any]:
        headers = kwargs.pop("headers", {})
        merged_headers = {**self._headers, **headers}
        params = kwargs.pop("params", None)
        print(f"DEBUG: Calling Azure DevOps URL: {url}")
        print(f"DEBUG: Method: {method}")
        print(f"DEBUG: Org: {self.org}, Project: {self.project}, PAT Set: {bool(self.pat)}")
        print(f"DEBUG: Params: {params}")
        response = requests.request(method, url, headers=merged_headers, params=params, **kwargs)
        print(f"DEBUG: Response status: {response.status_code}")
        if response.status_code != 200:
            print("DEBUG: Response content (first 500 chars):", response.text[:500])
        response.raise_for_status()
        try:
            return response.json()
        except Exception as exc:
            raise ValueError(
                f"Expected JSON from {url}, but got: {response.text[:500]}"
            ) from exc

    def list_wikis(self) -> List[Dict[str, Any]]:
        url = f"{self._base_url}/wikis"
        params = {"api-version": self.api_version}
        print(f"DEBUG: list_wikis() URL: {url} Params: {params}")
        data = self._request("GET", url, params=params)
        return data.get("value", [])

    def list_pages(self, wiki_identifier: str) -> List[Dict[str, Any]]:
        wiki_identifier = wiki_identifier.lstrip("/").rstrip("/")
        url = f"{self._base_url}/wikis/{wiki_identifier}/pages"
        params = {
            "api-version": self.api_version,
            "recursionLevel": "full"
        }
        print(f"DEBUG: list_pages() using wiki_identifier: {wiki_identifier}")
        print(f"DEBUG: Full URL: {url} Params: {params}")
        data = self._request("GET", url, params=params)
        print(f"DEBUG: Pages returned: {len(data.get('value', []))}")
        return data.get("value", [])

    def get_page_content(
        self,
        wiki_identifier: str,
        *,
        page_path: Optional[str] = None,
        page_id: Optional[int] = None,
    ) -> Optional[str]:
        wiki_identifier = wiki_identifier.lstrip("/").rstrip("/")
        params = {
            "includeContent": "true",
            "api-version": self.api_version,
        }
        if page_path is not None:
            encoded_path = quote(page_path, safe="/")
            url = f"{self._base_url}/wikis/{wiki_identifier}/pages"
            params["path"] = encoded_path
        else:
            url = f"{self._base_url}/wikis/{wiki_identifier}/pages/{page_id}"
        data = self._request("GET", url, params=params)
        return data.get("content")

    def crawl_wiki(self, wiki_identifier: str) -> List[Dict[str, Any]]:
        pages = self.list_pages(wiki_identifier)
        results: List[Dict[str, Any]] = []
        for page in pages:
            path = page.get("path")
            if not path:
                continue
            try:
                content = self.get_page_content(
                    wiki_identifier, page_path=path
                )
                results.append({"path": path, "content": content})
            except Exception as exc:
                results.append(
                    {
                        "path": path,
                        "content": None,
                        "error": str(exc),
                    }
                )
        return results

