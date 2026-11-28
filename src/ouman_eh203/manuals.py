"""User-initiated manual acquisition; no bundled PDFs or background updates."""
import hashlib
import os
from pathlib import Path
import tempfile
from urllib.parse import urlsplit
from urllib.request import build_opener, HTTPRedirectHandler
from PySide6.QtPdf import QPdfDocument

DEFAULT_URLS = {lang: f"https://ouman.fi/documentbank/EH-203__manual__{lang}.pdf"
                for lang in ("fi", "en")}
MAX_BYTES = 20 * 1024 * 1024

def validate_url(url):
    p = urlsplit(url)
    if p.scheme != "https" or not p.hostname or p.username or p.password:
        raise ValueError("HTTPS URL without credentials required")
    return url

class HTTPSRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)

def bounded_read(stream):
    data = stream.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("PDF exceeds 20 MiB")
    return data

def acquire(source, remote=False):
    if remote:
        with build_opener(HTTPSRedirect()).open(validate_url(source), timeout=15) as stream:
            return bounded_read(stream)
    with open(source, "rb") as stream:
        return bounded_read(stream)

class ManualManager:
    def __init__(self, directory):
        self.directory = Path(directory)

    def path(self, lang):
        if lang not in DEFAULT_URLS:
            raise ValueError("Unknown language")
        return self.directory / f"EH-203__manual__{lang}.pdf"

    @staticmethod
    def inspect(path):
        with open(path, "rb") as stream:
            data = bounded_read(stream)
        if not data.startswith(b"%PDF-"):
            raise ValueError("Not a PDF")
        doc = QPdfDocument(None)
        try:
            if doc.load(str(path)) != QPdfDocument.Error.None_ or doc.pageCount() < 1:
                raise ValueError("Invalid or encrypted PDF")
            return doc.pageCount(), hashlib.sha256(data).hexdigest()
        finally:
            doc.close()

    def install(self, lang, data):
        target = self.path(lang)
        if len(data) > MAX_BYTES:
            raise ValueError("PDF exceeds 20 MiB")
        self.directory.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(suffix=".pdf", dir=self.directory)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            info = self.inspect(name)
            os.replace(name, target)
            return info
        finally:
            Path(name).unlink(missing_ok=True)
