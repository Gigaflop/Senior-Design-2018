"""
Python(ver 3.6.0) RMDS stripper using Multiprocessing

Revision 3
Written by Austin McKay

Strips RMDS log files for job name, and start/end date/time.

TODO:
* Add proper file output
* Fix the thing that's not working but not exactly breaking

"""

from multiprocessing import Pool
import os
import time

################################################################################
#Options
################################################################################

#Directory where the logs are hosted. Should only host RMDS logs.
#'./dir' means the directory named 'dir' within the current dirrectory.
input_directory = r"C:\Users\Austin McKay\OneDrive\Documents\Classwork\SDP\box-logs\UConn Design Project" 

#Number of worker threads. 1 means single-threaded.
num_threads = 1

#0 prints to screen, 1 prints to file, 2 discards results.
output_method = 1

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

return type: list of 7 strings
"""
def scrape( filepath ):
    jobName = ""
    
    jobDay = ""
    jobDate = ""
    jobMonth = ""
    jobYear = ""

    jobStart = "____"
    jobTime = -0.1
    
    with open(filepath) as file:
        #file close happens on its own using 'with' operator
        fspl = filepath.split("RMDSXTCT.")[1]
        jobName = fspl.split('.')[0]

        for line in file:

            spl = line.split()
            
            if r'JOB/' in line:
                #Looking for job start time

                try:
                    #Several 'styles' are present in the logs.
                    if r'JOB/' in spl[0] and r'/START' in spl[0]:
                        jobStart = spl[1].split('.')[1]
                    elif r'JOB/' in spl[0] and r'/START' in spl[1]:
                        jobStart = spl[2].split('.')[1]
                    elif r'JOB/' in spl[1] and r'/START' in spl[1]:
                        jobStart = spl[2].split('.')[1]
                    elif r'JOB/' in spl[1] and r'/START' in spl[2]:
                        jobStart = spl[3].split('.')[1]

                except IndexError:
                    #In testing, I didn't need this, but there's no harm in leaving this here.
                    pass

                if ':' not in jobStart:
                    jobStart = jobStart[:2] + ':' + jobStart[2:]
                    #0113 becomes 01:13
            elif "THE CURRENT DATE" in line:
                #Looking for the start info (time isn't here)
                try:
                    if '----' in spl[11]:
                        #consistent between files
                        jobDay = spl[7].split(",")[0]     #MONDAY
                        jobDate = spl[8]   #31
                        jobMonth = spl[9]  #JUL
                        jobYear = spl[10]   #2017
                except IndexError:
                    #do nothing. Seems to be OK.
                    pass
                    
            #elif "STARTED - TIME=" in line:
            elif 'CPU: ' in line:
                #This can appear multiple times

                if 'CPU:' in spl[0]:
                    try:
                        jobTime = float(spl[1])*60*60 + float(spl[3])*60 + float(spl[5])
                        #jobTime = float(spl[1])*60*60
                        #jobTime += float(spl[3])*60
                        #jobTime += float(spl[5])
                    except ValueError:
                        jobTime = -0.2
                    except IndexError:
                        jobTime = -0.3
 
        return [jobName, jobStart, str(jobTime), jobDay, jobDate, jobMonth, jobYear]

if __name__ == '__main__':
    #this is the main function

    work_pool = []
    #obtain files in directory
    for fileName in os.listdir(input_directory):
        #if fileName.endswith(".txt"):  #We were given files that end with .txt, hence this assumption
        work_pool.append(os.path.join(input_directory, fileName))

    ###########
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
            print(r)
            #print( r[0] + "," + r[1] + "," + r[2] + "," + r[3] + "," + r[4] )
        print("Output takes ", (time.time() - t_output), "seconds")
    elif output_method == 1:
        #print to file as CSV

        outfile = open( output_filename , 'w+')
        for r in results:
            outfile.write( ','.join(r) + '\n')
        outfile.close()
        
        print("Output takes ", (time.time() - t_output), "seconds")
    elif output_method == 2:
        print("Output discarded due to selected option.")
