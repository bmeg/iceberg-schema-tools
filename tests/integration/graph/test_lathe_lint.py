import subprocess


def test_lathe_lint(bmeg_dir, lath_path):
    """Run lathe's schema-lint command."""
    cmd = f"{lath_path} schema-lint .".split()
    results = subprocess.run(cmd, capture_output=True, text=True)
    assert results.returncode == 0, (results.stdout, results.stderr)
    assert 'ERROR' not in results.stdout, results.stdout
    lines = results.stdout.split('\n')
    for _ in lines:
        if len(_) > 0:
            assert 'OK' in _, _
