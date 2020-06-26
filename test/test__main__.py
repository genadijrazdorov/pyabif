from pyabif.__main__ import main

from click.testing import CliRunner
import pytest

import shutil
import pathlib
import zipfile

ab1_filename = 'AB1-G02_002_0226.ab1'

ab1_filenames = """
    AB1-G02_002_0226.ab1
    AB1-G02_002_0227.ab1
""".strip().split()

fsa_filenames = """
    FSA-G02_002_0228.fsa
    FSA-G02_002_0229.fsa
""".strip().split()


@pytest.fixture
def runner():
    runner = CliRunner()
    pathobj = pathlib.Path(__file__).with_name('infiles.zip')
    with runner.isolated_filesystem():
        with zipfile.ZipFile(pathobj) as arch:
            arch.extractall()
        yield runner


class TestCLI:
    def test_help(self):
        runner = CliRunner()
        result = runner.invoke(main, '--help'.split())

        assert result.exit_code == 0
        assert result.output.startswith('Usage')

    def test_convert_a_file(self, runner):
        result = runner.invoke(main, f'{ab1_filename}'.split())

        assert result.exit_code == 0
        assert result.output.endswith(f"File '{ab1_filename}' is converted.\n")
        assert pathlib.Path(ab1_filename).with_suffix('.ab1.txt.zip').exists()

    def test_convert_files(self, runner):
        result = runner.invoke(main, ' '.join(ab1_filenames).split())

        assert result.exit_code == 0
        assert result.output.endswith(f"2 out of 2 files are converted.\n")

    def test_force_on(self, runner):
        runner.invoke(main, f'{ab1_filename}'.split())
        assert pathlib.Path(ab1_filename).with_suffix('.ab1.txt.zip').exists()

        runner.invoke(main, f'--force {ab1_filename}'.split())
        assert pathlib.Path(ab1_filename).with_suffix('.ab1.txt.zip').exists()

    def test_force_off(self, runner):
        runner.invoke(main, f'{ab1_filename}'.split())
        assert pathlib.Path(ab1_filename).with_suffix('.ab1.txt.zip').exists()

        result = runner.invoke(main, f'{ab1_filename}'.split())

        assert result.exit_code == 1
        assert 'File exists' in result.output
