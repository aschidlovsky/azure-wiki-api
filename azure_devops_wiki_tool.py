# azure_devops_wiki_tool.py

import os
import requests
from base64 import b64encode

AZURE_DEVOPS_ORG = os.getenv("AZURE_DEVOPS_ORG")
AZURE_DEVOPS_PROJECT = os.getenv("AZURE_DEVOPS_PROJECT")
AZURE_DEVOPS_PAT = os.getenv("AZURE_DEVOPS_PAT")

def get_auth_header():
    pat_token = f":{AZURE_DEVOPS_PAT}".encode('utf-8')
    return {
        "Authorization": f"Basic {b64encode(pat_token).decode()}",
        "Content-Type": "application/json"
    }

def az_base_url():
    return f"https://dev.azure.com/{AZURE_DEVOPS_ORG}/{AZURE_DEVOPS_PROJECT}/_apis"

def list_wikis():
    """
    Returns a list of wikis for the configured project.
    """
    url = f"{az_base_url()}/wiki/wikis?api-version=7.1-preview.1"
    headers = get_auth_header()
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return resp.json().get("value", [])

def list_pages(wiki_id):
    """
    Returns the full nested page tree for a given wiki ID.
    """
    url = f"{az_base_url()}/wiki/wikis/{wiki_id}/pages"
    params = {"api-version": "7.1-preview.1", "recursionLevel": "full"}
    headers = get_auth_header()
    resp = requests.get(url, headers=headers, params=params)
    resp.raise_for_status()
    return resp.json() # Will be a nested tree

def get_page(wiki_id, path=None, page_id=None):
    """
    Fetches the content of a specific page by path or id.
    """
    base = f"{az_base_url()}/wiki/wikis/{wiki_id}/pages"
    params = {"api-version": "7.1-preview.1"}
    headers = get_auth_header()
    if page_id:
        url = f"{base}/{page_id}"
        resp = requests.get(url, headers=headers, params=params)
    elif path:
        params["path"] = path
        resp = requests.get(base, headers=headers, params=params)
    else:
        raise ValueError("Either path or page_id must be provided.")
    resp.raise_for_status()
    return resp.json().get("content", "")

def search_wiki(wiki_id, query):
    """
    Searches wiki pages for a keyword.
    """
    url = f"{az_base_url()}/search/wikisearchresults"
    params = {
        "api-version": "7.1-preview.1",
        "searchText": query,
        "wikiId": wiki_id,
        "project": AZURE_DEVOPS_PROJECT
    }
    headers = get_auth_header()
    resp = requests.get(url, headers=headers, params=params)
    resp.raise_for_status()
    results = []
    for res in resp.json().get("results", []):
        results.append({
            "path": res.get("path"),
            "snippet": (res.get("highlights") or [""])[0]
        })
    return results

# Optional: Add attachments and other endpoints as needed




