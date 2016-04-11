#!/usr/bin/python

import sys
from taxolib import taxodatabase
from taxolib.taxonomy import Taxonomy, TaxonomyError
from taxolib.taxacomponents import RankTable, Taxon
from taxolib.taxoconfig import ConfigError
from argparse import ArgumentParser


argp = ArgumentParser(description='Searches for taxa in the taxonomy database by matching the taxon name \
string.  "%" can be used as a wildcard character in the search string.')
argp.add_argument('-d', '--dbconf', help='the database configuration file ("database.conf" by default)')
argp.add_argument('-s', '--nosynonyms', action='store_true', help='do not synonyms for taxa names')
argp.add_argument('search_string', help='the name search string')
argp.set_defaults(dbconf='database.conf', numtaxa=-1, maxdepth=-1)
args = argp.parse_args()

# Get a cursor for the taxonomy database.
try:
    pgcur = taxodatabase.getDBCursor(args.dbconf)
except ConfigError as e:
    exit('\n' + str(e) + '\n')

# Initialize the rank table from the database.
ranktable = RankTable()
ranktable.loadFromDB(pgcur)

taxa = Taxon.find(pgcur, args.search_string, ranktable)

# Organize the taxa by their source taxonomies.
# Create a dictionary mapping taxonomy IDs to lists of taxa.
taxonomy_taxa = {}
for taxon in taxa:
    if taxon.taxonomy_id not in taxonomy_taxa:
        taxonomy_taxa[taxon.taxonomy_id] = []
    taxonomy_taxa[taxon.taxonomy_id].append(taxon)

# Print the results.
taxacnt = len(taxa)
taxonomycnt = len(taxonomy_taxa.keys())
if taxacnt > 1 and taxonomycnt > 1:
    msg = '\n{0} matching taxon concepts, from {1} taxonomies, were found:\n'
elif taxacnt > 1 and taxonomycnt == 1:
    msg = '\n{0} matching taxon concepts, from {1} taxonomy, were found:\n'
elif taxacnt == 1 and taxonomycnt > 1:
    msg = '\n{0} matching taxon concept, from {1} taxonomies, was found:\n'
elif taxacnt == 1 and taxonomycnt == 1:
    msg = '\n{0} matching taxon concept, from {1} taxonomy, was found:\n'
else:
    msg = '\nNo matching taxon concepts were found.\n'
print msg.format(taxacnt, taxonomycnt)

for taxonomy_id, taxa in taxonomy_taxa.iteritems():
    # Load the taxonomy metadata from the database.
    taxonomy = Taxonomy(taxonomy_id)
    taxonomy.loadFromDB(pgcur, maxdepth=0)

    taxostr = '*** Taxonomy: ' + taxonomy.name + ' (ID ' + str(taxonomy.taxonomy_id)
    if taxonomy.ismaster:
        taxostr += ', MOL master taxonomy) ***'
    else:
        taxostr += ') ***'
    print taxostr

    if len(taxa) > 1:
        print '(' + str(len(taxa)) + ' taxon concepts)'

    for taxon in taxa:
        print taxon
        if not(args.nosynonyms):
            synstr = taxon.getSynonymsString()
            if synstr != '':
                print '  -- Synonyms: ' + synstr

    print

