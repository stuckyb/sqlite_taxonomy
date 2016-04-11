#!/usr/bin/python

import sys
import time, timeit
import csv
import json
import approxmatch
from argparse import ArgumentParser
# A hack for now to get the local package to import.
sys.path.append('../')
from taxolib import taxodatabase, taxoconfig
from taxolib.csvtaxonomy import UnicodeDictReader


# Variables to track the "noise" associated with correct matches as well as the
# total number of false positives.
noisecnt = falseposcnt = 0

# Variables for keeping track of qgram similarity score statistics.
qminscore = 1
qmaxscore = qsumscore = 0
qminpair = None

def qgramMatch(pgcur, searchstr):
    """
    Searches for an approximate string match using trigram matching.  Returns
    a list of all candidate matches that exceed the similarity score threshold.
    Each item of the list is a tuple containing the candidate string and the
    similarity score.
    """
    query = """SELECT namestr, similarity(namestr, %s)
        FROM {0} n WHERE n.namestr %% %s""".format(args.table)

    #print pgcur.mogrify(query, (searchstr, searchstr))
    pgcur.execute(query, (searchstr, searchstr))
    results = pgcur.fetchall()

    return results

def processQgramResults(searchres, searchstr, correctstr):
    """
    Updates quantities used for calculating descriptive statistics of trigram
    approximate matching results, and checks if the correct name string was
    found by the approximate match search.  If so, returns True; otherwise,
    returns False.
    """
    global noisecnt, falseposcnt, qminscore, qmaxscore, qsumscore, qminpair

    correctmatch = False

    rescnt = 0
    for result in searchres:
        #print '  ' + result[0] + '; score: ' + str(result[1])
        rescnt += 1
        if result[0] == correctstr:
            correctmatch = True
            score = result[1]
            qsumscore += score

            if score < qminscore:
                qminscore = score
                qminpair = (searchstr, result[0])
            if score > qmaxscore:
                qmaxscore = score

    if correctmatch:
        noisecnt += rescnt

    if not(correctmatch) and rescnt > 0:
        falseposcnt += 1

    return correctmatch

def printQgramStats():
    global qminscore, qmaxscore, qsumscore, qminpair

    if qsumscore != 0:
        print 'Minimum similarity score for correct matches:', qminscore
        print 'Maximum similarity score for correct matches:', qmaxscore
        print 'Mean similarity score for correct matches:', (qsumscore / correctcnt)
        print 'Correct pair with minimum similarity score (possibly not unique):', ', '.join(qminpair), '\n'
    else:
        print 'No correct qgram matches were found.'

def processResults(searchres, correctstr):
    """
    Checks if the correct name string is included in a PostgreSQL result set for
    an approximate match search.  If so, returns True; otherwise, returns False.
    Also tracks the total number of results returned, which can be used to calculate
    the "noise" for correct matches; that is, on average, how precise is the
    algorithm in recovering the correct string?
    """
    global noisecnt, falseposcnt

    correctmatch = False

    rescnt = len(searchres)

    for result in searchres:
        #print '  ' + result[0]
        if result == correctstr:
            correctmatch = True

    if correctmatch:
        noisecnt += rescnt

    if not(correctmatch) and rescnt > 0:
        #print searchres, correctstr
        falseposcnt += 1

    return correctmatch

def processCSVFile(reader, matcher, calcstats=True, writer=None):
    """
    Processes the input CSV file by reading each row and executing a search for the incorrect
    name using the chosen search method.  If calcstats is True, then the results of each search
    are processed to see if the correct match was found and also calculate other performance
    metrics, such as the false positive count.  If a CSV writer is provided, and calcstats is
    True, information about failed matches will be written to the output file.  This function
    returns a tuple containing the total number of rows process and the total number of correct
    matches, in that order.
    """
    totalcnt = correctcnt = 0

    # Read each row and attempt an approximate match for each incorrect genus name.
    for row in reader:
        totalcnt += 1
        #print 'Incorrect name:', row['Genus']
        #print 'Correct name:', row['standardGenus']
    
        # Correct the character casing for the name string.
        searchname = row['Genus'][0].upper() + row['Genus'][1:].lower()
    
        results = matcher.match(searchname)

        if calcstats:
            correctmatch = False
            if False:#method == 'qgram':
                correctmatch = processQgramResults(results, row['Genus'], row['standardGenus'])
            else:
                correctmatch = processResults(results, row['standardGenus'])
    
            if correctmatch:
                correctcnt += 1
    
            if not(correctmatch) and writer != None:
                rowout = (row['Genus'], row['standardGenus'], row['error'])
                writer.writerow([item.encode('utf-8') for item in rowout])

    return (totalcnt, correctcnt)

def printStats(totalcnt, correctcnt, noisecnt, falseposcnt, outformat='text'):
    nomatch = totalcnt - correctcnt
    output = {
            'totalcnt': totalcnt,
            'correctcnt': correctcnt,
            'correctpct': float(correctcnt) / totalcnt * 100,
            'mean_rs_size': float(noisecnt) / correctcnt,
            'failcnt': nomatch,
            'falseposcnt': falseposcnt,
            'falsepospct': float(falseposcnt) / nomatch * 100
            }
    if outformat == 'text':
        print '\n' + str(totalcnt) + ' total incorrect names examined.'
        print 'Found ' + str(correctcnt) + ' corrected names (' + str(output['correctpct']) + '%).'
        print 'Mean result set size for correct matches:', output['mean_rs_size']
        print (str(falseposcnt) + ' total false positives out of ' + str(nomatch) +
                ' unsuccessful queries (' + str(output['falsepospct']) + '%).\n')

        if args.method == 'qgram':
            printQgramStats()
    else:
        print json.dumps(output)


class CodeTimer:
    """
    A simple timer object that calculates both the wall clock time and the processor time
    required to execute an arbitrary block of code or function.  Code can be timed either by
    calling the doTimer() method with a function object or by using an instance of CodeTimer
    as a context manager around a block of code.  CodeTimer "remembers" the elapsed wall
    clock and processor times for all timing requests until the reset() method is called.
    This makes it easy to calculate mean or minimum run times from multiple tests.
    """
    def __init__(self):
        self.wc_times = []
        self.p_times = []

    def reset(self):
        self.wc_times = []
        self.p_times = []

    def __enter__(self):
        self.wc_stime = timeit.default_timer()
        self.p_stime = time.clock()

    def __exit__(self, etype, evalue, etraceback):
        if etype == None:
            self.wc_times.append(timeit.default_timer() - self.wc_stime)
            self.p_times.append(time.clock() - self.p_stime)

    def doTimer(self, function, reps=1):
        for cnt in range(reps):
            with self:
                function()

    def getMeanWCTime(self):
        return sum(self.wc_times) / len(self.wc_times)

    def getMeanPTime(self):
        return sum(self.p_times) / len(self.p_times)

    def getMinWCTime(self):
        return min(self.wc_times)

    def getMinPTime(self):
        return min(self.p_times)


#nhood = generateK1Neighborhood('Ty')
#nhood = generateNeighborhood('Tyto', dist=1)
#print nhood
#print len(nhood)
#exit()

argp = ArgumentParser(description='Searches for taxa in the taxonomy database by matching the taxon name \
string.  "%" can be used as a wildcard character in the search string.')
argp.add_argument('-d', '--dbconf', help='the database configuration file ("database.conf" by default)')
argp.add_argument('-t', '--table', help='the database table name ("ftest_genus_names" by default)')
argp.add_argument('-wf', '--write_failed', help='a file name for writing failed matches in CSV format')
argp.add_argument('-i', '--timer', action='store_true', help='Enables timer mode.  Timer mode calculates \
the total run time for the name searches.  No post-search processing is done, which means that other \
performance statistics will not be displayed.')
argp.add_argument('-tr', '--timer_runs', type=int, help='The number of complete search runs to execute when \
running in timer mode.  The best time among all runs is taken as the final run time.  The default is 3.')
argp.add_argument('-m', '--method', help='the matching method to use ("exact", "qgram", "neighbor", \
"wcneighbor", "dmetaphone", "soundex", or "hybrid")')
argp.add_argument('-qgt', '--qgram_threshold', type=float, help='The similarity threshold to use for \
qgram-based matching.  The default is 0.3.')
argp.add_argument('-fo', '--output_format', help='The format for reporting results, either "text" \
[the default] or "json".')
argp.add_argument('csv_file', help='the input CSV file')
argp.set_defaults(dbconf='../database.conf', table='ftest_genus_names', write_failed='', timer_runs=3,
        method='qgram', qgram_threshold=0.3, output_format='text')
args = argp.parse_args()

# Get a cursor for the taxonomy database.
try:
    pgcur = taxodatabase.getDBCursor(args.dbconf)
except taxoconfig.ConfigError as e:
    exit('\n' + str(e) + '\n')

#nhoodMatch(pgcur, 'Anas')
#wcNhoodMatch(pgcur, 'Ictaluris')
#qgramMatch(pgcur, 'Anas')
#exit()

# Instantiate a matcher object for the requested match strategy.
if args.method == 'qgram':
    matcher = approxmatch.QgramMatcher(args.table, 'namestr', pgcur)
    # Set the qgram matching similarity threshold.
    matcher.setSimilarityCutoff(args.qgram_threshold)
elif args.method == 'exact':
    matcher = approxmatch.ExactMatcher(args.table, 'namestr', pgcur)
elif args.method == 'neighbor':
    matcher = approxmatch.DLMatcher(args.table, 'namestr', pgcur)
elif args.method == 'wcneighbor':
    matcher = approxmatch.DLMatcher(args.table, 'namestr', pgcur)
    matcher.setSearchMethod(approxmatch.DLMatcher.METHOD_WCNHOOD)
elif args.method == 'hybrid':
    matcher = approxmatch.HybridMatcher(args.table, 'namestr', pgcur)
elif args.method == 'soundex':
    matcher = approxmatch.SoundexMatcher(args.table, 'namestr', pgcur)
elif args.method == 'dmetaphone':
    matcher = approxmatch.DMetaphoneMatcher(args.table, 'namestr', pgcur)

if not(args.timer):
    # Run the test searches in non-timer mode.

    writer = None
    # If writing out failed matches is enabled, open the output file.
    if args.write_failed != '':
        fout = open(args.write_failed, 'wb')
        writer = csv.writer(fout)
        writer.writerow(('Genus', 'standardGenus', 'error'))

    # Open the input CSV file.
    fin = open(args.csv_file, 'rU')
    reader = UnicodeDictReader(fin)

    # Process the input file by executing a search for each input row.
    totalcnt, correctcnt = processCSVFile(reader, matcher, writer=writer)

    # Print the results.
    printStats(totalcnt, correctcnt, noisecnt, falseposcnt, args.output_format)
else:
    # Run the test searches in timer mode.

    timer = CodeTimer()

    for cnt in range(args.timer_runs):
        print 'Timing run ' + str(cnt + 1) + ' of ' + str(args.timer_runs) + '...'

        # Open the input CSV file.
        fin = open(args.csv_file, 'rU')
        reader = UnicodeDictReader(fin)

        # Calculate the time required to process all test cases.
        with timer:
            totalcnt = processCSVFile(reader, matcher, calcstats=False)[0]

        fin.close()

    #print timer.wc_times
    #print timer.p_times
    print '\nShortest total elapsed time:', timer.getMinWCTime(), 's'
    print 'Mean total elapsed time:', timer.getMeanWCTime(), 's\n'
    print 'Shortest elapsed processor time:', timer.getMinPTime(), 's'
    print 'Mean elapsed processor time:', timer.getMeanPTime(), 's\n'
    smtpquery = timer.getMinWCTime() / totalcnt
    amtpquery = timer.getMeanWCTime() / totalcnt
    tunit = 's'
    if smtpquery < 0.1:
        smtpquery *= 1000
        amtpquery *= 1000
        unit = 'ms'
    print 'Shortest mean time per query (mean query time for fastest test):', smtpquery, unit
    print 'Average mean time per query (mean query time across all tests):', amtpquery, unit, '\n'

