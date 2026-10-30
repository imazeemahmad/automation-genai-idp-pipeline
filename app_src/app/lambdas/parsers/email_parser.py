import mimetypes
from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass

from aws_lambda_powertools import Logger

from models.parsed_email import Attachment, ParsedEmail

logger = Logger()


@dataclass
class RawAttachment:
    """A format-agnostic attachment yielded by a concrete parser.

    The subclass is responsible only for surfacing the raw pieces; the base
    class turns them into a normalized :class:`Attachment`.
    """

    original_name: str | None
    content: bytes
    # Authoritative MIME type when the format provides one (e.g. .eml MIME
    # parts). Left None when it must be guessed from the filename (e.g. .msg).
    content_type: str | None = None


class EmailParser(ABC):
    """Base class for email attachment parsers (template method pattern).

    Subclasses implement :meth:`_iter_raw_attachments` for their specific
    format; the base class owns the shared concerns: parsing guardrails,
    1-based indexing, unique index-prefixed filenames, content-type
    resolution, logging, and building the :class:`ParsedEmail` result.

    The email body is never extracted — only attachments.
    """

    #: Human-readable format label used in error messages (e.g. ".eml").
    format_label: str = "email"

    def parse(self, raw_content: bytes) -> ParsedEmail:
        """Parse raw email bytes and return the extracted attachments.

        Args:
            raw_content: Raw bytes of the email file.

        Returns:
            ParsedEmail with the list of attachments (empty if none).

        Raises:
            ValueError: If the content cannot be parsed, or if any attachment
                payload cannot be decoded/read (blocking — no silent skip).
        """
        attachments: list[Attachment] = []
        for index, raw in enumerate(self._iter_raw_attachments(raw_content), start=1):
            attachments.append(self._build_attachment(index, raw))
        return ParsedEmail(attachments=attachments)

    @abstractmethod
    def _iter_raw_attachments(self, raw_content: bytes) -> Iterator[RawAttachment]:
        """Yield each file attachment as a RawAttachment.

        Implementations must:
        - raise ValueError if ``raw_content`` cannot be parsed,
        - raise ValueError if an attachment payload cannot be read/decoded,
        - skip the email body and non-file parts (e.g. inline CID images,
          embedded messages).
        """
        raise NotImplementedError

    def _build_attachment(self, index: int, raw: RawAttachment) -> Attachment:
        """Normalize a RawAttachment into an Attachment with a unique name."""
        if raw.original_name:
            content_type = raw.content_type or (
                mimetypes.guess_type(raw.original_name)[0] or "application/octet-stream"
            )
            filename = f"attach_{index}_{raw.original_name}"
        else:
            content_type = raw.content_type or "application/octet-stream"
            ext = mimetypes.guess_extension(content_type) or ""
            filename = f"attach_{index}_unnamed{ext}"

        logger.debug(
            "Extracted attachment",
            extra={
                "attachment_filename": filename,
                "content_type": content_type,
                "size_bytes": len(raw.content),
            },
        )

        return Attachment(
            filename=filename,
            content=raw.content,
            content_type=content_type,
        )
