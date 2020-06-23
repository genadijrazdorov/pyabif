from pyabif import pyABIF

import pytest

import datetime
import struct
import pathlib
import zipfile
import xml.etree.ElementTree as ET


ab1_filenames = """
    AB1-G02_002_0226.ab1
    AB1-G02_002_0227.ab1
""".strip().split()

fsa_filenames = """
    FSA-G02_002_0228.fsa
    FSA-G02_002_0229.fsa
""".strip().split()


@pytest.fixture(params=ab1_filenames)
def ab1(request, path):
    abif_path = path.joinpath(request.param)
    with pyABIF(str(abif_path)) as abif:
        yield abif, ET.parse(abif_path.with_suffix(abif_path.suffix + '.xml'))


@pytest.fixture(params=fsa_filenames)
def fsa(request, path):
    abif_path = path.joinpath(request.param)
    with pyABIF(str(abif_path)) as abif:
        yield abif, ET.parse(abif_path.with_suffix(abif_path.suffix + '.xml'))


@pytest.fixture(params=ab1_filenames + fsa_filenames)
def abif(request, path):
    abif_path = path.joinpath(request.param)
    with pyABIF(str(abif_path)) as abif:
        yield abif, ET.parse(abif_path.with_suffix(abif_path.suffix + '.xml'))


@pytest.fixture
def path(tmp_path):
    infiles = pathlib.Path(__file__).with_name('infiles.zip')
    outfiles = pathlib.Path(__file__).with_name('outfiles.zip')
    for files in (infiles, outfiles):
        with zipfile.ZipFile(files) as arch:
            arch.extractall(tmp_path)
    return tmp_path


def read(etree, name, id):
    tag = etree.find(f".//Tag/[Name='{name}'][ID='{id}']")
    return tag.find('Value').text


class TestpyABIF:
    @pytest.mark.xfail
    def test_fail(self):
        assert False

    def test_user(self, abif):
        abif, etree = abif
        assert abif.User1 in {'bfj', 'joan'}

