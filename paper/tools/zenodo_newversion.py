#!/usr/bin/env python3
"""Publish a new version of the paper's Zenodo record (the concept DOI stays the same).

Creates a new-version draft of ``RECORD_ID``, replaces its files with the paper PDF and
the LaTeX source archive, sets the version label and today's publication date (and, with
``--code-url``, the code link), makes the PDF the record's default preview, and --
only with ``--publish`` -- publishes it and writes the new record's metadata to
``tools/zenodo_record.json``. Without ``--publish`` the draft is left for review on
Zenodo. Never creates a new record.

    make source                                     # build/source.tar.gz
    python tools/zenodo_newversion.py 24312265 v7   # draft only
    python tools/zenodo_newversion.py 24312265 v7 --publish

The token is read from ``$ZENODO_TOKEN`` or from the file named by ``--token-file`` /
``$ZENODO_TOKEN_FILE``; it is never printed.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import urllib.request
from pathlib import Path
from typing import Any

PAPER_DIR = Path(__file__).resolve().parent.parent
API = "https://zenodo.org/api/deposit/depositions"
RDM = "https://zenodo.org/api/records"  # InvenioRDM API (needed for the default preview file)
RDM_JSON = "application/vnd.inveniordm.v1+json"
GITHUB_URL = re.compile(r"https://github\.com/[\w.-]+/[\w.-]+")
DEFAULT_TOKEN_FILE = "~/.config/agents/zenodo_token"


def read_token(token_file: str) -> str:
    token = os.environ.get("ZENODO_TOKEN", "").strip()
    if token:
        return token
    path = Path(token_file).expanduser()
    if not path.is_file():
        sys.exit(f"no Zenodo token: set ZENODO_TOKEN or ZENODO_TOKEN_FILE (looked for {path})")
    return path.read_text().strip()


class Zenodo:
    """Minimal client for the legacy deposition API."""

    def __init__(self, token: str) -> None:
        self._auth = {"Authorization": f"Bearer {token}"}

    def request(
        self,
        url: str,
        data: bytes | None = None,
        method: str = "GET",
        ctype: str = "application/json",
        accept: str | None = None,
    ) -> Any:
        headers = {**self._auth, **({"Content-Type": ctype} if data is not None else {})}
        if accept:
            headers["Accept"] = accept
        req = urllib.request.Request(url, data=data, method=method, headers=headers)
        with urllib.request.urlopen(req, timeout=300) as resp:
            body = resp.read()
        return json.loads(body) if body else {}

    def upload(self, bucket: str, name: str, path: Path) -> None:
        self.request(f"{bucket}/{name}", path.read_bytes(), "PUT", "application/octet-stream")


def set_code_url(meta: dict[str, Any], url: str) -> None:
    """Point the 'is supplemented by' software link and the description's code link at ``url``."""
    rel = [r for r in meta.get("related_identifiers", []) if "github.com/" not in r.get("identifier", "")]
    rel.append({"identifier": url, "relation": "isSupplementedBy", "resource_type": "software", "scheme": "url"})
    meta["related_identifiers"] = rel
    shown = url.removeprefix("https://")
    desc = GITHUB_URL.sub(url, meta.get("description", ""))
    meta["description"] = re.sub(r">github\.com/[\w.-]+/[\w.-]+<", f">{shown}<", desc)


def set_default_preview(z: Zenodo, record_id: int | str, filename: str, *, published: bool) -> None:
    """Make ``filename`` the file previewed on the record page (InvenioRDM ``files.default_preview``)."""
    if published:  # editing a published record opens a draft of the same version (no new version)
        z.request(f"{RDM}/{record_id}/draft", b"", "POST", accept=RDM_JSON)
    draft = z.request(f"{RDM}/{record_id}/draft", accept=RDM_JSON)
    draft.setdefault("files", {})["default_preview"] = filename
    body = {k: draft[k] for k in ("metadata", "files", "access", "pids", "custom_fields") if k in draft}
    z.request(f"{RDM}/{record_id}/draft", json.dumps(body).encode(), "PUT", RDM_JSON, accept=RDM_JSON)
    if published:
        z.request(f"{RDM}/{record_id}/draft/actions/publish", b"", "POST", accept=RDM_JSON)


def default_preview(z: Zenodo, record_id: int | str) -> str | None:
    return z.request(f"{RDM}/{record_id}", accept=RDM_JSON).get("files", {}).get("default_preview")


def new_version(
    z: Zenodo,
    record_id: str,
    label: str,
    pdf: Path,
    source: Path,
    publish: bool,
    code_url: str | None = None,
) -> dict[str, Any]:
    nv = z.request(f"{API}/{record_id}/actions/newversion", b"", "POST")
    draft = z.request(nv["links"]["latest_draft"])
    print("draft", draft["id"], draft["links"].get("html", ""))
    for f in draft.get("files", []):
        z.request(f"{API}/{draft['id']}/files/{f['id']}", None, "DELETE")
    z.upload(draft["links"]["bucket"], pdf.name, pdf)
    z.upload(draft["links"]["bucket"], "source.tar.gz", source)
    meta = draft["metadata"]
    meta["version"] = label
    meta["publication_date"] = dt.date.today().isoformat()
    meta.pop("doi", None)
    if code_url:
        set_code_url(meta, code_url)
    z.request(f"{API}/{draft['id']}", json.dumps({"metadata": meta}).encode(), "PUT")
    print("files", [f["filename"] for f in z.request(f"{API}/{draft['id']}")["files"]])
    try:
        set_default_preview(z, draft["id"], pdf.name, published=False)
    except Exception as e:  # retried after publishing
        print("could not set the default preview on the draft:", type(e).__name__)
    if not publish:
        print("draft left unpublished (pass --publish to publish)")
        return draft
    d = z.request(f"{API}/{draft['id']}/actions/publish", b"", "POST")
    print("PUBLISHED", d.get("doi"), d.get("conceptdoi"), d["links"].get("record_html") or d["links"].get("html"))
    if default_preview(z, d["id"]) != pdf.name:
        set_default_preview(z, d["id"], pdf.name, published=True)
    print("default preview:", default_preview(z, d["id"]))
    return d


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("record_id", help="id of the latest published version (see tools/zenodo_record.json)")
    ap.add_argument("version", help="version label, e.g. v7")
    ap.add_argument("--pdf", type=Path, default=PAPER_DIR / "Chu_2026_Illustrated_NeurIPS.pdf")
    ap.add_argument("--source", type=Path, default=PAPER_DIR / "build" / "source.tar.gz", help="LaTeX source archive")
    ap.add_argument("--record-out", type=Path, default=PAPER_DIR / "tools" / "zenodo_record.json")
    ap.add_argument("--token-file", default=os.environ.get("ZENODO_TOKEN_FILE", DEFAULT_TOKEN_FILE))
    ap.add_argument("--code-url", help="set the record's code link (related identifier and description)")
    ap.add_argument("--publish", action="store_true", help="publish the new version (irreversible)")
    args = ap.parse_args(argv)
    for f in (args.pdf, args.source):
        if not f.is_file():
            sys.exit(f"missing {f} (run `make pdf source` first)")

    d = new_version(
        Zenodo(read_token(args.token_file)), args.record_id, args.version, args.pdf, args.source, args.publish
    )
    if args.publish:
        record = {k: d.get(k) for k in ("id", "doi", "conceptdoi")} | {"version": args.version, "links": d["links"]}
        args.record_out.write_text(json.dumps(record, indent=1) + "\n")
        print("wrote", args.record_out)


if __name__ == "__main__":
    main()
