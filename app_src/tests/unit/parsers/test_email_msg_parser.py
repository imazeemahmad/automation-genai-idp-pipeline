from unittest.mock import MagicMock, patch

import pytest

from models.parsed_email import Attachment, ParsedEmail
from parsers.email_msg_parser import parse

_PREFIX = "__attach_version1.0"
_DATA = "__substg1.0_37010102"
_LONG = "__substg1.0_3707001F"
_SHORT = "__substg1.0_3704001F"
_MIME = "__substg1.0_370E001F"


def _u16(text):
    """Encode a string as a UTF-16-LE MAPI stream with trailing NUL."""
    return (text + "\x00").encode("utf-16-le")


def _build_ole(attachments):
    """Build a fake olefile.OleFileIO from a list of attachment dicts.

    Each attachment dict: {"dir": str, "data": bytes|None, "long": str|None,
    "short": str|None, "mime": str|None}. A None "data" means the DATA stream
    is absent (non-file attachment to be skipped).
    """
    streams = {}
    listing = []
    for att in attachments:
        d = att["dir"]
        listing.append([d, "__properties_version1.0"])
        if att.get("data") is not None:
            streams[f"{d}/{_DATA}"] = att["data"]
            listing.append([d, _DATA])
        if att.get("long"):
            streams[f"{d}/{_LONG}"] = _u16(att["long"])
            listing.append([d, _LONG])
        if att.get("short"):
            streams[f"{d}/{_SHORT}"] = _u16(att["short"])
            listing.append([d, _SHORT])
        if att.get("mime"):
            streams[f"{d}/{_MIME}"] = _u16(att["mime"])
            listing.append([d, _MIME])

    ole = MagicMock()
    ole.listdir.return_value = listing
    ole.exists.side_effect = lambda path: path in streams
    ole.openstream.side_effect = lambda path: MagicMock(
        read=MagicMock(return_value=streams[path])
    )
    return ole


def _patch_ole(attachments):
    return patch(
        "parsers.email_msg_parser.olefile.OleFileIO",
        return_value=_build_ole(attachments),
    )


class TestParse:
    def test_single_binary_attachment_preserves_null_bytes(self):
        pdf = b"%PDF-1.5\x00\x00binary\x00payload%%EOF"
        with _patch_ole(
            [
                {
                    "dir": f"{_PREFIX}_#00000000",
                    "data": pdf,
                    "long": "sow.pdf",
                    "mime": "application/pdf",
                }
            ]
        ):
            result = parse(b"raw-msg")

        assert isinstance(result, ParsedEmail)
        assert len(result.attachments) == 1
        att = result.attachments[0]
        assert att.filename == "attach_1_sow.pdf"
        assert att.content == pdf  # byte-for-byte, null bytes kept
        assert att.content_type == "application/pdf"

    def test_two_attachments_prefixed_with_index(self):
        with _patch_ole(
            [
                {
                    "dir": f"{_PREFIX}_#00000000",
                    "data": b"%PDF one",
                    "long": "devis.pdf",
                    "mime": "application/pdf",
                },
                {
                    "dir": f"{_PREFIX}_#00000001",
                    "data": b"PNGbytes",
                    "long": "specs.png",
                    "mime": "image/png",
                },
            ]
        ):
            result = parse(b"raw-msg")

        assert [a.filename for a in result.attachments] == [
            "attach_1_devis.pdf",
            "attach_2_specs.png",
        ]
        assert result.attachments[1].content_type == "image/png"

    def test_no_attachments_returns_empty_list(self):
        with _patch_ole([]):
            result = parse(b"raw-msg")

        assert result.attachments == []

    def test_same_named_attachments_get_unique_prefixes(self):
        with _patch_ole(
            [
                {"dir": f"{_PREFIX}_#00000000", "data": b"a", "long": "devis.pdf"},
                {"dir": f"{_PREFIX}_#00000001", "data": b"b", "long": "devis.pdf"},
            ]
        ):
            result = parse(b"raw-msg")

        assert result.attachments[0].filename == "attach_1_devis.pdf"
        assert result.attachments[1].filename == "attach_2_devis.pdf"

    def test_falls_back_to_short_filename(self):
        with _patch_ole(
            [{"dir": f"{_PREFIX}_#00000000", "data": b"a", "short": "doc.pdf"}]
        ):
            result = parse(b"raw-msg")

        assert result.attachments[0].filename == "attach_1_doc.pdf"

    def test_unnamed_attachment_gets_generated_name(self):
        with _patch_ole([{"dir": f"{_PREFIX}_#00000000", "data": b"img"}]):
            result = parse(b"raw-msg")

        assert result.attachments[0].filename.startswith("attach_1_unnamed")
        assert result.attachments[0].content_type == "application/octet-stream"

    def test_attachment_without_data_stream_is_skipped(self):
        # First entry has no DATA stream (embedded message / OLE object) -> skip;
        # index only counts real file attachments.
        with _patch_ole(
            [
                {"dir": f"{_PREFIX}_#00000000", "data": None, "long": "nested.msg"},
                {"dir": f"{_PREFIX}_#00000001", "data": b"%PDF", "long": "real.pdf"},
            ]
        ):
            result = parse(b"raw-msg")

        assert len(result.attachments) == 1
        assert result.attachments[0].filename == "attach_1_real.pdf"

    def test_malformed_content_raises_value_error(self):
        with patch(
            "parsers.email_msg_parser.olefile.OleFileIO",
            side_effect=Exception("bad OLE"),
        ):
            with pytest.raises(ValueError, match="Unable to parse .msg content"):
                parse(b"not-a-real-msg")

    def test_returns_pydantic_models(self):
        with _patch_ole(
            [{"dir": f"{_PREFIX}_#00000000", "data": b"a", "long": "devis.pdf"}]
        ):
            result = parse(b"raw-msg")

        assert isinstance(result, ParsedEmail)
        assert all(isinstance(a, Attachment) for a in result.attachments)
