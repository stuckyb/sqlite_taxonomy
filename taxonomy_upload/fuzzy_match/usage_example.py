#!/usr/bin/python

# This program provides a simple example of how to use the approximate string
# matching search library.  Note that this requires only 2 lines of code: 1 to
# instantiate a matcher object, and 1 to actually perform the match.

import sys
import approxmatch
# A hack for now to get the local taxonomy package to import.
sys.path.append('../')
from taxolib import taxodatabase, taxoconfig


# Get a cursor for the taxonomy database.
try:
    pgcur = taxodatabase.getDBCursor('../database.conf')
except taxoconfig.ConfigError as e:
    exit('\n' + str(e) + '\n')

if len(sys.argv) != 2:
    exit('\nPlease provide a name to search for in the names table.\n')

searchstr = sys.argv[1]

# Specify the database table and column names.
#tablename = 'names'
tablename = 'ftest_genus_names'
colname = 'namestr'

# Instantiate a q-gram/DL hybrid algorithm matcher.
matcher = approxmatch.HybridMatcher(tablename, colname, pgcur)

# Search for the specified target string.
results = matcher.match(searchstr)

print '\nApproximate matches for ' + searchstr + ':'
for result in results:
    print '  ' + result
print

