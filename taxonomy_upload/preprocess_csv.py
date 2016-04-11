#!/usr/bin/python

import sys
import csv
from taxolib.csvtaxonomy import UnicodeDictReader, UnicodeDictWriter
from argparse import ArgumentParser


argp = ArgumentParser(description='Provides methods for pre-processing source CSV taxonomy files in unusual \
formats so they can subsequently be used by the other taxonomy utilities.  Currently, only a single method \
is implemented: the ability to "expand" cells that contain multiple, newline-separated entries.  The \
transformed CSV file is printed to standard out.')
argp.add_argument('-m', '--maxrows', type=int, help='the maximum number of rows to process')
argp.add_argument('-c', '--colname', required=True, help='the column name to expand')
argp.add_argument('infile', help='the input CSV taxonomy file')
argp.set_defaults(maxrows=-1)
args = argp.parse_args()

# Get the column names and column order from the first row of the CSV file.
with open(args.infile, 'rU') as fin:
    reader = csv.reader(fin)
    colnames = reader.next()

# Create the CSV writer.
writer = UnicodeDictWriter(sys.stdout, colnames)
writer.writeheader()

with open(args.infile, 'rU') as fin:
    reader = UnicodeDictReader(fin, encoding='utf-8')

    rowcnt = 0
    for row in reader:
        # See if the specified column has multiple lines for this cell.
        clines = row[args.colname].splitlines()
        if len(clines) > 1:
            # Expand the cell contents to multiple rows in the output CSV text.
            for line in clines:
                row[args.colname] = line
                writer.writerow(row)
        else:
            # No multiple lines, so just output the row.
            writer.writerow(row)

        rowcnt += 1
        if rowcnt == args.maxrows:
            break

