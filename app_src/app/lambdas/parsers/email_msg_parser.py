import io
from collections.abc import Iterator

import olefile

from models.parsed_email import ParsedEmail
from parsers.email_parser import EmailParser, RawAttachment

# --- Library choice: olefile (not extract-msg, not msg-parser's .data) ------
# A .msg file is an OLE/CFB container. Each attachment lives in a
# "__attach_version1.0_#XXXXXXXX" storage, whose MAPI property streams follow
# the documented tag scheme:
#   __substg1.0_37010102 -> PR_ATTACH_DATA_BIN   (raw attachment bytes)
#   __substg1.0_3707001F -> PR_ATTACH_LONG_FILENAME (Unicode, UTF-16-LE)
#   __substg1.0_3704001F -> PR_ATTACH_FILENAME      (Unicode, short name)
#   __substg1.0_370E001F -> PR_ATTACH_MIME_TAG      (Unicode)
#
# We read these streams directly with `olefile` (pure-Python, arm64-safe,
# already the backing lib of the .msg ecosystem). Two libraries were rejected:
#   * extract-msg: its RTFDE->oletools->pyopenssl chain pins cryptography<50,
#     conflicting with snowflake-connector-python's cryptography>=50 (the arm64
#     Lambda layer build fails with ResolutionImpossible).
#   * msg-parser: its PtypBinary strips every 0x00 byte from binary properties
#     (replace(b"\x00", b"")), which CORRUPTS binary attachments — a 540 KB PDF
#     came back 6 KB short and unreadable. Its .data is unusable for binaries.
# Reading the OLE stream ourselves yields the exact, unaltered bytes.
# ---------------------------------------------------------------------------

_ATTACH_PREFIX = "__attach_version1.0"
_TAG_DATA = "__substg1.0_37010102"
_TAG_LONG_FILENAME = "__substg1.0_3707001F"
_TAG_SHORT_FILENAME = "__substg1.0_3704001F"
_TAG_MIME = "__substg1.0_370E001F"


def _read_unicode(ole: olefile.OleFileIO, path: str) -> str | None:
    """Read a UTF-16-LE MAPI string stream, or None if absent."""
    if not ole.exists(path):
        return None
    raw = ole.openstream(path).read()
    # MAPI Unicode strings are UTF-16-LE and may carry a trailing NUL.
    return raw.decode("utf-16-le", "ignore").rstrip("\x00") or None


class MsgEmailParser(EmailParser):
    """Parser for Outlook ``.msg`` files, reading OLE streams via ``olefile``.

    Only file attachments are extracted — the email body is ignored. Each
    attachment's binary payload is read verbatim from its
    ``PR_ATTACH_DATA_BIN`` stream (no byte stripping), so PDFs/images come out
    intact.
    """

    format_label = ".msg"

    def _iter_raw_attachments(self, raw_content: bytes) -> Iterator[RawAttachment]:
        try:
            ole = olefile.OleFileIO(io.BytesIO(raw_content))
        except Exception as exc:
            raise ValueError(f"Unable to parse .msg content: {exc}") from exc

        try:
            # Top-level storages named "__attach_version1.0_#XXXXXXXX".
            attach_dirs = sorted(
                {
                    entry[0]
                    for entry in ole.listdir()
                    if entry and entry[0].startswith(_ATTACH_PREFIX)
                }
            )

            index = 0
            for attach_dir in attach_dirs:
                data_path = f"{attach_dir}/{_TAG_DATA}"
                # No binary data stream => embedded message or non-file OLE
                # object; skip it (we only handle real file attachments).
                if not ole.exists(data_path):
                    continue

                content = ole.openstream(data_path).read()
                index += 1

                original_name = _read_unicode(
                    ole, f"{attach_dir}/{_TAG_LONG_FILENAME}"
                ) or _read_unicode(ole, f"{attach_dir}/{_TAG_SHORT_FILENAME}")

                content_type = _read_unicode(ole, f"{attach_dir}/{_TAG_MIME}")

                yield RawAttachment(
                    original_name=original_name,
                    content=content,
                    content_type=content_type,
                )
        finally:
            ole.close()


def parse(raw_content: bytes) -> ParsedEmail:
    """Parse raw Outlook ``.msg`` bytes and extract attachments.

    Thin module-level entry point delegating to :class:`MsgEmailParser`.

    Args:
        raw_content: Raw bytes of the .msg file.

    Returns:
        ParsedEmail with the list of attachments (empty if none).

    Raises:
        ValueError: If the content cannot be parsed as a valid .msg message.
    """
    return MsgEmailParser().parse(raw_content)
