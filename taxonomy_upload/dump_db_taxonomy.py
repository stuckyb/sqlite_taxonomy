#!/usr/bin/python

import sys
from taxolib import taxodatabase
from taxolib.taxonomy import Taxonomy, TaxonomyError
from taxolib.taxoconfig import ConfigError
from argparse import ArgumentParser


argp = ArgumentParser(description='Prints a text representation of a taxonomy in the taxonomy database.  \
The only required argument is the taxonomy ID.  A database configuration file must be provided in order \
to connect to the taxonomy databse.  By default, "database.conf" is used, but an alternative configuration \
file name can be provided with the -d option.  If the target taxonomy is not the MOL backbone taxonomy, \
the program will automatically retrieve and display the higher taxa that link the target taxonomy to the \
root of the backbone taxonomy.  To disable this, use the -g flag.')
argp.add_argument('-n', '--numtaxa', type=int, help='the number of taxa to retrieve and print (all by default)')
argp.add_argument('-m', '--maxdepth', type=int, help='the maximum depth to traverse the taxa tree (no limit by default)')
argp.add_argument('-d', '--dbconf', help='the database configuration file ("database.conf" by default)')
argp.add_argument('-g', '--nohigher', action='store_true', help='do not retrieve higher taxa for this taxonomy')
argp.add_argument('taxonomy_id', type=int, help='the taxonomy ID')
argp.set_defaults(dbconf='database.conf', numtaxa=-1, maxdepth=-1)
args = argp.parse_args()

# Get a cursor for the taxonomy database.
try:
    pgcur = taxodatabase.getDBCursor(args.dbconf)
except ConfigError as e:
    exit('\n' + str(e) + '\n')

# Attempt to load the taxonomy from the database.
taxonomy = Taxonomy(args.taxonomy_id)
print 'Loading taxonomy from the database...'
try:
    taxonomy.loadFromDB(pgcur, args.numtaxa, args.maxdepth)
except TaxonomyError as e:
    exit('\n' + str(e) + '\n')
print 'done.\n'

if not(args.nohigher) and taxonomy.taxonomy_id != 1:
    # Get the nodes that connect this taxonomy to the root of the MOL backbone taxonomy.
    # Do not change the values of the depth properties for the nodes.
    print 'Retrieving higher taxa links...'
    if not(taxonomy.linkToBackbone(pgcur, False)):
        exit('\nError:\n  Could not retrieve higher taxa links for this taxonomy.\n')
    print 'done.\n'

    # Adjust the maximum traversal depth, if specified, to account for the extra
    # linking nodes.
    if args.maxdepth > -1:
        args.maxdepth += taxonomy.roottaxon.depth

taxonomy.printAll(args.numtaxa, args.maxdepth)

