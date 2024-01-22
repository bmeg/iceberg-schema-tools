import subprocess


# This is getting swapped into Lathe
def test_jsonschemagraph_lint(bmeg_dir, jsonschemagraph_path):
    """Run lathe's schema-lint command."""
    cmd = f"{jsonschemagraph_path} schema-lint .".split()
    results = subprocess.run(cmd, capture_output=True, text=True)
    for result in str(results).split(": "):
        print(result)
    assert results.returncode == 0, (results.stdout, results.stderr)
    assert 'ERROR' not in results.stdout, results.stdout
    lines = results.stdout.split('\n')
    for _ in lines:
        if len(_) > 0:
            assert 'OK' in _, _
