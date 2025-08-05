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
        api_version: str = "7.1-preview.2",
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
        print(f"DEBUG: Calling Azure DevOps URL: {url}")
        print(f"DEBUG: Method: {method}")
        print(f"DEBUG: Org: {self.org}, Project: {self.project}, PAT Set: {bool(self.pat)}")
        response = requests.request(method, url, headers=merged_headers, **kwargs)
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
        url = f"{self._base_url}/wikis?api-version={self.api_version}"
        print(f"DEBUG: list_wikis() URL: {url}")
        data = self._request("GET", url)
        return data.get("value", [])

    def list_pages(self, wiki_identifier: str) -> List[Dict[str, Any]]:
        # recursionLevel=full for all pages
        url = (
            f"{self._base_url}/wikis/{wiki_identifier}/pages"
            f"?api-version={self.api_version}&recursionLevel=full"
        )
        print(f"DEBUG: list_pages() using wiki_identifier: {wiki_identifier}")
        print(f"DEBUG: Full URL: {url}")
        data = self._request("GET", url)
        return data.get("value", [])

    def get_page_content(
        self,
        wiki_identifier: str,
        *,
        page_path: Optional[str] = None,
        page_id: Optional[int] = None,
    ) -> Optional[str]:
        if (page_path is None and page_id is None) or (page_path and page_id):
            raise ValueError(
                "Exactly one of page_path or page_id must be supplied to get_page_content"
            )
        params = {
            "includeContent": "true",
            "api-version": self.api_version,
        }
        if page_path is not None:
            encoded_path = quote(page_path, safe="/")
            url = f"{self._base_url}/wikis/{wiki_identifier}/pages?path={encoded_path}"
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

