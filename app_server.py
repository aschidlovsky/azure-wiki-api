import os
from flask import Flask, request, jsonify
from azure_devops_wiki_tool import AzureDevOpsWikiTool

app = Flask(__name__)

wiki_tool = AzureDevOpsWikiTool(
    org=os.environ["AZURE_DEVOPS_ORG"],
    project=os.environ["AZURE_DEVOPS_PROJECT"],
    pat=os.environ["AZURE_DEVOPS_PAT"],
)

@app.route("/", methods=["GET"])
def index():
    return jsonify({"message": "Azure wiki API is running"}), 200

@app.route("/wikis", methods=["GET"])
def list_wikis():
    return jsonify(wiki_tool.list_wikis())

@app.route("/pages", methods=["GET"])
def list_pages_route():
    wiki = request.args.get("wiki")
    if not wiki:
        return jsonify({"error": "wiki param required"}), 400
    return jsonify(wiki_tool.list_pages(wiki))

@app.route("/page", methods=["GET"])
def get_page():
    wiki = request.args.get("wiki")
    page_path = request.args.get("path")
    page_id = request.args.get("id")
    if not wiki or (not page_path and not page_id):
        return jsonify({"error": "wiki and (path or id param required)"}), 400
    if page_path:
        return jsonify(wiki_tool.get_page_content(wiki_identifier=wiki, page_path=page_path))
    else:
        try:
            id_int = int(page_id)
        except (TypeError, ValueError):
            return jsonify({"error": "id must be an integer"}), 400
        return jsonify(wiki_tool.get_page_content(wiki_identifier=wiki, page_id=id_int))

@app.route("/search", methods=["GET"])
def search_route():
    wiki = request.args.get("wiki")
    keyword = request.args.get("q")
    if not wiki or not keyword:
        return jsonify({"error": "wiki and q param required"}), 400
    pages = wiki_tool.crawl_wiki(wiki)
    matches = []
    lower = keyword.lower()
    for page in pages:
        content = page.get("content") or ""
        if lower in content.lower():
            matches.append({"path": page.get("path"), "snippet": content[:250]})
    return jsonify(matches)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
