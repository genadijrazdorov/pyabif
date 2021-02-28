import struct
import pkgutil
import csv
import io
import datetime
# import xml.etree.ElementTree as ET


BIG_ENDIAN = '>'
ENDIAN = BIG_ENDIAN

# Current Data Types
# Described on page 13. of the Manual
TYPES = '- B B H h l - f d - h2B 4B llBB ? - - - - p s'.split()


def read_tags():
    package = __name__.rsplit('.', 1)[0]
    file_ = io.StringIO(pkgutil.get_data(package, 'tags.csv').decode())
    reader = csv.reader(file_, delimiter='\t')
    next(reader)
    tag2desc = {}
    for line in reader:
        line = [field for field in line if field]
        tag, num, type_, desc = line
        if num.isdigit():
            num = int(num)
        tag2desc[(tag, num)] = desc
    return tag2desc


class ABIF:
    '''a ABIF file reader

    ABIF (Applied Biosystems Genetic Analysis Data File Format) is a binary
    file format used by genetic analyzers from Applied Biosystems (today
    Thermo). Files are designated as ABIF encoded by *.ab1* or *fsa* name
    extension.

    ABIF encoding can be described as directory of tag, value pairs,
    where tags are 4 characher plus a single digit designation.
    For example 'DATA1' is described as *Channel 1 raw data*.

    For same tags single digit can be replaced with multidigit number,
    for example 'DATA105' represents *Raw data for dye 5*,
    while 'DATA5' is reserved for *Voltage, measured (decaVolts)*.

    There are number of tags using unlimited number (1-N) designation,
    for example 'OfScN' for *List of scans that are marked off scale in
    Collection*, with number designation from 1 to N.

    '''
    HEADER = f'{ENDIAN}4sh'
    ITEM = f'{ENDIAN}4si2h4i'
    tag2desc = read_tags()

    def __init__(self, fileobj):
        '''ABIF(fileobj)

        Parameters
        ----------
        fileobj
            filename or file like object

        '''
        if isinstance(fileobj, str):
            self.filename = fileobj
            self.fileobj = None

        else:
            self.filename = None
            self.fileobj = fileobj

        self.closed = None

    @classmethod
    def describe(cls, tag, number=None):
        if number is None:
            tag, number = tag[:4], tag[4:]
            try:
                number = int(number)
            except ValueError:
                number = 1
        return cls.tag2desc[tag, number]

    def open(self):
        if self.filename:
            self.fileobj = open(self.filename, 'rb')

        self._read_header()
        self._read_directory()

        self.closed = False

    def close(self):
        if self.closed is False:
            self.fileobj.close()

    def __enter__(self):
        if self.closed is None or self.closed is True:
            self.open()
        return self

    def __exit__(self, type_, value, traceback):
        self.close()

    def _read_header(self):
        abif, version = self._unpack(self.HEADER, offset=0)
        assert abif == b'ABIF'
        self.version = version

        directory = self._unpack(self.ITEM)
        tdir, one, _, _, elements, size, offset, _ = directory

        assert tdir == b'tdir'
        assert one == 1

        self._dir_offset = offset
        self._dir_elements = elements

    def _read_directory(self):
        self.fileobj.seek(self._dir_offset)

        self.directory = {}
        for i in range(self._dir_elements):
            item = self._unpack(self.ITEM)
            tag, num, type_, _, elements, size, offset, _ = item
            tag = tag.decode()
            self.directory[tag, num] = (type_, elements, size, offset)

    def _unpack(self, format, packed=None, offset=None):
        if offset:
            assert packed is None
            self.fileobj.seek(offset)

        if packed is None:
            packed = self.fileobj.read(struct.calcsize(format))

        else:
            packed = packed[:struct.calcsize(format)]

        data = list(struct.unpack(format, packed))

        if len(data) == 1:
            data = data[0]

            try:
                data = data.decode()

            except AttributeError:
                pass

            else:
                if data.endswith('\x00'):
                    data = data[:-1]

        return data

    def __getattr__(self, attr):
        if attr == 'directory':
            raise ValueError(f"{self} is not opened.")

        if len(attr) > 4:
            tag, num = attr[:4], attr[4:]
            num = int(num)

            try:
                attr = getattr(self, tag)
                return attr(num)

            except AttributeError:
                return self.read(tag, num)

        else:
            raise AttributeError

    def read(self, tag, number):
        num = number
        try:
            type_, elements, size, offset = self.directory[tag, num]

        except KeyError:
            raise AttributeError

        user = False
        if type_ >= 1024:
            type_ = 1
            user = True

        if elements == 1:
            fmt = f'{ENDIAN}{TYPES[type_]}'

        else:
            fmt = f'{ENDIAN}{elements}{TYPES[type_]}'

        if size <= 4:
            value = struct.pack(f'{ENDIAN}l', offset)
            value = self._unpack(fmt, packed=value)

        else:
            value = self._unpack(fmt, offset=offset)

        if type_ == 10:
            value = datetime.date(*value)

        elif type_ == 11:
            value = datetime.time(*value)

        elif user:
            value = bytes(value)

        return value

    @property
    def CpEP1(self):
        value = self.read('CpEP', 1)
        return value

    def DyeB(self, number):
        value = self.read('DyeB', number)
        return chr(value)

    @property
    def APrX1(self):
        value = self.read('APrX', 1)
        return bytes(value).decode()

    @property
    def FWO_1(self):
        value = self.read('FWO_', 1)
        return bytes(value).decode()

    @property
    def RMdX1(self):
        value = self.read('RMdX', 1)
        return bytes(value).decode()

    @property
    def MODL1(self):
        value = self.read('MODL', 1)
        return bytes(value).decode()
