import email
import email.policy
from collections.abc import Iterator
from email.message import EmailMessage

from models.parsed_email import ParsedEmail
from parsers.email_parser import EmailParser, RawAttachment


def _is_attachment(part: EmailMessage) -> bool:
    """Return True when a MIME part is a file attachment (not the body).

    A part is treated as an attachment when:
    - Its Content-Disposition is explicitly ``attachment``, OR
    - It carries a filename and is neither a multipart container nor a
      CID-only inline image used purely for email formatting.
    """
    disposition = part.get_content_disposition()
    if part.is_multipart():
        return False

    if disposition == "attachment":
        return True

    filename = part.get_filename()
    if filename is None:
        return False

    # A part with a filename but an ``inline`` disposition that is referenced
    # by Content-ID (CID) is an embedded formatting image — skip it.
    if disposition == "inline" and part.get("Content-ID") is not None:
        return False

    return True


class EmlEmailParser(EmailParser):
    """Parser for RFC-822 ``.eml`` files using the Python stdlib ``email``.

    Only attachments are extracted — the email body (text/plain, text/html)
    is ignored. The MIME part carries an authoritative content type, so it is
    passed through as-is (no guessing).
    """

    format_label = ".eml"

    def _iter_raw_attachments(self, raw_content: bytes) -> Iterator[RawAttachment]:
        try:
            message = email.message_from_bytes(raw_content, policy=email.policy.default)
        except Exception as exc:
            raise ValueError(f"Unable to parse .eml content: {exc}") from exc

        index = 0
        for part in message.walk():
            if not _is_attachment(part):
                continue

            index += 1
            content_type = part.get_content_type()

            try:
                content = part.get_payload(decode=True)
            except Exception as exc:
                raise ValueError(
                    f"Unable to decode attachment #{index}: {exc}"
                ) from exc

            if content is None:
                raise ValueError(f"Unable to decode attachment #{index}: empty payload")

            yield RawAttachment(
                original_name=part.get_filename(),
                content=content,
                content_type=content_type,
            )


def parse(raw_content: bytes) -> ParsedEmail:
    """Parse raw ``.eml`` bytes and extract attachments.

    Thin module-level entry point delegating to :class:`EmlEmailParser`.

    Args:
        raw_content: Raw bytes of the .eml file.

    Returns:
        ParsedEmail with the list of attachments (empty if none).

    Raises:
        ValueError: If the content cannot be parsed as a valid email message
            or if any attachment payload cannot be decoded (blocking).
    """
    return EmlEmailParser().parse(raw_content)
