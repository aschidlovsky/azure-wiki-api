import os
from flask import Flask, request, jsonify
from azure_devops_wiki_tool import AzureDevOpsWikiTool

print("Starting app...")
print("ORG:", os.environ.get("AZURE_DEVOPS_ORG"))
print("PROJECT:", os.environ.get("AZURE_DEVOPS_PROJECT"))
print("PAT present:", bool(os.environ.get("AZURE_DEVOPS_PAT")))
print("PORT ENV:", os.environ.get("PORT"))

app = Flask(__name__)

wiki_tool = AzureDevOpsWikiTool(
    org=os.environ["AZURE_DEVOPS_ORG"],
    project=os.environ["AZURE_DEVOPS_PROJECT"],
    pat=os.environ["AZURE_DEVOPS_PAT"],
)

@app.route("/", methods=["GET"])
def index():
    return "OK", 200

@app.route("/debug-env", methods=["GET"])
def debug_env():
    return jsonify({
        "ORG": os.environ.get("AZURE_DEVOPS_ORG"),
        "PROJECT": os.environ.get("AZURE_DEVOPS_PROJECT"),
        "PAT_present": bool(os.environ.get("AZURE_DEVOPS_PAT")),
        "PORT": os.environ.get("PORT"),
    })

@app.route("/wikis", methods=["GET"])
def list_wikis():
    try:
        return jsonify(wiki_tool.list_wikis())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/pages", methods=["GET"])
def list_pages_route():
    wiki = request.args.get("wiki")
    if not wiki:
        return jsonify({"error": "wiki param required"}), 400
    try:
        return jsonify(wiki_tool.list_pages(wiki))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/page", methods=["GET"])
def get_page():
    wiki = request.args.get("wiki")
    page_path = request.args.get("path")
    page_id = request.args.get("id")
    if not wiki or (not page_path and not page_id):
        return jsonify({"error": "wiki and (path or id) param required"}), 400
    try:
        if page_path:
            return jsonify({"content": wiki_tool.get_page_content(wiki_identifier=wiki, page_path=page_path)})
        else:
            try:
                id_int = int(page_id)
            except (TypeError, ValueError):
                return jsonify({"error": "id must be an integer"}), 400
            return jsonify({"content": wiki_tool.get_page_content(wiki_identifier=wiki, page_id=id_int)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/search", methods=["GET"])
def search_route():
    wiki = request.args.get("wiki")
    keyword = request.args.get("q")
    limit = int(request.args.get("limit", 10))
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
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)

