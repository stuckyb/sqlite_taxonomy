#!/usr/bin/python

import sys
from taxolib import taxodatabase
from argparse import ArgumentParser


argp = ArgumentParser(description='Prints a list of all taxonomies in a taxonomy database.')
argp.add_argument('-d', '--dbconf', help='the SQLite database file ("database.sqlite" by default)')
argp.set_defaults(dbconf='database.sqlite')
args = argp.parse_args()

# Get a cursor for the taxonomy database.
try:
    pgcur = taxodatabase.getDBCursor(args.dbconf)
except ConfigError as e:
    exit('\n' + str(e) + '\n')

query = 'SELECT name, taxonomy_id, ismaster FROM taxonomies'
pgcur.execute(query)
taxonomycnt = 0
for rec in pgcur:
    print '\nTaxonomy name:', rec[0]
    print '  ID:', rec[1]
    print '  Is MOL master:', rec[2]
    taxonomycnt += 1

if taxonomycnt > 0:
    print '\n{0} total taxonomies were found.\n'.format(taxonomycnt)
else:
    print '\nNo taxonomies were found.\n'

