from pyabif import ABIF

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
    with ABIF(str(abif_path)) as abif:
        yield abif, ET.parse(abif_path.with_suffix(abif_path.suffix + '.xml'))


@pytest.fixture(params=fsa_filenames)
def fsa(request, path):
    abif_path = path.joinpath(request.param)
    with ABIF(str(abif_path)) as abif:
        yield abif, ET.parse(abif_path.with_suffix(abif_path.suffix + '.xml'))


@pytest.fixture(params=ab1_filenames + fsa_filenames)
def abif(request, path):
    abif_path = path.joinpath(request.param)
    with ABIF(str(abif_path)) as abif:
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


class TestABIF:
    def test__init__with_fileobj(self, path):
        abif_path = path.joinpath(ab1_filenames[0])
        with open(str(abif_path), 'rb') as fileobj:
            abif = ABIF(fileobj)
        assert abif.filename is None

    def test__getattr__with_closed_file(self):
        path = pathlib.Path(__file__).with_name(ab1_filenames[0])
        ab1 = ABIF(str(path))
        with pytest.raises(ValueError):
            ab1.User1

    def test_read_wrong_attr(self, ab1):
        ab1, etree = ab1
        with pytest.raises(AttributeError):
            ab1.User2

    def test_user_type(self, ab1):
        ab1, etree = ab1
        ab1.Rate1
        assert ab1.directory['Rate', 1][0] >= 1024

    def test_user(self, abif):
        abif, etree = abif
        assert abif.User1 in {'bfj', 'joan'}

    def test_CpEP(self, abif):
        abif, etree = abif
        value = read(etree, 'CpEP', 1)
        expected = struct.unpack('>?', value.encode())[0]

        assert abif.CpEP1 == expected

    def test_date(self, abif):
        abif, etree = abif
        value = read(etree, 'RUND', 1)
        expected = datetime.datetime.strptime(value, '%m/%d/%Y').date()

        assert abif.RUND1 == expected

    def test_MODL1(self, abif):
        abif, etree = abif
        expected = read(etree, 'MODL', 1)

        assert abif.MODL1 == expected

    def test_time(self, abif):
        abif, etree = abif
        value = read(etree, 'RUNT', 1)
        expected = datetime.datetime.strptime(value, '%H:%M:%S').time()

        assert abif.RUNT1 == expected

    def test_DyeB(self, fsa):
        abif, etree = fsa
        expected = read(etree, 'DyeB', 1)

        assert abif.DyeB1 == expected

    def test_APrX1(self, ab1):
        abif, etree = ab1
        expected = bytes(map(int, read(etree, 'APrX', 1).split())).decode()

        assert abif.APrX1 == expected

    def test_RMdX1(self, abif):
        abif, etree = abif
        expected = bytes(map(int, read(etree, 'RMdX', 1).split())).decode()

        assert abif.RMdX1 == expected

    def test_auto(self, abif):
        IGNORE = frozenset('CpEP MODL RUND RUNT Rate DyeB APrX RMdX'.split())
        abif, etree = abif
        for attr, num in abif.directory:
            if attr in IGNORE:
                continue

            value = getattr(abif, f'{attr}{num}')
            expected = read(etree, attr, num)
            try:
                expected = eval(expected)

            except SyntaxError:
                expected = list(map(int, expected.split()))

            except NameError:
                pass

            assert value == expected
