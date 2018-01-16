"""
Python(ver 3.6.0) RMDS stripper using Multiprocessing

Revision 2
Written by Austin McKay

Strips RMDS log files for job name, and start/end date/time.

TODO:
* Add proper output methods from previous version 'rmds-strip-threaded.py'
* Remove methods not used since the Multiprocessing update?

"""

from multiprocessing import Pool
import os
import time

################################################################################
#Options
################################################################################

#Directory where the logs are hosted. Should only host RMDS logs.
#'./dir' means the directory named 'dir' within the current dirrectory.
input_directory = "./RMDS-logs-4096" 

#Number of worker threads. 1 means single-threaded.
num_threads = 4

#0 prints to screen, 1 prints to file, 2 discards results.
output_method = 2

#filename used when output_method = 1
#Given .format(strftime()) stuff produced 'RMDS_stripped_2017-11-02-20:26.txt'
output_filename = "RMDS_stripped_{}.txt".format( time.strftime("%Y-%m-%d-%H:%M", time.gmtime()) )

#A multiplier with which to spoof input files. 1 means 1x, 2 is 2x, etc.
#Spoofing with a value <= 1 has no effect.
input_spoof = 1

#Number of results to preview between multiprocessing and output. I use this for
#verification that thigns ran correctly.
results_preview = 3

################################################################################
#Code. Don't edit anything below this line
################################################################################

"""
Scrapes a given log file.
filepath: a b'string' filepath

return type: list of 5 strings
"""
def scrape( filepath ):
    jobName = ""
    
    jobStartD = ""
    jobEndD = ""

    jobStartT = ""
    jobEndT = ""
    with open(filepath) as file:
        for line in file:
            spl = line.split(" ")
            if "REPORT NAME" in line:
                jobName = line.split("=>")[1].rstrip()
            elif "MESSAGE HANDLER INITIALIZED." in line:
                jobStartD = spl[1]
                jobStartT = spl[2]
            elif "MESSAGE HANDLER CLOSED." in line:
                jobEndD = spl[1]
                jobEndT = spl[2]
    #file close happens on its own using 'with' operator
    return [jobName, jobStartT, jobEndT, jobStartD, jobEndD]

if __name__ == '__main__':
    #this is the main function

    work_pool = []
    #obtain files in directory
    for fileName in os.listdir(input_directory):
        if fileName.endswith(".txt"):  #We were given files that end with .txt, hence this assumption
            work_pool.append(os.path.join(input_directory, fileName))

    #Input spoofing for testing purposes
    if input_spoof > 1:
        #counter = len(results)
        for i in range(len(work_pool)):
            for j in range(input_spoof):
                work_pool.append(work_pool[i])
    ###########


    t_mp_work = time.time()
    #Multiprocessing code:
    results = []
    with Pool(num_threads) as p:
        results = p.map(scrape, work_pool)

    print("Time spent on multiprocessing with {} processes: {}"
          .format(num_threads, (time.time() - t_mp_work) ))
    
    #results_preview = 3
    for item in results: #Prints the first N results, if enough exist.
        print (item)
        results_preview -= 1
        if results_preview < 1:
            break
    
    print (len(results) , " total results")
    #Perform output
    t_output = time.time()
    if output_method == 0:
        #print results to screen
        for r in results:
            print( r[0] + "," + r[1] + "," + r[2] + "," + r[3] + "," + r[4] )
        print("Output takes ", (time.time() - t_output), "seconds")
    elif output_method == 1:
        #print to file as CSV
        #FILE OPENING STUFF
        with open( output_filename , 'w') as outfile:
            for r in results:
                #['AIWENRJ7', '22:14:08', '22:16:38', '2017/08/02', '2017/08/02']
                outfile.write(r[0] + "," + r[1] + "," + r[2] + ","
                              + r[3] + "," + r[4] + "\n")
        print("Output takes ", (time.time() - t_output), "seconds")
    elif output_method == 2:
        print("Output discarded due to selected option.")
