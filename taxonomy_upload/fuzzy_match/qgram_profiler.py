#!/usr/bin/python

import json
import csv
import subprocess
from argparse import ArgumentParser


argp = ArgumentParser(description='Profiles the performance of qgram approximate string matching for \
different values of the minimum similarity threshold.')
argp.add_argument('-o', '--fileout', required=True, help='an output CSV file name')
argp.add_argument('csv_file', help='the input CSV file')
argp.set_defaults()
args = argp.parse_args()

# Define the similarity threshold values to test.
test_max = 1.0
test_min = 0.1
test_steps = 19

# Generate the test similarity threshold values.
interval = (test_max - test_min) / (test_steps - 1)
testvals = [test_min + interval * cnt for cnt in range(test_steps - 1)]
testvals.append(test_max)
#print testvals

# Open and initialize the output CSV file.
fout = open(args.fileout, 'wb')
writer = csv.writer(fout)
writer.writerow(('simthreshold', 'correctpct', 'falsepospct', 'mean_rs_size'))

for testval in testvals:
    command = './fuzzy_test.py --method qgram --qgram_threshold {0} --output_format json {1}'
    command = command.format(testval, args.csv_file)

    print command
    resstr = subprocess.check_output(command, shell=True)
    res = json.loads(resstr)

    writer.writerow((testval, res['correctpct'], res['falsepospct'], res['mean_rs_size']))

fout.close()

