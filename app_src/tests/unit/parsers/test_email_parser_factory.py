import pytest

from parsers.email_eml_parser import EmlEmailParser
from parsers.email_msg_parser import MsgEmailParser
from parsers.email_parser_factory import get_email_parser


class TestGetEmailParser:
    @pytest.mark.parametrize(
        "filename, expected_cls",
        [
            ("email1.eml", EmlEmailParser),
            ("email1.msg", MsgEmailParser),
            ("EMAIL1.MSG", MsgEmailParser),  # case-insensitive
            ("EMAIL1.EML", EmlEmailParser),
            ("some/path/email1.eml", EmlEmailParser),
            ("some/path/email1.msg", MsgEmailParser),
        ],
    )
    def test_selects_parser_by_extension(self, filename, expected_cls):
        assert isinstance(get_email_parser(filename), expected_cls)

    @pytest.mark.parametrize("filename", ["file.pdf", "noext", "file.unknown"])
    def test_unknown_extension_falls_back_to_eml(self, filename):
        # Non-email extensions default to the .eml (MIME) parser.
        assert isinstance(get_email_parser(filename), EmlEmailParser)
