import os
from typing import Tuple

import magic

paths = ["/usr/share/misc/magic", os.path.join(os.path.dirname(__file__), "magic_patterns")]

MAGIC_ENC_MAPPING = {
    "us-ascii": "utf-8",
    "iso-8859-1": "iso-8859-15"
}
MAGIC_MIME_MAPPING = {
    "application/octet-stream": None # binary file, not otherwise specified
}

MIME_ZIP = "application/zip"

def get_mime(filename: str) -> Tuple[str, str, bool]:
    """
    Guesses the mime-type and encoding of the file using libmagic. Uses magic patterns located in ./magic_patterns,
    as well as the system's built in magic file located in /usr/share/misc.
    If the file is a zipfile, the contents of the zipfile will be read.
    @param filename: the full path to the file.
    @return: A 3-tuple: (mime-type, encoding, is_zip)
    """
    with magic.Magic(paths=paths, flags=magic.MAGIC_MIME) as m:
        mime_enc = m.id_filename(filename)
    mime, enc = mime_enc.split(";")
    is_zip = False
    if mime == MIME_ZIP:
        with magic.Magic(paths=paths, flags=magic.MAGIC_MIME | magic.MAGIC_COMPRESS) as m:
            mime_enc = m.id_filename(filename)
            q = [part1 for part0 in mime_enc.split(" ") for part1 in part0.split(";") if part1]
            try:
                mime, enc, _, _ = q
            except ValueError:
                # Magic did not return 4 values, so it failed to read the contents of the zip file.
                # We report it as a non-zipped file of type application/zip.
                return MIME_ZIP, "binary", False
        is_zip = True

    enc = enc.replace("charset=", "").strip()
    mime = MAGIC_MIME_MAPPING.get(mime, mime)
    enc = MAGIC_ENC_MAPPING.get(enc, enc)
    return mime, enc, is_zip
