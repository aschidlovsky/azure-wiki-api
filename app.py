import os
import logging
from flask import Flask, request, jsonify
import requests
from base64 import b64encode

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

app = Flask(__name__)

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

@app.route('/wikis', methods=['GET'])
def list_wikis():
    url = f"{az_base_url()}/wiki/wikis?api-version=7.1-preview.1"
    headers = get_auth_header()
    logging.info(f"Requesting: {url}")
    resp = requests.get(url, headers=headers)
    logging.info(f"Response [{resp.status_code}]: {resp.text[:300]}")
    if resp.status_code != 200:
        return jsonify({"error": resp.text}), resp.status_code
    return jsonify(resp.json().get('value', [])), 200

@app.route('/pages', methods=['GET'])
def list_pages():
    wiki_id = request.args.get("wiki")
    if not wiki_id:
        return jsonify({"error": "Missing 'wiki' parameter"}), 400
    url = f"{az_base_url()}/wiki/wikis/{wiki_id}/pages"
    params = {"api-version": "7.1-preview.1", "recursionLevel": "full"}
    headers = get_auth_header()
    logging.info(f"Requesting: {url} params={params}")
    resp = requests.get(url, headers=headers, params=params)
    logging.info(f"Response [{resp.status_code}]: {resp.text[:300]}")
    if resp.status_code != 200:
        return jsonify({"error": resp.text}), resp.status_code
    return jsonify(resp.json()), 200

@app.route('/page', methods=['GET', 'POST', 'PUT', 'DELETE'])
def page_ops():
    wiki = request.args.get("wiki") or (request.json.get("wiki") if request.json else None)
    path = request.args.get("path") or (request.json.get("path") if request.json else None)
    page_id = request.args.get("id") or (request.json.get("id") if request.json else None)
    headers = get_auth_header()

    # --- GET ---
    if request.method == 'GET':
        if not wiki:
            return jsonify({"error": "Missing 'wiki' parameter"}), 400
        if not path and not page_id:
            return jsonify({"error": "Provide 'path' or 'id'"}), 400
        base = f"{az_base_url()}/wiki/wikis/{wiki}/pages"
        params = {"api-version": "7.1-preview.1"}
        if page_id:
            url = f"{base}/{page_id}"
        else:
            url = base
            params["path"] = path
        logging.info(f"Requesting page: {url} params={params}")
        resp = requests.get(url, headers=headers, params=params)
        logging.info(f"Response [{resp.status_code}]: {resp.text[:300]}")
        if resp.status_code != 200:
            return jsonify({"error": resp.text}), resp.status_code
        return jsonify({"content": resp.json().get("content", "")}), 200

    # --- POST (Create) ---
    if request.method == 'POST':
        data = request.json
        content = data.get("content")
        if not (wiki and path and content):
            return jsonify({"error": "wiki, path, and content required"}), 400
        url = f"{az_base_url()}/wiki/wikis/{wiki}/pages"
        params = {"api-version": "7.1-preview.1", "path": path}
        payload = {"content": content, "comment": data.get("comment", "Created via API")}
        logging.info(f"Creating page: {url} params={params} payload={payload}")
        resp = requests.put(url, headers=headers, params=params, json=payload)
        logging.info(f"Response [{resp.status_code}]: {resp.text[:300]}")
        if resp.status_code not in (200, 201):
            return jsonify({"error": resp.text}), resp.status_code
        return jsonify({"message": "Page created"}), 201

    # --- PUT (Update) ---
    if request.method == 'PUT':
        data = request.json
        content = data.get("content")
        if not (wiki and path and content):
            return jsonify({"error": "wiki, path, and content required"}), 400
        url = f"{az_base_url()}/wiki/wikis/{wiki}/pages"
        params = {"api-version": "7.1-preview.1", "path": path}
        payload = {"content": content, "comment": data.get("comment", "Updated via API")}
        logging.info(f"Updating page: {url} params={params} payload={payload}")
        resp = requests.put(url, headers=headers, params=params, json=payload)
        logging.info(f"Response [{resp.status_code}]: {resp.text[:300]}")
        if resp.status_code not in (200, 201):
            return jsonify({"error": resp.text}), resp.status_code
        return jsonify({"message": "Page updated"}), 200

    # --- DELETE ---
    if request.method == 'DELETE':
        if not (wiki and path):
            return jsonify({"error": "wiki and path required"}), 400
        url = f"{az_base_url()}/wiki/wikis/{wiki}/pages"
        params = {"api-version": "7.1-preview.1", "path": path}
        logging.info(f"Deleting page: {url} params={params}")
        resp = requests.delete(url, headers=headers, params=params)
        logging.info(f"Response [{resp.status_code}]: {resp.text[:300]}")
        if resp.status_code != 204:
            return jsonify({"error": resp.text}), resp.status_code
        return jsonify({"message": "Page deleted"}), 204

@app.route('/search', methods=['GET', 'POST'])
def search_pages():
    # Allow GET for backwards compatibility but recommend POST!
    if request.method == 'POST':
        data = request.json or {}
        wiki = data.get("wiki")
        query = data.get("q") or data.get("query") or data.get("searchText")
    else:
        wiki = request.args.get("wiki")
        query = request.args.get("q")
    logging.info(f"/search called with wiki={wiki}, q={query}")

    if not (wiki and query):
        return jsonify({"error": "wiki and q required"}), 400

    # CORRECT endpoint and domain for search
    url = f"https://almsearch.dev.azure.com/{AZURE_DEVOPS_ORG}/{AZURE_DEVOPS_PROJECT}/_apis/search/wikisearchresults"
    params = {"api-version": "7.1", "project": AZURE_DEVOPS_PROJECT}
    headers = get_auth_header()
    payload = {
        "searchText": query,
        "wikiId": wiki
    }

    logging.info(f"POSTing search to: {url} params={params} payload={payload}")
    resp = requests.post(url, headers=headers, params=params, json=payload)
    logging.info(f"Azure response [{resp.status_code}]: {resp.text[:500]}")
    if resp.status_code != 200:
        return jsonify({"error": resp.text}), resp.status_code

    try:
        data = resp.json()
    except Exception as ex:
        logging.exception("Failed to parse search response as JSON")
        return jsonify({"error": "Failed to parse search response"}), 500

    results = []
    for res in data.get("results", []):
        results.append({
            "path": res.get("path"),
            "snippet": (res.get("highlights") or [""])[0]
        })
    return jsonify(results), 200

@app.route('/attachments', methods=['GET'])
def list_attachments():
    wiki = request.args.get("wiki")
    if not wiki:
        return jsonify({"error": "wiki required"}), 400
    url = f"{az_base_url()}/wiki/wikis/{wiki}/attachments?api-version=7.1-preview.1"
    headers = get_auth_header()
    logging.info(f"Requesting: {url}")
    resp = requests.get(url, headers=headers)
    logging.info(f"Response [{resp.status_code}]: {resp.text[:300]}")
    if resp.status_code != 200:
        return jsonify({"error": resp.text}), resp.status_code
    return jsonify(resp.json().get('value', [])), 200

@app.route('/attachment', methods=['POST'])
def upload_attachment():
    wiki = request.form.get("wiki")
    file = request.files.get("file")
    if not wiki or not file:
        return jsonify({"error": "wiki and file required"}), 400
    url = f"{az_base_url()}/wiki/wikis/{wiki}/attachments?api-version=7.1-preview.1"
    headers = get_auth_header()
    headers.pop("Content-Type", None)
    files = {"file": (file.filename, file.stream, file.mimetype)}
    logging.info(f"Uploading attachment: {file.filename} to wiki {wiki}")
    resp = requests.post(url, headers=headers, files=files)
    logging.info(f"Response [{resp.status_code}]: {resp.text[:300]}")
    if resp.status_code not in (200, 201):
        return jsonify({"error": resp.text}), resp.status_code
    return jsonify(resp.json()), 201

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.getenv("PORT", "8080")))

