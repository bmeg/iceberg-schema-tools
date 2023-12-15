import logging
from typing import Union

logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


def monkey_patch_url_validate():
    # monkey patch to allow file: urls
    import fhir.resources.fhirtypes
    from pydantic.v1 import FileUrl

    original_url_validate = fhir.resources.fhirtypes.Url.validate

    @classmethod
    def better_url_validate(  # type: ignore
            cls, value: str, field: "ModelField", config: "BaseConfig"
    ) -> Union["AnyUrl", str]:
        """Allow file: urls. see https://github.com/pydantic/pydantic/issues/1983
        bugfix: addresses issue introduced with `fhir.resources`==7.0.1
        """
        if value.startswith("file:"):
            return FileUrl.validate(value, field, config)
        value = original_url_validate(value, field, config)
        return value

    fhir.resources.fhirtypes.Url.validate = better_url_validate
    logger.debug("monkey patched Url.validate")


monkey_patch_url_validate()
