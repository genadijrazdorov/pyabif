import struct
import pkgutil
import csv
import io
import datetime
import functools
import hashlib
# import xml.etree.ElementTree as ET


__all__ = ('ABIF',)


BIG_ENDIAN = '>'
ENDIAN = BIG_ENDIAN

# Current Data Types
# Described on page 13. of the Manual
TYPES = '- B B H h l - f d - h2B 4B llBB ? - - - - p s'.split()

HEADER = f'{ENDIAN}4sh'
ITEM = f'{ENDIAN}4si2h4i'

DIGEST = '0ac522f4b022c72ced9227ff7056b40bcc6bf9c4113af14defd94128292594e3bb7faa91d740576a249ab50da7ed400b9e42aa764b5d952bfb0b4f324cbb12d6'


def read_tags():
    package = __name__.rsplit('.', 1)[0]
    fh = io.StringIO(pkgutil.get_data(package, 'tags.csv').decode())

    digest = hashlib.sha512(fh.read().encode()).hexdigest()
    assert digest == DIGEST
    fh.seek(0)

    reader = csv.reader(fh, delimiter='\t')
    next(reader)
    tag2desc = {}
    for line in reader:
        line = [field for field in line if field]
        tag, num, type_, desc = line
        if num.isdigit():
            num = int(num)
        tag2desc[(tag, num)] = desc
    return tag2desc


class ABIFMeta(type):
    tag2desc = read_tags()

    def __new__(cls, name, bases, namespace, **kwargs):
        tag2desc = cls.tag2desc
        read = namespace['read']
        for tag, num in cls.tag2desc:
            desc = tag2desc[tag, num]
            name = tag + str(num)

            if name in namespace:
                method = namespace[name]
                method.__doc__ = desc

            else:
                try:
                    method = functools.partial(namespace[tag], number=num)

                except KeyError:
                    method = functools.partial(read, tag=tag, number=num)

                method = property(method, doc=desc)

            namespace[name] = method

        for tag, num in tag2desc:
            if num == 1:
                namespace[tag] = namespace[tag + '1']

        return super().__new__(cls, name, bases, namespace, **kwargs)


class ABIF(metaclass=ABIFMeta):
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
    _tag2desc = read_tags()

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
        tag2desc = cls._tag2desc
        if number is None:
            tag, number = tag[:4], tag[4:]
            if number.isdigit():
                number = int(number)
            else:
                number = 1
        return tag2desc.get((tag, number)) or tag2desc.get((tag, 'N'))

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
        abif, version = self._unpack(HEADER, offset=0)
        assert abif == b'ABIF'
        self.version = version

        directory = self._unpack(ITEM)
        tdir, one, _, _, elements, size, offset, _ = directory

        assert tdir == b'tdir'
        assert one == 1

        self._dir_offset = offset
        self._dir_elements = elements

    def _read_directory(self):
        self.fileobj.seek(self._dir_offset)

        self.directory = {}
        for i in range(self._dir_elements):
            item = self._unpack(ITEM)
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
