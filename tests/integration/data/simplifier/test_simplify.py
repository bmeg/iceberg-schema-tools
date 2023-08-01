import pathlib

import orjson

from iceberg_tools.data.simplifier import simplify_directory, validate_simplified_value


def test_simplify_study():
    """Ensure we can validate a synthetic study"""

    simplify_directory('tests/fixtures/simplify/study/', '**/*.*', 'tmp/study/extractions',
                       'iceberg/schemas/simplified/simplified-fhir.json', 'PFB', 'config.yaml')

    directory_path = pathlib.Path('tmp/study/extractions')
    input_files = [_ for _ in directory_path.glob("*.ndjson")]
    for file_name in input_files:
        with open(file_name) as fp:
            for line in fp.readlines():
                pfb_ready = orjson.loads(line)
                simplified = pfb_ready['object']
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
                relations = pfb_ready['relations']
                if len(relations) > 0:
                    dst_ids = [_['dst_id'] for _ in relations]
                    if len(set(dst_ids)) != len(dst_ids):
                        print("WARNING: multiple edges between nodes", file_name, line)


def test_simplify_foo():
    """Ensure we can validate a synthetic study"""

    simplify_directory('tests/fixtures/simplify/foo/', '**/*.*', 'tmp/foo/extractions',
                       'iceberg/schemas/simplified/simplified-fhir.json', 'PFB', 'config.yaml')

    directory_path = pathlib.Path('tmp/foo/extractions')
    input_files = [_ for _ in directory_path.glob("*.ndjson")]
    for file_name in input_files:
        with open(file_name) as fp:
            for line in fp.readlines():
                pfb_ready = orjson.loads(line)
                simplified = pfb_ready['object']
                all_ok = all([validate_simplified_value(_) for _ in simplified.values()])
                print((file_name, line))
                assert all_ok, (file_name, line)
                if simplified['resourceType'] == 'DocumentReference':
                    # 'content_md5'
                    expected = set(
                        ['content_attachment_contentType', 'content_attachment_url', 'content_attachment_size',
                         'content_attachment_extension_md5']
                    )
                    actual = set([_ for _ in simplified if _.startswith('content')])
                    assert expected == actual, (file_name, line)
                    assert len(pfb_ready['relations']) > 0, "DocumentReference should have relationships"
