"""
Python RMDS Log stripper
Strips RMDS log files for job name, and start/end date/times
"""
import os

"""
Scrapes the RMDS log file for our relevant info
"""
def scrapeLog( filepath ):
    #print("scraping")
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
    #return [jobName, jobStartD, jobEndD, jobStartT, jobEndT]
    return [jobName, jobStartT, jobEndT, jobStartD, jobEndD]

def main():
    data = [] #initialize an empty list
    for fileName in os.listdir("./RMDS-logs"):
        print ("fname: " + fileName)
        if fileName.endswith(".txt"):
            #Let's hope there's nothing but logs in here for now
            data.append(scrapeLog(os.path.join("./RMDS-logs", fileName)))
    for job in data:
        print (job)
        #Later, format as below:
        #name, start time, end time, start date, end date
#do the things
main()
