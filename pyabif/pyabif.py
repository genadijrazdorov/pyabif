import struct
# from struct import pack, unpack, calcsize
import pkgutil
import csv
import io
import datetime
import xml.etree.ElementTree as ET


BIG_ENDIAN = '>'

TYPES = '- B B H h l - f d - h2B 4B llBB ? - - - - p s'.split()


def read_tags():
    package = __name__.rsplit('.', 1)[0]
    file_ = io.StringIO(pkgutil.get_data(package, 'tags.csv').decode())
    reader = csv.reader(file_, delimiter='\t')
    next(reader)
    tag2desc = {}
    for line in reader:
        line = [field for field in line if field]
        name, num, type_, desc = line
        if num.isdigit():
            num = int(num)
        tag2desc[(name, num)] = desc
    return tag2desc


class pyABIF:
    '''a ABIF file reader

    '''
    HEADER = '>4sh'
    ITEM = '>4si2h4i'
    tag2desc = read_tags()

    def __init__(self, fileobj):
        '''

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

    def open(self):
        if self.filename:
            self.fileobj = open(self.filename, 'rb')

        self.read_header()
        self.read_directory()

        self.closed = False

    def __enter__(self):
        if self.closed is None or self.closed is True:
            self.open()
        return self

    def __exit__(self, type_, value, traceback):
        self.close()

    def close(self):
        if self.closed is False:
            self.fileobj.close()

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
                if data.endswith('\x00'):
                    data = data[:-1]

            except AttributeError:
                pass

        return data

    def read_header(self):
        abif, version = self._unpack(self.HEADER, offset=0)
        assert abif == b'ABIF'
        self.version = version

        directory = self._unpack(self.ITEM)
        tdir, one, _, _, elements, size, offset, _ = directory

        assert tdir == b'tdir'
        assert one == 1

        self._dir_offset = offset
        self._dir_elements = elements

    def read_directory(self):
        self.fileobj.seek(self._dir_offset)

        self.directory = {}
        for i in range(self._dir_elements):
            item = self._unpack(self.ITEM)
            name, num, type_, _, elements, size, offset, _ = item
            name = name.decode()
            self.directory[name, num] = (type_, elements, size, offset)

    def __getattr__(self, attr):
        if attr == 'directory':
            raise ValueError(f"{self} is not opened.")

        if len(attr) > 4:
            name, num = attr[:4], attr[4:]
            num = int(num)

            try:
                attr = getattr(self, name)
                return attr(num)

            except AttributeError:
                return self.read(name, num)

        else:
            raise AttributeError

    def read(self, name, num):
        try:
            type_, elements, size, offset = self.directory[name, num]

        except KeyError:
            raise AttributeError

        user = False
        if type_ >= 1024:
            type_ = 1
            user = True

        if elements != 1:
            fmt = '>{}{}'.format(elements, TYPES[type_])
        else:
            fmt = '>{}'.format(TYPES[type_])

        if size <= 4:
            value = struct.pack('>l', offset)
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

    def DyeB(self, num):
        value = self.read('DyeB', num)
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
