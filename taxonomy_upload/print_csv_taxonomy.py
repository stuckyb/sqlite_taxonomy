#!/usr/bin/python

import sys
from taxolib import taxodatabase
from taxolib.taxacomponents import Citation
from taxolib.taxonomy import Taxonomy
from taxolib.taxoconfig import TaxonomyConfig, ConfigError
from taxolib.csvtaxonomy import CSVTaxonomyParser, TaxoCSVError
from argparse import ArgumentParser


argp = ArgumentParser(description='Prints a text representation of the taxonomy tree contained in \
a CSV taxonomy file.  Also prints metadata about the taxonomy from the taxonomy configuration file.  \
The only required argument is the location of a configuration file that specifies the input CSV file \
and how it should be parsed.  Parsing a CSV taxonomy file requires accessing taxonomic rank \
information in the taxonomy database, so a SQLite database file must be provided.  By default, \
"database.sqlite" is used, but an alternative database file can be provided using the -d option.')
argp.add_argument('-n', '--numtaxa', type=int, help='the number of taxa to print (all by default)')
argp.add_argument('-m', '--maxdepth', type=int, help='the maximum depth to traverse the taxa tree (no limit by default)')
argp.add_argument('-d', '--dbconf', help='the SQLite database file ("database.sqlite" by default)')
argp.add_argument('infile', help='the CSV taxonomy configuration file')
argp.set_defaults(dbconf='database.sqlite', numtaxa=-1, maxdepth=-1)
args = argp.parse_args()

# Get a cursor for the taxonomy database.
try:
    pgcur = taxodatabase.getDBCursor(args.dbconf)
except ConfigError as e:
    exit('\n' + str(e) + '\n')

# Attempt to read the configuration file and parse the input taxonomy CSV file.
taxoconfig = TaxonomyConfig()
taxoparser = CSVTaxonomyParser()
try:
    taxoconfig.read(args.infile)
    print 'Parsing input CSV taxonomy file...'
    taxonomyroot = taxoparser.parseCSV(taxoconfig, pgcur)
    print 'done.\n'
except (ConfigError, TaxoCSVError) as e:
    exit('\n' + str(e) + '\n')

# Get the citation configuration information and create the Citation object.
citation = Citation(*taxoconfig.getCitationSettings())

# Get the taxonomy information from the configuration file.
taxonomyid, taxonomyname, ismaster = taxoconfig.getTaxonomySettings()

# Create the Taxonomy object and print it to standard out.
taxonomy = Taxonomy(taxonomyid, taxonomyname, ismaster, citation, taxonomyroot)
taxonomy.printAll(args.numtaxa, args.maxdepth)

totalrows, totaltaxa = taxoparser.getStats()
print '\nProcessed', totalrows, 'CSV file rows containing', totaltaxa, 'unique taxa.\n'

