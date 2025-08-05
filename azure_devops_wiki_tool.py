"""
Azure DevOps Wiki Tool
=======================

This module provides a simple interface for interacting with the Azure DevOps
Wiki REST API. It allows you to list wikis, list pages within a wiki,
retrieve the content of individual pages, create or update wiki pages,
crawl an entire wiki, and perform basic keyword searches over wiki
content. The intent is to make it easy for a language model or any
automation to fetch and manage contextual information from Azure DevOps
wikis.

Authentication
---------------

The API requires a Personal Access Token (PAT) with access to the Wiki
features of your organization and project. The PAT should be provided via
environment variables or passed directly when instantiating the
``AzureDevOpsWikiTool``. For convenience, the constructor will look for the
following environment variables if the parameters are not provided:

- ``AZURE_DEVOPS_ORG``: Your Azure DevOps organization name.
- ``AZURE_DEVOPS_PROJECT``: Your Azure DevOps project name.
- ``AZURE_DEVOPS_PAT``: A PAT with Wiki read permissions.

Usage
-----

The class exposes several methods to interact with the Wiki API. See the
docstrings on each method for details. A simple command-line interface is
provided when run as a script, allowing you to test the functionality
directly.

Example:

.. code:: shell

    # List all wikis in the configured organization/project
    python azure_devops_wiki_tool.py list-wikis

    # List pages in a specific wiki
    python azure_devops_wiki_tool.py list-pages --wiki MyWiki

    # Fetch the content of a page by path
    python azure_devops_wiki_tool.py get-page --wiki MyWiki --path /Home

    # Crawl an entire wiki and write the results to a JSON file
    python azure_devops_wiki_tool.py crawl --wiki MyWiki --output wiki_dump.json

    # Search for a keyword across a wiki's pages
    python azure_devops_wiki_tool.py search --wiki MyWiki --keyword "architecture"

This module depends on the ``requests`` library.
"""

import base64
import json
import os
from typing import List, Dict, Optional, Any

import requests
from urllib.parse import quote


class AzureDevOpsWikiTool:
    """A helper for interacting with the Azure DevOps Wiki REST API.

    Parameters
    ----------
    org : str, optional
        The Azure DevOps organization name. If not provided, the constructor
        will attempt to read it from the ``AZURE_DEVOPS_ORG`` environment variable.
    project : str, optional
        The Azure DevOps project name. If not provided, the constructor
        will attempt to read it from the ``AZURE_DEVOPS_PROJECT`` environment variable.
    pat : str, optional
        A Personal Access Token with Wiki read permissions. If not provided,
        the constructor will attempt to read it from the ``AZURE_DEVOPS_PAT``
        environment variable.
    api_version : str, optional
        The API version to use when communicating with Azure DevOps. Defaults
        to ``"7.1-preview.2"``.

    Raises
    ------
    ValueError
        If any of ``org``, ``project``, or ``pat`` are missing.
    """

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
                "Organization, project, and PAT must all be provided either via parameters or environment variables"
            )

        # Prepare the basic auth header. Azure DevOps PATs are used as the
        # password with an empty username.
        pat_bytes = f":{self.pat}".encode()
        self._headers = {
            "Authorization": "Basic " + base64.b64encode(pat_bytes).decode(),
        }

        self._base_url = (
            f"https://dev.azure.com/{self.org}/{self.project}/_apis/wiki"
        )

    def _request(self, method: str, url: str, **kwargs: Any) -> Dict[str, Any]:
        """Internal helper to perform an HTTP request with authentication.

        Parameters
        ----------
        method : str
            The HTTP method (e.g. "GET").
        url : str
            The full URL to request.
        **kwargs
            Additional keyword arguments forwarded to ``requests.request``.

        Returns
        -------
        dict
            The JSON-decoded response body.

        Raises
        ------
        requests.HTTPError
            If the request returns an unsuccessful status code.
        ValueError
            If the response cannot be parsed as JSON.
        """
        headers = kwargs.pop("headers", {})
        # Merge user-provided headers with auth header, preferring user headers
        merged_headers = {**self._headers, **headers}
        response = requests.request(method, url, headers=merged_headers, **kwargs)
        response.raise_for_status()
        try:
            return response.json()
        except ValueError as exc:
            raise ValueError(
                f"Expected JSON response from {url}, but could not decode it"
            ) from exc

    def list_wikis(self) -> List[Dict[str, Any]]:
        """Retrieve all wikis in the configured project.

        Returns
        -------
        list of dict
            A list of wiki metadata objects. Each object contains information
            such as ``id`` and ``name``.
        """
        url = f"{self._base_url}/wikis?api-version={self.api_version}"
        data = self._request("GET", url)
        return data.get("value", [])

    def list_pages(self, wiki_identifier: str) -> List[Dict[str, Any]]:
        """List pages within a specific wiki.

        Parameters
        ----------
        wiki_identifier : str
            The name or ID of the wiki to query.

        Returns
        -------
        list of dict
            A list of page metadata objects containing keys such as ``path`` and ``id``.
        """
        url = f"{self._base_url}/wikis/{wiki_identifier}/pages?api-version={self.api_version}"
        data = self._request("GET", url)
        return data.get("value", [])

    def get_page_content(
        self,
        wiki_identifier: str,
        *,
        page_path: Optional[str] = None,
        page_id: Optional[int] = None,
    ) -> Optional[str]:
        """Retrieve the content of a wiki page.

        You must provide either ``page_path`` or ``page_id``, but not both.

        Parameters
        ----------
        wiki_identifier : str
            The wiki name or ID.
        page_path : str, optional
            The path to the page (e.g., ``/Home/GettingStarted``).
        page_id : int, optional
            The numeric ID of the page.

        Returns
        -------
        str or None
            The page content as a string, or ``None`` if the content could not be retrieved.

        Raises
        ------
        ValueError
            If neither or both of ``page_path`` and ``page_id`` are provided.
        requests.HTTPError
            If the API request fails.
        """
        if (page_path is None and page_id is None) or (page_path and page_id):
            raise ValueError(
                "Exactly one of page_path or page_id must be supplied to get_page_content"
            )

        params = {"includeContent": "true", "api-version": self.api_version}

        if page_path is not None:
            # Encode the path to ensure special characters are properly escaped.
            encoded_path = quote(page_path, safe="/")
            url = f"{self._base_url}/wikis/{wiki_identifier}/pages?path={encoded_path}"
        else:
            url = f"{self._base_url}/wikis/{wiki_identifier}/pages/{page_id}"

        data = self._request("GET", url, params=params)
        # The Azure DevOps API returns the page's text content under the "content" key.
        return data.get("content")

    def crawl_wiki(self, wiki_identifier: str) -> List[Dict[str, Any]]:
        """Retrieve the content of every page in a wiki.

        Parameters
        ----------
        wiki_identifier : str
            The name or ID of the wiki to crawl.

        Returns
        -------
        list of dict
            A list of objects, each containing the ``path`` and ``content`` of a page.
            If a page could not be fetched, the ``content`` value will be ``None``
            and an ``error`` key will describe the failure.
        """
        pages = self.list_pages(wiki_identifier)
        results: List[Dict[str, Any]] = []
        for page in pages:
            path = page.get("path")
            # Skip if path is missing for some reason
            if not path:
                continue
            try:
                content = self.get_page_content(
                    wiki_identifier, page_path=path
                )
                results.append({"path": path, "content": content})
            except Exception as exc:  # broad except to capture network errors etc.
                results.append(
                    {
                        "path": path,
                        "content": None,
                        "error": str(exc),
                    }
                )
        return results

    def search_keyword(
        self, wiki_identifier: str, keyword: str
    ) -> List[Dict[str, Any]]:
        """Search for a keyword within all pages of a wiki.

        This performs a simple substring match (case-insensitive) over the
        content of every page in the specified wiki. It can be used as a
        lightweight way to find relevant pages before feeding their content
        into a language model.

        Parameters
        ----------
        wiki_identifier : str
            The wiki name or ID.
        keyword : str
            The keyword to search for. Search is case-insensitive.

        Returns
        -------
        list of dict
            A list of objects for each page containing the keyword. Each
            object includes the ``path`` and ``content`` keys.
        """
        keyword_lower = keyword.lower()
        matches: List[Dict[str, Any]] = []
        pages = self.crawl_wiki(wiki_identifier)
        for entry in pages:
            content = entry.get("content") or ""
            if keyword_lower in content.lower():
                matches.append(entry)
        return matches

    def create_or_update_page(
        self,
        wiki_identifier: str,
        path: str,
        content: str,
        *,
        comment: Optional[str] = None,
        etag: Optional[str] = None,
        version_descriptor: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Create a new wiki page or update an existing one.

        This method uses the Azure DevOps ``Pages - Create Or Update`` endpoint
        (HTTP ``PUT``) to create a page when it does not exist or to edit an
        existing page at the given path. For updates, you may optionally
        specify the page's current ETag via the ``etag`` parameter. Including
        the ETag helps prevent accidental overwrites when concurrent edits
        occur, although the REST API will also perform the operation without
        the ETag header.

        Parameters
        ----------
        wiki_identifier : str
            The wiki name or ID.
        path : str
            The wiki page path (e.g. ``/Home/MyPage``). This path should not
            contain file extensions; the wiki will manage the underlying
            `.md` file.
        content : str
            The full content of the page to create or update. The API
            overwrites the entire page with the provided content.
        comment : str, optional
            A comment describing the change. This appears in the page's
            history. If omitted, no comment is recorded.
        etag : str, optional
            The current ETag of the page. If provided, it is passed via
            ``If-Match`` header to ensure that the update only succeeds if
            the ETag matches. You can retrieve the ETag by performing a
            ``get_page_content`` call and inspecting the ``ETag`` header of
            the response using the ``return_headers`` flag.
        version_descriptor : dict, optional
            A dictionary specifying version parameters (``version``,
            ``versionOptions``, ``versionType``). These are used to
            identify specific branches or commits in a code-backed wiki. Most
            users can leave this unset.

        Returns
        -------
        dict
            The JSON response from the API, containing metadata about the
            created or updated page.

        Notes
        -----
        - Creating or updating pages requires ``vso.wiki_write`` scope on
          your PAT. Without this, the API will return a 401 or 403 error.
        - The API call uses a ``PUT`` request. When a page does not exist,
          the response status code is ``201`` (Created). When the page
          already exists, the response status code is ``200`` (OK).

        Examples
        --------

        ``tool.create_or_update_page("MyWiki", "/NewPage", "Hello world")``
            Create a new page named ``NewPage`` at the root of the wiki.

        ``tool.create_or_update_page("MyWiki", "/Existing", "Updated content", etag="4c6adda...")``
            Update an existing page using its ETag to prevent clobbering
            concurrent changes.
        """
        # Construct the request URL and parameters
        params = {"api-version": self.api_version, "path": path}
        if comment:
            params["comment"] = comment
        if version_descriptor:
            # Flatten the version descriptor into query parameters
            if "version" in version_descriptor:
                params["versionDescriptor.version"] = version_descriptor["version"]
            if "versionOptions" in version_descriptor:
                params["versionDescriptor.versionOptions"] = version_descriptor["versionOptions"]
            if "versionType" in version_descriptor:
                params["versionDescriptor.versionType"] = version_descriptor["versionType"]

        url = f"{self._base_url}/wikis/{wiki_identifier}/pages"

        # Build headers. Copy the auth header so we don't mutate the instance's
        # headers. If an ETag is provided, include it in an If-Match header.
        headers = dict(self._headers)
        if etag:
            headers["If-Match"] = etag

        payload = {"content": content}
        response = requests.put(url, params=params, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()


def _main() -> None:
    """CLI entry point for the module.

    This function parses command-line arguments and invokes the appropriate
    methods on ``AzureDevOpsWikiTool``. The results are printed as pretty-
    formatted JSON or written to a file if the ``--output`` option is
    provided.
    """
    import argparse
    parser = argparse.ArgumentParser(description="Interact with Azure DevOps Wiki via REST API")
    parser.add_argument(
        "command",
        choices=[
            "list-wikis",
            "list-pages",
            "get-page",
            "crawl",
            "search",
            "create-page",
            "update-page",
        ],
        help="Operation to perform",
    )
    parser.add_argument(
        "--wiki",
        help="Wiki identifier (name or ID) for operations that require it",
    )
    parser.add_argument(
        "--path",
        help="Page path when using the get-page command (e.g. /Home/GettingStarted)",
    )
    parser.add_argument(
        "--page-id",
        type=int,
        help="Page ID when using the get-page command",
    )
    parser.add_argument(
        "--keyword",
        help="Keyword to search for when using the search command",
    )
    parser.add_argument(
        "--output",
        help="Write the JSON result to this file instead of printing",
    )

    # Flags for create/update page operations
    parser.add_argument(
        "--content",
        help="Raw content to write when creating or updating a page",
    )
    parser.add_argument(
        "--content-file",
        help="Path to a file containing the page content. Used when creating or updating a page",
    )
    parser.add_argument(
        "--comment",
        help="Comment describing the change. Used when creating or updating a page",
    )
    parser.add_argument(
        "--etag",
        help="ETag for the existing page. Include this to protect against concurrent updates when updating a page",
    )

    args = parser.parse_args()
    tool = AzureDevOpsWikiTool()
    result: Any = None

    try:
        if args.command == "list-wikis":
            result = tool.list_wikis()
        elif args.command == "list-pages":
            if not args.wiki:
                raise SystemExit("The list-pages command requires --wiki")
            result = tool.list_pages(args.wiki)
        elif args.command == "get-page":
            if not args.wiki:
                raise SystemExit("The get-page command requires --wiki")
            if args.path:
                result = tool.get_page_content(args.wiki, page_path=args.path)
            elif args.page_id is not None:
                result = tool.get_page_content(args.wiki, page_id=args.page_id)
            else:
                raise SystemExit("The get-page command requires --path or --page-id")
        elif args.command == "crawl":
            if not args.wiki:
                raise SystemExit("The crawl command requires --wiki")
            result = tool.crawl_wiki(args.wiki)
        elif args.command == "search":
            if not args.wiki or not args.keyword:
                raise SystemExit("The search command requires both --wiki and --keyword")
            result = tool.search_keyword(args.wiki, args.keyword)
        elif args.command in {"create-page", "update-page"}:
            # Both create-page and update-page share the same logic. Only the presence
            # of an ETag distinguishes them. For create-page, the ETag is
            # typically omitted; for update-page, it can be provided via --etag.
            if not args.wiki or not args.path:
                raise SystemExit("The create-page and update-page commands require --wiki and --path")
            # Determine the content: either directly from --content or read from --content-file
            if args.content and args.content_file:
                raise SystemExit("Specify either --content or --content-file, not both")
            if args.content_file:
                try:
                    with open(args.content_file, "r", encoding="utf-8") as f:
                        page_content = f.read()
                except Exception as exc:
                    raise SystemExit(f"Failed to read content from {args.content_file}: {exc}") from exc
            elif args.content:
                page_content = args.content
            else:
                raise SystemExit("You must provide page content via --content or --content-file")
            # For update-page, pass the ETag if provided; for create-page, etag is optional (ignored if None)
            result = tool.create_or_update_page(
                args.wiki,
                args.path,
                page_content,
                comment=args.comment,
                etag=args.etag,
            )
    except requests.HTTPError as exc:
        # Provide a friendly error message on HTTP failures
        status = exc.response.status_code
        message = exc.response.text
        raise SystemExit(f"HTTP error {status}: {message}") from exc

    # Output handling
    if args.output:
        # Write the result as JSON to the specified file
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
        print(f"Result written to {args.output}")
    else:
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    _main()