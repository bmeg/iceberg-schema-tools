from iceberg_tools.data.pfb import SimplePFBWriter
from iceberg_tools.data.simplifier import simplify_directory


def test_studies(caplog, dependency_order):
    """Ensure we can create a pfb file from a synthetic study."""
    simplify_directory('tests/fixtures/simplify/study/', '**/*.*', 'tmp/study/extractions',
                       'iceberg/schemas/simplified/simplified-fhir.json', 'PFB', 'config.yaml')

    pfb_writer = SimplePFBWriter(schema_path='iceberg/schemas/simplified/simplified-fhir.json',
                                 output_path='tmp/CohesiveDataSet.avro',
                                 dependency_order=dependency_order)

    list(pfb_writer.transform_directory('tmp/study/extractions'))

    inspection = pfb_writer.inspect()
    assert len(inspection.errors) == 0, "Unexpected errors"
    if len(inspection.warnings) > 0:
        print(inspection.warnings)


def test_synthea(caplog, dependency_order):
    """Ensure we can create a pfb file from a synthetic study."""
    simplify_directory('tests/fixtures/simplify/synthea', '**/*.*', 'tmp/synthea/extractions',
                       'iceberg/schemas/simplified/simplified-fhir.json', 'PFB', 'config.yaml')

    pfb_writer = SimplePFBWriter(schema_path='iceberg/schemas/simplified/simplified-fhir.json',
                                 output_path='tmp/Synthea.avro',
                                 dependency_order=dependency_order)

    list(pfb_writer.transform_directory('tmp/synthea/extractions'))

    inspection = pfb_writer.inspect()
    assert len(inspection.errors) == 0, "Unexpected errors"
    if len(inspection.warnings) > 0:
        print(inspection.warnings)


def test_kf(caplog, dependency_order):
    """Ensure we can create a pfb file from a Kids first study."""
    simplify_directory('tests/fixtures/simplify/kf', '**/*.*', 'tmp/kf/extractions',
                       'iceberg/schemas/simplified/simplified-fhir.json', 'PFB', 'config.yaml')

    pfb_writer = SimplePFBWriter(schema_path='iceberg/schemas/simplified/simplified-fhir.json',
                                 output_path='tmp/KidsFirst.avro',
                                 dependency_order=dependency_order)

    list(pfb_writer.transform_directory('tmp/kf/extractions'))

    inspection = pfb_writer.inspect()
    assert len(inspection.errors) == 0, "Unexpected errors"
    if len(inspection.warnings) > 0:
        print(inspection.warnings)


def test_ncpi(caplog, dependency_order):
    """Ensure we can create a pfb file from a NCPI IG examples."""

    simplify_directory('tests/fixtures/simplify/ncpi/examples-5.0', '*.*', 'tmp/ncpi/extractions',
                       'iceberg/schemas/simplified/simplified-fhir.json', 'PFB', 'config.yaml')

    pfb_writer = SimplePFBWriter(schema_path='iceberg/schemas/simplified/simplified-fhir.json',
                                 output_path='tmp/NCPI.avro',
                                 dependency_order=dependency_order)

    list(pfb_writer.transform_directory('tmp/ncpi/extractions'))

    inspection = pfb_writer.inspect()
    assert len(inspection.errors) == 0, "Unexpected errors"
    if len(inspection.warnings) > 0:
        print(inspection.warnings)


def test_genomics_reporting(caplog, dependency_order):
    """Ensure we can create a pfb file from a Genomics Reporting IG examples."""

    simplify_directory('tests/fixtures/simplify/genomics-reporting/examples-5.0',
                       '*.*', 'tmp/genomics-reporting/extractions',
                       'iceberg/schemas/simplified/simplified-fhir.json', 'PFB', 'config.yaml')

    pfb_writer = SimplePFBWriter(schema_path='iceberg/schemas/simplified/simplified-fhir.json',
                                 output_path='tmp/GenomicsReporting.avro',
                                 dependency_order=dependency_order)

    list(pfb_writer.transform_directory('tmp/genomics-reporting/extractions'))

    inspection = pfb_writer.inspect()
    assert len(inspection.errors) == 0, "Unexpected errors"
    if len(inspection.warnings) > 0:
        print(inspection.warnings)


def test_dbgap(caplog, dependency_order):
    """Ensure we can create a pfb file from dbGAP examples."""

    simplify_directory('tests/fixtures/simplify/dbgap/examples-5.0', '*.*', 'tmp/dbgap/extractions',
                       'iceberg/schemas/simplified/simplified-fhir.json', 'PFB', 'config.yaml')

    pfb_writer = SimplePFBWriter(schema_path='iceberg/schemas/simplified/simplified-fhir.json',
                                 output_path='tmp/dbGap.avro',
                                 dependency_order=dependency_order)

    list(pfb_writer.transform_directory('tmp/dbgap/extractions'))

    inspection = pfb_writer.inspect()
    assert len(inspection.errors) == 0, "Unexpected errors"
    if len(inspection.warnings) > 0:
        print(inspection.warnings)


def test_anvil(caplog, dependency_order):
    """Ensure we can create a pfb file from AnVIL examples."""

    simplify_directory('tests/fixtures/simplify/anvil/fhir-5.0/', '**/*.*', 'tmp/anvil/extractions',
                       'iceberg/schemas/simplified/simplified-fhir.json', 'PFB', 'config.yaml')

    pfb_writer = SimplePFBWriter(schema_path='iceberg/schemas/simplified/simplified-fhir.json',
                                 output_path='tmp/AnVIL.avro',
                                 dependency_order=dependency_order)

    list(pfb_writer.transform_directory('tmp/anvil/extractions'))

    inspection = pfb_writer.inspect()
    assert len(inspection.errors) == 0, "Unexpected errors"
    if len(inspection.warnings) > 0:
        print(inspection.warnings)
