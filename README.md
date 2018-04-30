# Senior Design 2018
Code used in my Senior Design project, for IBM Operational Awareness. Using historical data, we  provide a tool that allows a user to gain insight into a mainframe job's average length. We provide per-job analysis based on the financial quarter it was run in, as well as the day of the munth it was run on.

We were given about 4,000 log files to test with, but these were all over the same month. The graphs would be more meaningful had we been given all 2 years of data. Furthermore, we would have been able to implement more meaningful visualizations such as performance for `current month at time of viewing`, `this day of this month`, and etc. We collected more data than we needed from the log files, so the team who takes over this project (and database) should be able to extend this.

A suggestion to that team would be to figure out how to link Jobs and Applications, so that analysis can be given on runtime of Applications.



# rmds-strip files
These scripts are used to scrape project-relevant data from RMDS log files.

`rmds-strip` is the most basic version, made to work with specific test data.

`rmds-strip-mp` implemented Multiprocessing, and a way to spoof input to test performance. Also adds a set of configurable options for thread count and output method.

`rmds-strip-mp-2` changed the scrape logic to fit differently-formatted log files that we got later. Logs used with this version don't work with older versions.

# Operational+Awareness
This is the working directory for the Operational Awareness Flask application. It contains `OpAware.py` and everything it needs to run, except for MySQL server login information and Slack bot token + channel. If all passwords were filled properly and the proper packages installed, you would be able to run the whole thing by running `OpAware.py`. 
