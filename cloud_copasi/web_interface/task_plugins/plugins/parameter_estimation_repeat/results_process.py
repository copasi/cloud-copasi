#!/usr/bin/python
#-------------------------------------------------------------------------------
# Cloud-COPASI
# Copyright (c) 2013 Edward Kent.
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the GNU Public License v3.0
# which accompanies this distribution, and is available at
# http://www.gnu.org/licenses/gpl.html
#-------------------------------------------------------------------------------

#Script to process output from stochastic simulation task
#Assumes that a file called raw_results.txt is in the current working directory
#Writes to a file called results.txt

import sys


class IncrementalStats:
    """Class for calculating mean and standard deviation incrementally; ensures not having to load all results into memory"""
    def __init__(self):
        self.n = 0

    def add(self, x):
        x = float(x)
        self.n += 1
        if self.n == 1:
            self.mean = x
            self.variance = 0.0
        else:
            #Algorithm for incremental mean and variance by B. P. Welford, Technometrics, Vol. 4, No. 3 (Aug., 1962), pp. 419-420

            last_mean = self.mean
            last_variance = self.variance
           
            self.mean = last_mean + ((x - last_mean) / self.n)
            self.variance = last_variance + ((x - last_mean)*(x - self.mean))
           
    def get_mean(self):
        return self.mean
       
    def get_variance(self):
        if self.n > 1:
            return self.variance / (self.n - 1)
        else:
            return 0.0
       
    def get_stdev(self):
        import math
        return math.sqrt(self.get_variance())

#Arguments are the list of files. First arg wille be script name so ignore
files = sys.argv[1:]

#Go through the first file and find out how many time points there are
timepoints = -1 #Start at -1 to ignore the header line
for line in open(files[0], 'r'):
    if line == '\n':
        break
    timepoints += 1
#find out how many columns are in the file
file1 = open(files[0], 'r')
firstline = file1.readline()
secondline = file1.readline()
cols = len(secondline.split('\t'))
file1.close()

#Create a new file called results.txt, and copy the header line over
file1 = open(files[0], 'r')
header_line = file1.readline().rstrip().split('\t')
file1.close()

#Create a new header line, by putting in stdev headings
new_header_line = header_line[0] + '\t'
for header in header_line[1:]:
    new_header_line = new_header_line + header + ' (Mean)\t' + header + ' (STDev)\t'

new_header_line = new_header_line.rstrip() + '\n'


output = open('results.txt', 'w')
output.write(new_header_line)
output.close()

#Create list of objects to store means and stdevs as we read through the file

results = [[0] + [IncrementalStats() for c in range(cols-1)] for t in range(timepoints)]

for filename in files:
    print 'reading ' + filename
    line_count = 0
    for line in open(filename, 'r'):
        timepoint = line_count % (timepoints + 1)            
        if timepoint == 0:
            pass # The first line contains the headers, all other sets of timepoints are separated by a newline
        else:
            try:
                line_cols = line.rstrip().split('\t')
               
                #Store the timepoint
                results[timepoint-1][0] = float(line_cols[0])
               
                #And add the particle numbers
                for i in range(cols)[1:]:
                    result = float(line_cols[i])
                    results[timepoint-1][i].add(result)
            except:
                print i
                print line_cols
                print timepoint
                print results[0][0]
                print len(results)
                print results[timepoint-1]
                raise
        line_count += 1


output_file = open('results.txt', 'a')    
for i in range(len(results)):
    #Write the time point
    output_file.write(str(results[i][0]))
    output_file.write('\t')
    #And write the means and stdevs
    for col in range(len(results[i]))[1:]:
        output_file.write(str(results[i][col].get_mean()))
        output_file.write('\t')
        output_file.write(str(results[i][col].get_stdev()))
        #don't put a tab at the end of the last column
        if col != len(results[i])-1:
            output_file.write('\t')
    output_file.write('\n')
   
output_file.close()
