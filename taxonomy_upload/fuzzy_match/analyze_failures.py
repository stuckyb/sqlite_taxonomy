#!/usr/bin/python

# Generates summary statistics for failed test cases data.

import sys
import csv
# A hack for now to get the local package to import.
sys.path.append('../')
from taxolib.csvtaxonomy import UnicodeDictReader
from argparse import ArgumentParser


argp = ArgumentParser(description='Generates summary statistics for the failed test cases data.')
argp.add_argument('-cf', '--comp_file', help='a failed cases CSV file with which to compare the main input file')
argp.add_argument('csv_file', help='the input CSV file')
argp.set_defaults(dbconf='../database.conf', comp_file='')
args = argp.parse_args()

# Open the CSV file.
fin = open(args.csv_file, 'rU')
reader = UnicodeDictReader(fin)

# Variables for counting the failure totals.
totalcnt = 0
causes = {}

# Variables for calculating mean string lengths.
strlen_search = 0
strlen_target = 0

# A list for all failed search strings.
searchstrs = []

for row in reader:
    cause = row['error']
    if cause not in causes:
        causes[cause] = 0

    causes[cause] += 1
    totalcnt += 1

    strlen_search += len(row['Genus'])
    strlen_target += len(row['standardGenus'])

    searchstrs.append(row['Genus'])

fin.close()

# Sort the causes and counts in descending order by count.
allcauses = sorted(causes.items(), key=lambda causecnt: causecnt[1], reverse=True)
#print allcauses

print '\n** Summary of failed test cases for', args.csv_file, '**\n'

for cause, cnt in allcauses:
    print cause + ':  ' + str(cnt) + ' (' + str(float(cnt) / totalcnt * 100) + '%)'
print

print 'Mean length of failed search strings:', (float(strlen_search) / totalcnt)
print 'Mean length of failed target strings:', (float(strlen_target) / totalcnt)
print

# If a second input CSV file name was provided, read it in and compare it.
if args.comp_file != '':
    fin = open(args.comp_file, 'rU')
    reader = UnicodeDictReader(fin)

    searchstrs2 = []
    for row in reader:
        searchstrs2.append(row['Genus'])

    ss1 = set(searchstrs)
    ss2 = set(searchstrs2)

    print '** Comparison of', args.csv_file, 'with', args.comp_file, '**\n'
    intsize = len(ss1.intersection(ss2))
    print (args.csv_file + ' has ' + str(intsize) + ' of ' + str(totalcnt) + ' search strings (' +
            str(float(intsize) / len(ss1) * 100) + '%) in common with ' + args.comp_file + '.\n')

    remain = ss1.difference(ss1.intersection(ss2))
    #print remain
    rlens = [len(sstr) for sstr in remain]
    print 'Search strings included in', args.csv_file, 'but not included in', args.comp_file + ':'
    print '  Maximum length:', max(rlens)
    print '  Minimum length:', min(rlens)
    print '  Mean length:', (float(sum(rlens)) / len(rlens))
    print

    remain = ss2.difference(ss1.intersection(ss2))
    #print remain
    rlens = [len(sstr) for sstr in remain]
    print 'Search strings included in', args.comp_file, 'but not included in', args.csv_file + ':'
    print '  Maximum length:', max(rlens)
    print '  Minimum length:', min(rlens)
    print '  Mean length:', (float(sum(rlens)) / len(rlens))
    print

