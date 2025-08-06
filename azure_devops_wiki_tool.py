import requests

class AzureDevOpsWikiTool:
    def __init__(self, org, project, pat):
        self.org = org
        self.project = project
        self.pat = pat
        self.api_version = "7.1-preview.1"
        self._base_url = f"https://dev.azure.com/{self.org}/{self.project}/_apis/wiki"

    def _request(self, method, url, params=None):
        print(f"DEBUG: Calling Azure DevOps URL: {url}")
        print(f"DEBUG: Method: {method}")
        print(f"DEBUG: Org: {self.org}, Project: {self.project}, PAT Set: {bool(self.pat)}")
        print(f"DEBUG: Params: {params}")
        response = requests.request(
            method,
            url,
            params=params,
            auth=("", self.pat),
        )
        print(f"DEBUG: Response status: {response.status_code}")
        response.raise_for_status()
        return response.json()

    def list_wikis(self):
        url = f"{self._base_url}/wikis?api-version={self.api_version}"
        data = self._request("GET", url)
        return data["value"]

    def list_pages(self, wiki_identifier: str):
        wiki_identifier = wiki_identifier.lstrip("/").rstrip("/")
        url = (
            f"{self._base_url}/wikis/{wiki_identifier}/pages"
        )
        params = {
            "api-version": self.api_version,
            "recursionLevel": "full"
        }
        print(f"DEBUG: list_pages() using wiki_identifier: {wiki_identifier}")
        print(f"DEBUG: Full URL: {url} Params: {params}")
        data = self._request("GET", url, params=params)
        print(f"DEBUG: RAW RESPONSE JSON: {data}")
        return data  # <--- Return exactly what Azure returns (nested)



