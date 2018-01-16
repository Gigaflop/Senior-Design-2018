# Senior-Design-2018
Code used in my Senior Design project, for IBM Operational Awareness. Using historical data, we (will be) provide a tool that allows a user to gain insight into a mainframe job's average length.

# rmds-strip files
These scripts are used to scrape project-relevant data from RMDS log files.

`rmds-strip` is the most basic version, made to work with specific test data.

`rmds-strip-mp` implemented Multiprocessing, and a way to spoof input to test performance. Also adds a set of configurable options for thread count and output method.

`rmds-strip-mp-2` changed the scrape logic to fit differently-formatted log files that we got later. Logs used with this version don't work with older versions.

# flaskSpace
This (will be) where the Flask code is placed.
