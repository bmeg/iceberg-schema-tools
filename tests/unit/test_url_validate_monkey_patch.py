import pytest
from pydantic.v1 import ValidationError

from iceberg_tools import monkey_patch_url_validate

monkey_patch_url_validate()

from fhir.resources.attachment import Attachment  # noqa: E402


@pytest.mark.parametrize(
    'value',
    ['file:///foo/bar', 'file://localhost/foo/bar', 'file:////localhost/foo/bar', 'filex://localhost/foo/bar'],
)
def test_valid_file_url(value):
    """Should not raise an exception."""
    a = Attachment.validate({"url": value})
    assert a.url == value, f"{a.url} should be {value}"


@pytest.mark.parametrize(
    'value',
    ['file:foo/bar', 'file:'],
)
def test_invalid_file_url(value):
    """Should raise an exception."""
    with pytest.raises(ValidationError):
        Attachment.validate({"url": value})
