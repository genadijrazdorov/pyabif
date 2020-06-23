from pyabif import pyABIF

import click

import datetime
import pathlib
import csv
import zipfile
import io

IGNORE = frozenset('''
    Satd
    RMdX
    OfSc
    BufT
    APrX
'''.strip().split())

SECOND = datetime.timedelta(seconds=1)
MINUTE = datetime.timedelta(minutes=1)

LOG_TEMPLATE = '{filename}.log.{name}.csv'
DATA_TEMPLATE = '{filename}.data.{channel}.csv'
META_TEMPLATE = '{filename}.meta.csv'


def convert_meta(abif, zipfileobj):
    meta_filename = META_TEMPLATE.format(filename=pathlib.Path(abif.filename).stem)
    with zipfileobj.open(meta_filename, mode='w') as meta_bin, \
            io.TextIOWrapper(meta_bin, newline='') as meta:
        writer = csv.writer(meta)
        writer.writerow(('Tag', 'Number', 'Value', 'Description'))

        global IGNORE
        IGNORE |= frozenset(('DATA',))

        for item in abif.directory.keys():
            if item[0] in IGNORE:
                row = list(item) + ['', abif.tag2desc[item]]

            else:
                row = list(item) + [abif.read(*item), abif.tag2desc[item]]

            writer.writerow(row)


def convert(filename, force=False, digits=3):
    pathobj = pathlib.Path(filename)
    arch = pathobj.with_suffix(pathobj.suffix + '.csv.zip')
    if force:
        mode = 'w'
    else:
        mode = 'x'
    # zipfileobj = zipfile.ZipFile(arch, mode=mode)
    with zipfile.ZipFile(arch, mode=mode) as zipfileobj:
        with pyABIF(filename) as abif:
            convert_meta(abif, zipfileobj)

            start = datetime.datetime.combine(abif.RUND3, abif.RUNT3)
            stop = datetime.datetime.combine(abif.RUND4, abif.RUNT4)
            runtime = stop - start

            data_nums = (i for name, i in abif.directory.keys() if name == 'DATA')
            for i in data_nums:
                data = abif.read('DATA', i)
                descr = abif.tag2desc['DATA', i]
                if ',' in descr:
                    data_filename = LOG_TEMPLATE.format(
                        filename=pathobj.stem,
                        name=descr.split(',', 1)[0].lower()
                    )
                else:
                    data_filename = DATA_TEMPLATE.format(
                        filename=pathobj.stem,
                        channel=i
                    )

                with zipfileobj.open(data_filename, mode='w') as data_fh, \
                        io.TextIOWrapper(data_fh, newline='') as text_fh:
                    data_writer = csv.writer(text_fh)
                    data_writer.writerow(('Time', descr))
                    scan_time = runtime / len(data)

                    def row(j, I):
                        time = scan_time * j / MINUTE
                        return '{:.0{:d}f}'.format(time, digits), I

                    data_writer.writerows(row(j, I) for j, I in enumerate(data))


@click.command()
@click.argument(
    'filenames',
    nargs=-1,
    type=click.Path(exists=True, dir_okay=False)
)
@click.option(
    '-f', '--force',
    default=False,
    is_flag=True,
    show_default=True,
    help='Force conversion even if resulting file already exists'
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
def main(filenames, force=False, digits=3, migration_units='minutes'):
    '''Converts FILENAMES from ABIF to txt format

    FILENAMES are names of ABIF files to convert.
    '''
    errors = []
    succesful = []
    with click.progressbar(filenames, label='Files converted') as progress:
        for filename in progress:
            try:
                convert(filename, force=force, digits=digits)

            except Exception as exc:
                errors.append((filename, exc))
                click.echo(f'{filename}: {exc}', err=True)

            else:
                succesful.append(filename)

    if len(filenames) == 1 and len(succesful) == 1:
        click.echo(f"File '{filename}' is converted.")

    elif len(filenames) > 1:
        click.echo(f'{len(succesful)} out of {len(filenames)} files are converted.')

    if not succesful:
        raise click.ClickException('No files were converted.')

    if errors:
        click.exit(1)


if __name__ == '__main__':
    main()
