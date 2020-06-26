from pyabif import pyABIF

import click

import datetime
import pathlib
import csv
from zipfile import ZipFile, ZIP_DEFLATED, ZIP_BZIP2, ZIP_LZMA
import io
import glob
import contextlib

META_LIMIT = 10
SUFFIX = '.txt.zip'

# COMPRESSION = ZIP_LZMA
# COMPRESSION = ZIP_BZIP2
COMPRESSION = ZIP_DEFLATED

COMPRESSLEVEL = 6
SECOND = datetime.timedelta(seconds=1)
MINUTE = datetime.timedelta(minutes=1)


@contextlib.contextmanager
def txtfile(*, zipfile, path):
    try:
        bfh = zipfile.open(str(path), mode='w')
        fh = io.TextIOWrapper(bfh, newline='')
        yield fh

    finally:
        fh.close()
        bfh.close()


def convert(filename, *, force=False, digits=3, migration_units='minutes'):
    path = pathlib.Path(filename)
    archive = path.with_suffix(path.suffix + SUFFIX)
    path = pathlib.Path(path.name)
    mode = 'w' if force else 'x'

    zipfile = ZipFile(
        archive,
        mode=mode,
        compression=COMPRESSION,
        compresslevel=COMPRESSLEVEL
    )
    with zipfile, pyABIF(filename) as abif:

        start = datetime.datetime.combine(abif.RUND3, abif.RUNT3)
        stop = datetime.datetime.combine(abif.RUND4, abif.RUNT4)
        runtime = stop - start

        meta = [('Tag', 'ID', 'Value', 'Description')]
        for item in abif.directory:
            name, id_ = item
            value = abif.read(*item)
            description = abif.tag2desc.get(item, 'NA')

            if name == 'DATA':
                data_path = path.with_suffix(path.suffix + f'.data.{id_}.txt')
                with txtfile(zipfile=zipfile, path=data_path) as data:
                    data_writer = csv.writer(data, dialect='excel-tab')
                    data_writer.writerow(('Migration time', 'Value'))

                    scan_time = runtime / len(value)
                    if migration_units == 'minutes':
                        scan_time /= MINUTE

                    elif migration_units == 'seconds':
                        scan_time /= SECOND

                    rows = ((scan_time * i, AU) for i, AU in enumerate(value))
                    data_writer.writerows(rows)

                value = data_path

            elif name in 'RMdX APrX'.split():
                xml_path = path.with_suffix(path.suffix + f'.{name}.{id_}.xml')
                with zipfile.open(str(xml_path), mode='w') as xml_handle:
                    xml_handle.write(bytes(value))

                value = xml_path

            elif isinstance(value, (tuple, list)) and len(value) > META_LIMIT:
                item_path = path.with_suffix(path.suffix + f'.{name}.{id_}.txt')
                with txtfile(zipfile=zipfile, path=item_path) as item_handle:
                    item_handle.writelines((f'{v}\n' for v in value))

                value = item_path

            meta.append((*item, value, description))

        meta_path = path.with_suffix(path.suffix + '.meta.csv')
        with txtfile(zipfile=zipfile, path=meta_path) as meta_handle:

            writer = csv.writer(meta_handle, dialect='excel')
            writer.writerows(meta)


@click.command()
@click.argument(
    'patterns',
    nargs=-1
)
@click.option(
    '-f', '--force',
    default=False,
    is_flag=True,
    show_default=True,
    help='Force conversion even if resulting file already exists'
)
@click.option(
    '-b', '--batch',
    default=False,
    is_flag=True,
    show_default=True,
    help='Combine data files in batches'
)
@click.option(
    '-d', '--digits',
    default=3,
    type=int,
    show_default=True,
    help='Number of digits for migration times'
)
@click.option(
    '-u', '--migration-units',
    type=click.Choice('seconds minutes'.split()),
    default='minutes',
    show_default=True,
    help='Migration units'
)
def main(patterns, *, force=False, batch=False, digits=3, migration_units='minutes'):
    '''Converts PATTERNS from ABIF to txt format

    PATTERNS are glob filenames of ABIF files to convert.
    '''
    errors = []
    succesful = []
    filenames = [fname for ptrn in patterns for fname in glob.glob(ptrn)]

    click.echo(f'Found {len(filenames)} files to convert.')

    with click.progressbar(filenames, label='Files converted:') as progress:
        for filename in progress:
            try:
                convert(
                    filename,
                    force=force,
                    digits=digits,
                    migration_units=migration_units
                )

            except Exception as exc:
                errors.append((filename, exc))
                click.echo(f'{filename}: {exc}', err=True)

            else:
                succesful.append(filename)

    if batch and len(succesful) > 1:
        batch = ZipFile(
            'abif.batch.zip',
            mode='w',
            compression=COMPRESSION,
            compresslevel=COMPRESSLEVEL
        )
        with batch:
            for filename in succesful:
                zipfile = pathlib.Path(filename)
                zipfile = zipfile.with_suffix(zipfile.suffix + SUFFIX)
                data_filename = pathlib.Path(filename)
                data_filename = data_filename.with_suffix(data_filename.suffix + '.data.1.txt')
                with ZipFile(zipfile, mode='r') as zfh, \
                        batch.open(str(data_filename), mode='w') as bfh:
                    bfh.write(zfh.read(data_filename.name))

    if len(filenames) == 1 and succesful:
        click.echo(f"File '{filename}' is converted.")

    elif len(filenames) > 1 and succesful:
        click.echo(f'{len(succesful)} out of {len(filenames)} files are converted.')

    if not succesful and patterns:
        raise click.ClickException('No files were converted.')

    if errors:
        click.exit(1)


if __name__ == '__main__':
    main()
