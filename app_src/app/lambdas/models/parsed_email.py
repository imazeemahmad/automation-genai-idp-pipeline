"""Shared models for parsed email attachments (.eml and .msg)."""

from pydantic import BaseModel


class Attachment(BaseModel):
    """A single file attachment extracted from an email (.eml or .msg)."""

    filename: str
    content: bytes
    content_type: str


class ParsedEmail(BaseModel):
    """The result of parsing an email: its extracted attachments.

    Shared across all email parsers (.eml via stdlib, .msg via extract-msg).
    The email body is NOT represented here — only attachments are extracted.
    """

    attachments: list[Attachment]
