import os
import sys
from flask import Flask, request, jsonify
from azure_devops_wiki_tool import AzureDevOpsWikiTool
import requests

print("Starting app...", file=sys.stderr)
print("ORG:", os.environ.get("AZURE_DEVOPS_ORG"), file=sys.stderr)
print("PROJECT:", os.environ.get("AZURE_DEVOPS_PROJECT"), file=sys.stderr)
print("PAT present:", bool(os.environ.get("AZURE_DEVOPS_PAT")), file=sys.stderr)
print("PORT ENV:", os.environ.get("PORT"), file=sys.stderr)

app = Flask(__name__)

wiki_tool = AzureDevOpsWikiTool(
    org=os.environ["AZURE_DEVOPS_ORG"],
    project=os.environ["AZURE_DEVOPS_PROJECT"],
    pat=os.environ["AZURE_DEVOPS_PAT"],
)

@app.route("/", methods=["GET"])
def index():
    return "OK", 200

@app.route("/wikis", methods=["GET"])
def list_wikis():
    try:
        wikis = wiki_tool.list_wikis()
        return jsonify(wikis)
    except requests.HTTPError as e:
        error_body = e.response.text[:1000] if hasattr(e.response, "text") else ""
        return jsonify({"error": "Azure DevOps API error", "detail": str(e), "body": error_body}), e.response.status_code
    except Exception as e:
        return jsonify({"error": "Unhandled error", "detail": str(e)}), 500

@app.route("/pages", methods=["GET"])
def list_pages_route():
    wiki = request.args.get("wiki")
    print(f"DEBUG: /pages endpoint called with wiki param: {wiki}", file=sys.stderr)
    if not wiki:
        return jsonify({"error": "wiki param required"}), 400
    try:
        pages = wiki_tool.list_pages(wiki)
        return jsonify([
            {"path": page.get("path"), "id": page.get("id"), "order": page.get("order")}
            for page in pages
        ])
    except requests.HTTPError as e:
        error_body = e.response.text[:1000] if hasattr(e.response, "text") else ""
        return jsonify({"error": "Azure DevOps API error", "detail": str(e), "body": error_body}), e.response.status_code
    except Exception as e:
        return jsonify({"error": "Unhandled error", "detail": str(e)}), 500

@app.route("/page", methods=["GET"])
def get_page():
    wiki = request.args.get("wiki")
    page_path = request.args.get("path")
    page_id = request.args.get("id")
    if not wiki or (not page_path and not page_id):
        return jsonify({"error": "wiki and (path or id) param required"}), 400
    try:
        if page_path:
            content = wiki_tool.get_page_content(wiki_identifier=wiki, page_path=page_path)
            return jsonify({"content": content})
        else:
            try:
                id_int = int(page_id)
            except (TypeError, ValueError):
                return jsonify({"error": "id must be an integer"}), 400
            content = wiki_tool.get_page_content(wiki_identifier=wiki, page_id=id_int)
            return jsonify({"content": content})
    except requests.HTTPError as e:
        error_body = e.response.text[:1000] if hasattr(e.response, "text") else ""
        return jsonify({"error": "Azure DevOps API error", "detail": str(e), "body": error_body}), e.response.status_code
    except Exception as e:
        return jsonify({"error": "Unhandled error", "detail": str(e)}), 500

@app.route("/search", methods=["GET"])
def search_route():
    wiki = request.args.get("wiki")
    keyword = request.args.get("q")
    limit = min(int(request.args.get("limit", 10)), 50)  # Hard cap at 50 results
    print(f"DEBUG: /search endpoint called with wiki param: {wiki} and keyword: {keyword}", file=sys.stderr)
    if not wiki or not keyword:
        return jsonify({"error": "wiki and q param required"}), 400
    try:
        pages = wiki_tool.crawl_wiki(wiki)
        matches = []
        lower = keyword.lower()
        for page in pages:
            content = page.get("content") or ""
            if lower in content.lower():
                matches.append({"path": page.get("path"), "snippet": content[:250]})
            if len(matches) >= limit:
                break
        return jsonify(matches)
    except requests.HTTPError as e:
        error_body = e.response.text[:1000] if hasattr(e.response, "text") else ""
        return jsonify({"error": "Azure DevOps API error", "detail": str(e), "body": error_body}), e.response.status_code
    except Exception as e:
        return jsonify({"error": "Unhandled error", "detail": str(e)}), 500

@app.route("/debug-env")
def debug_env():
    return jsonify({
        "ORG": os.environ.get("AZURE_DEVOPS_ORG"),
        "PROJECT": os.environ.get("AZURE_DEVOPS_PROJECT"),
        "PAT_present": bool(os.environ.get("AZURE_DEVOPS_PAT"))
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
