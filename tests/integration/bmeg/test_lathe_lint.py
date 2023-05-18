import subprocess


def test_lathe_lint(bmeg_dir, lath_path):
    """Run lathe's schema-lint command."""
    cmd = f"{lath_path} schema-lint .".split()
    results = subprocess.run(cmd)
    assert results.returncode == 0, (results.stdout, results.stderr)
