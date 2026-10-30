from pathlib import PurePosixPath

from models.parsed_email import ParsedEmail
from parsers.email_eml_parser import EmlEmailParser
from parsers.email_msg_parser import MsgEmailParser
from parsers.email_parser import EmailParser

# Extensions handled by each concrete parser. Anything that is not a known
# email extension falls back to the .eml (MIME) parser.
_PARSERS_BY_EXTENSION: dict[str, type[EmailParser]] = {
    ".eml": EmlEmailParser,
    ".msg": MsgEmailParser,
}


def get_email_parser(filename: str) -> EmailParser:
    """Return the concrete email parser instance for a filename's extension.

    ``.msg`` -> :class:`MsgEmailParser` (Outlook OLE via olefile).
    ``.eml`` (and any other extension) -> :class:`EmlEmailParser` (stdlib MIME).

    Args:
        filename: The email filename (used only for its extension).

    Returns:
        An :class:`EmailParser` instance ready to ``parse(raw_content)``.
    """
    extension = PurePosixPath(filename).suffix.lower()
    parser_cls = _PARSERS_BY_EXTENSION.get(extension, EmlEmailParser)
    return parser_cls()


def parse_email(filename: str, raw_content: bytes) -> ParsedEmail:
    """Parse raw email bytes using the parser selected from the extension.

    Args:
        filename: The email filename (selects the parser by extension).
        raw_content: Raw bytes of the email file.

    Returns:
        ParsedEmail with the extracted attachments.
    """
    return get_email_parser(filename).parse(raw_content)
