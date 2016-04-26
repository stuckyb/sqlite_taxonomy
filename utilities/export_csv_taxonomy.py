#!/usr/bin/python

import sys
from taxolib import taxodatabase
from taxolib.taxonomy import Taxonomy, TaxonomyError
from taxolib.taxoconfig import ConfigError
from argparse import ArgumentParser


argp = ArgumentParser(description='Exports a CSV representation of a taxonomy in the taxonomy database.  \
The only required argument is the taxonomy ID.  A SQLite database file must also be available.  \
By default, "database.sqlite" is used, but an alternative database file name can be provided with the -d \
option.')
argp.add_argument('-n', '--numtaxa', type=int, help='the number of taxa to retrieve and print (all by default)')
argp.add_argument('-m', '--maxdepth', type=int, help='the maximum depth to traverse the taxa tree (no limit by default)')
argp.add_argument('-d', '--dbconf', help='the SQLite database file ("database.sqlite" by default)')
argp.add_argument('taxonomy_id', type=int, help='the taxonomy ID')
argp.set_defaults(dbconf='database.sqlite', numtaxa=-1, maxdepth=-1)
args = argp.parse_args()

# Get a cursor for the taxonomy database.
try:
    pgcur = taxodatabase.getDBCursor(args.dbconf)
except ConfigError as e:
    exit('\n' + str(e) + '\n')

# Attempt to load the taxonomy from the database.
taxonomy = Taxonomy(args.taxonomy_id)
try:
    taxonomy.loadFromDB(pgcur, args.numtaxa, args.maxdepth)
except TaxonomyError as e:
    exit('\n' + str(e) + '\n')

taxonomy.printCSVTaxaTree(args.numtaxa, args.maxdepth)

