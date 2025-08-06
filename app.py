import os
from flask import Flask, request, jsonify
from azure_devops_wiki_tool import AzureDevOpsWikiTool

app = Flask(__name__)

wiki_tool = AzureDevOpsWikiTool(
    org=os.environ["AZURE_DEVOPS_ORG"],
    project=os.environ["AZURE_DEVOPS_PROJECT"],
    pat=os.environ["AZURE_DEVOPS_PAT"],
)

@app.route("/wikis", methods=["GET"])
def list_wikis_route():
    wikis = wiki_tool.list_wikis()
    return jsonify(wikis)

@app.route("/pages", methods=["GET"])
def list_pages_route():
    wiki = request.args.get("wiki")
    if not wiki:
        return jsonify({"error": "wiki param required"}), 400
    raw = wiki_tool.list_pages(wiki)
    return jsonify(raw)  # <--- Just return as-is, keeps nested structure

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), debug=True)

