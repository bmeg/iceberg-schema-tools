from iceberg_tools.data.pfb import SimplePFBWriter
from iceberg_tools.data.simplifier import simplify_directory


def test_studies(caplog):
    """Ensure we can create a pfb file from a synthetic study."""
    simplify_directory('tests/fixtures/simplify/study/', '**/*.*', 'tmp/study/extractions',
                       'iceberg/schemas/gen3/aced.json', 'GEN3')

    pfb_writer = SimplePFBWriter(schema_path='iceberg/schemas/gen3/aced.json',
                                 output_path='tmp/study/extractions/simplified-study.avro')
    for _ in pfb_writer.transform_directory('tmp/study/extractions'):
        print(_)

    inspection = pfb_writer.inspect()
    assert len(inspection.errors) == 0, "Unexpected errors"
    if len(inspection.warnings) > 0:
        print(inspection.warnings)


def test_synthea(caplog):
    """Ensure we can create a pfb file from a synthetic study."""
    simplify_directory('tests/fixtures/simplify/synthea', '**/*.*', 'tmp/synthea/extractions',
                       'iceberg/schemas/gen3/aced.json', 'GEN3')

    pfb_writer = SimplePFBWriter(schema_path='iceberg/schemas/gen3/aced.json',
                                 output_path='tmp/synthea/simplified-synthea.avro')
    for _ in pfb_writer.transform_directory('tmp/synthea/extractions'):
        print(_)

    inspection = pfb_writer.inspect()
    assert len(inspection.errors) == 0, "Unexpected errors"
    if len(inspection.warnings) > 0:
        print(inspection.warnings)


def test_kf(caplog):
    """Ensure we can create a pfb file from a Kids first study."""
    simplify_directory('tests/fixtures/simplify/kf', '**/*.*', 'tmp/kf/extractions',
                       'iceberg/schemas/gen3/aced.json', 'GEN3')

    pfb_writer = SimplePFBWriter(schema_path='iceberg/schemas/gen3/aced.json',
                                 output_path='tmp/kf/simplified-kf.avro')

    for _ in pfb_writer.transform_directory('tmp/kf/extractions'):
        print(_)

    inspection = pfb_writer.inspect()
    assert len(inspection.errors) == 0, "Unexpected errors"
    if len(inspection.warnings) > 0:
        print(inspection.warnings)


def test_ncpi(caplog):
    """Ensure we can create a pfb file from a NCPI IG examples."""

    simplify_directory('tests/fixtures/simplify/ncpi/examples-5.0', '*.*', 'tmp/ncpi/extractions',
                       'iceberg/schemas/gen3/aced.json', 'GEN3')

    pfb_writer = SimplePFBWriter(schema_path='iceberg/schemas/gen3/aced.json',
                                 output_path='tmp/ncpi/simplified-ncpi.avro')

    for _ in pfb_writer.transform_directory('tmp/ncpi/extractions'):
        print(_)

    inspection = pfb_writer.inspect()
    assert len(inspection.errors) == 0, "Unexpected errors"
    if len(inspection.warnings) > 0:
        print(inspection.warnings)


def test_genomics_reporting(caplog):
    """Ensure we can create a pfb file from a Genomics Reporting IG examples."""

    simplify_directory('tests/fixtures/simplify/genomics-reporting/examples-5.0', '*.*', 'tmp/genomics-reporting/extractions',
                       'iceberg/schemas/gen3/aced.json', 'GEN3')

    pfb_writer = SimplePFBWriter(schema_path='iceberg/schemas/gen3/aced.json',
                                 output_path='tmp/genomics-reporting/simplified-ncpi.avro')

    for _ in pfb_writer.transform_directory('tmp/genomics-reporting/extractions'):
        print(_)

    inspection = pfb_writer.inspect()
    assert len(inspection.errors) == 0, "Unexpected errors"
    if len(inspection.warnings) > 0:
        print(inspection.warnings)


def test_dbgap(caplog):
    """Ensure we can create a pfb file from dbGAP examples."""

    simplify_directory('tests/fixtures/simplify/dbgap/examples-5.0', '*.*', 'tmp/dbgap/extractions',
                       'iceberg/schemas/gen3/aced.json', 'GEN3')

    pfb_writer = SimplePFBWriter(schema_path='iceberg/schemas/gen3/aced.json',
                                 output_path='tmp/dbgap/simplified-dbgap.avro')

    for _ in pfb_writer.transform_directory('tmp/dbgap/extractions'):
        print(_)

    inspection = pfb_writer.inspect()
    assert len(inspection.errors) == 0, "Unexpected errors"
    if len(inspection.warnings) > 0:
        print(inspection.warnings)


def test_anvil(caplog):
    """Ensure we can create a pfb file from AnVIL examples."""

    simplify_directory('tests/fixtures/simplify/anvil/fhir/', '**/*.*', 'tmp/anvil/extractions',
                       'iceberg/schemas/gen3/aced.json', 'GEN3')

    pfb_writer = SimplePFBWriter(schema_path='iceberg/schemas/gen3/aced.json',
                                 output_path='tmp/anvil/simplified-anvil.avro')

    for _ in pfb_writer.transform_directory('tmp/anvil/extractions'):
        print(_)

    inspection = pfb_writer.inspect()
    assert len(inspection.errors) == 0, "Unexpected errors"
    if len(inspection.warnings) > 0:
        print(inspection.warnings)
