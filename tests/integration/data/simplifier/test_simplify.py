import pathlib

import orjson

from iceberg_tools.data.simplifier import simplify_directory, validate_simplified_value


def test_simplify_study():
    """Ensure we can validate a synthetic study"""

    simplify_directory('tests/fixtures/simplify/study/', '**/*.*', 'tmp/study/extractions',
                       'iceberg/schemas/simplified/simplified-fhir.json', 'FHIR', 'config.yaml')

    directory_path = pathlib.Path('tmp/study/extractions')
    input_files = [_ for _ in directory_path.glob("*.ndjson")]
    for file_name in input_files:
        with open(file_name) as fp:
            for line in fp.readlines():
                simplified = orjson.loads(line)
                all_ok = all([validate_simplified_value(_) for _ in simplified.values()])
                assert all_ok, (file_name, line)
                if simplified['resourceType'] == 'DocumentReference':
                    # 'content_md5'
                    expected = set(
                        ['content_attachment_contentType', 'content_attachment_url', 'content_attachment_size',
                         'content_attachment_extension_md5']
                    )
                    actual = set([_ for _ in simplified if _.startswith('content')])
                    assert expected == actual, (file_name, line)
