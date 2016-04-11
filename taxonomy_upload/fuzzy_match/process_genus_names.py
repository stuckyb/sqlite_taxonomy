#!/usr/bin/python

import sys
# An ugly hack for now to get the local package to import.
sys.path.append('../')
from taxolib import taxodatabase
from taxolib.csvtaxonomy import UnicodeDictReader
from argparse import ArgumentParser


argp = ArgumentParser(description='Loads a list of valid genus names from a CSV file into a PostgreSQL database table.')
argp.add_argument('-d', '--dbconf', help='the database configuration file ("../database.conf" by default)')
argp.add_argument('-t', '--table', help='the database table name ("ftest_genus_names" by default)')
#argp.add_argument('-s', '--nosynonyms', action='store_true', help='do not synonyms for taxa names')
argp.add_argument('csv_file', help='the input CSV file')
argp.set_defaults(dbconf='../database.conf', table='ftest_genus_names')
args = argp.parse_args()

# Get a cursor for the taxonomy database.
try:
    pgcur = taxodatabase.getDBCursor(args.dbconf)
except ConfigError as e:
    exit('\n' + str(e) + '\n')

# Empty the table.
pgcur.execute('TRUNCATE TABLE {0}'.format(args.table))

# Open the CSV file.
fin = open(args.csv_file, 'rU')
reader = UnicodeDictReader(fin)

# Read each row, building up a list of unique accepted genus names.
genera = []
cnt = 0
for row in reader:
    cnt += 1
    if row['standardGenus'] not in genera:
        genera.append(row['standardGenus'])

print '\nFound', len(genera), 'unique genus names in', cnt, 'CSV file rows.\n'

# Insert the rows into the database.
query = 'INSERT INTO {0} (namestr) VALUES (%s)'.format(args.table)
for gname in genera:
    pgcur.execute(query, (gname,))

pgcur.connection.commit()

