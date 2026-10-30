from email.message import EmailMessage

import pytest

from models.parsed_email import Attachment, ParsedEmail
from parsers.email_eml_parser import parse


def _build_email_with_attachments(attachments, body="Hello body"):
    """Build an EmailMessage with a text body and the given attachments.

    Each attachment is a tuple of (data, maintype, subtype, filename).
    A filename of None adds the part without a filename.
    """
    msg = EmailMessage()
    msg["From"] = "sender@example.com"
    msg["To"] = "receiver@example.com"
    msg["Subject"] = "Test"
    msg.set_content(body)
    for data, maintype, subtype, filename in attachments:
        msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=filename)
    return msg.as_bytes()


class TestParse:
    def test_two_pdf_attachments_prefixed_with_index(self):
        raw = _build_email_with_attachments(
            [
                (b"%PDF-1 one", "application", "pdf", "devis.pdf"),
                (b"%PDF-1 two", "application", "pdf", "specs.pdf"),
            ]
        )

        result = parse(raw)

        assert isinstance(result, ParsedEmail)
        assert len(result.attachments) == 2
        assert result.attachments[0].filename == "attach_1_devis.pdf"
        assert result.attachments[0].content == b"%PDF-1 one"
        assert result.attachments[0].content_type == "application/pdf"
        assert result.attachments[1].filename == "attach_2_specs.pdf"
        assert result.attachments[1].content == b"%PDF-1 two"

    def test_body_only_returns_empty_list(self):
        msg = EmailMessage()
        msg["Subject"] = "No attachments"
        msg.set_content("Just a plain text body")

        result = parse(msg.as_bytes())

        assert result.attachments == []

    def test_html_and_text_body_only_returns_empty_list(self):
        msg = EmailMessage()
        msg["Subject"] = "Multipart alternative"
        msg.set_content("plain text body")
        msg.add_alternative("<p>html body</p>", subtype="html")

        result = parse(msg.as_bytes())

        assert result.attachments == []

    def test_two_same_named_attachments_get_unique_prefixes(self):
        raw = _build_email_with_attachments(
            [
                (b"first", "application", "pdf", "devis.pdf"),
                (b"second", "application", "pdf", "devis.pdf"),
            ]
        )

        result = parse(raw)

        assert len(result.attachments) == 2
        assert result.attachments[0].filename == "attach_1_devis.pdf"
        assert result.attachments[1].filename == "attach_2_devis.pdf"

    def test_unnamed_attachment_gets_generated_name_from_content_type(self):
        raw = _build_email_with_attachments(
            [
                (b"\x89PNG image bytes", "image", "png", None),
            ]
        )

        result = parse(raw)

        assert len(result.attachments) == 1
        assert result.attachments[0].filename == "attach_1_unnamed.png"
        assert result.attachments[0].content_type == "image/png"

    def test_inline_cid_image_without_attachment_disposition_is_skipped(self):
        msg = EmailMessage()
        msg["Subject"] = "Inline image"
        msg.set_content("body referencing inline image")
        # Add an inline image referenced by Content-ID (email formatting only)
        msg.add_related(
            b"\x89PNG inline bytes",
            maintype="image",
            subtype="png",
            cid="logo123",
        )

        result = parse(msg.as_bytes())

        assert result.attachments == []

    def test_explicit_attachment_alongside_inline_cid_image(self):
        msg = EmailMessage()
        msg["Subject"] = "Mixed"
        msg.set_content("body")
        msg.add_related(
            b"\x89PNG inline bytes",
            maintype="image",
            subtype="png",
            cid="logo123",
        )
        msg.add_attachment(
            b"%PDF real attachment",
            maintype="application",
            subtype="pdf",
            filename="contract.pdf",
        )

        result = parse(msg.as_bytes())

        assert len(result.attachments) == 1
        assert result.attachments[0].filename == "attach_1_contract.pdf"

    def test_malformed_content_raises_value_error(self):
        with pytest.raises(ValueError):
            parse(None)

    def test_attachment_decode_failure_raises_value_error(self, monkeypatch):
        raw = _build_email_with_attachments(
            [
                (b"data", "application", "pdf", "devis.pdf"),
            ]
        )

        # Force a decode failure when the parser decodes an attachment payload.
        import parsers.email_eml_parser as module

        real_message = module.email.message_from_bytes(
            raw, policy=module.email.policy.default
        )

        def _raise(*_args, **_kwargs):
            raise RuntimeError("corrupt encoding")

        for part in real_message.walk():
            if part.get_filename() == "devis.pdf":
                part.get_payload = _raise

        monkeypatch.setattr(
            module.email,
            "message_from_bytes",
            lambda _content, policy=None: real_message,
        )

        with pytest.raises(ValueError, match="Unable to decode attachment"):
            parse(raw)

    def test_returns_pydantic_models(self):
        raw = _build_email_with_attachments(
            [
                (b"data", "application", "pdf", "devis.pdf"),
            ]
        )

        result = parse(raw)

        assert isinstance(result, ParsedEmail)
        assert all(isinstance(a, Attachment) for a in result.attachments)
