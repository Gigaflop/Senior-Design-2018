"""
Austin McKay

Update 2, 14-Feb-2018:
    Now hosted on Bluemix
    Pete gave us a MySQL instance to use
        Removed Cloudant-specific code
        Reworked MySQL-based code to work on new DB schema
    Added some fancier comments
    TODO:
        Sort job data by quarter
        Pad zeros where data DNE in the avg duration by-hour
        Pretty formatting
        Rebuild DB so that job duration is a float instead of int (0.01 seconds instead of 0)
Update 1:
    Locally hosted MySQL DB for testing
Update 0:
    I got Flask to start
    Using Cloudant NoSQL for testing because it's free
    




Server is visible to me at 127.0.0.1:5000

For future reference and later testing,
http://flask.pocoo.org/docs/0.12/quickstart/#public-server

This is now hosted on Bluemix, at operational-awareness.mybluemix.net
"""

import os
import json
import time

import MySQLdb

from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash, make_response

app = Flask(__name__)
app.config.from_object(__name__)

#Conenction info for the MySQL database. Redact before posting to GitHub.
app.config.update(dict(
    HOST='',
    USER='',
    PORT=0,
    PASS='',
    DB=''
    ))

#app.config.from_envvar('OpAware_SETTINGS', silent=True)

##########################
# MySQL Connection stuff #
##########################
def connect_mysql():

    #Pete's SQL server.
    db = MySQLdb.connect(host=app.config['HOST'], port=app.config['PORT'],
                         user=app.config['USER'], passwd=app.config['PASS'],
                         db=app.config['DB'])
    return db #still needs a cursor to execute statements.

def get_mysql_db():
    #Gets a connection object
    if not hasattr(g, 'mysqldb'):
        g.mysqldb = connect_mysql()
    return g.mysqldb #still needs a cursor to execute statements.

@app.teardown_appcontext
def close_db(error):
    #Closes database connection at end of request
    if hasattr(g, 'mysqldb'):
        g.mysqldb.close()

    
@app.route('/')
def home():
    return render_template("home.html")
    #return r"This is the first thing I was able to <b>accomplish</b>. Hooray."

#############
# API stuff #
#############
@app.route('/api')
def api_info():
    return r"At a later date, this will contain documentation about the API."

@app.route('/api/realtime', methods=['POST'])
def api_check():
    #This is where current runtime data will be sent, i.e. runtime when a job is yet to complete.
    #This will compare it to historical data, and then 'say' something.
    return r'This is meant to be an API target in the future.'

@app.route('/api/historical', methods=['POST'])
def api_insert():
    if not request.json or not 'jobID' in request.json or not 'duration' in request.json:
        #We don't have the name or duration of the job, or this isn't JSON.
        abort(400)
        
    #Otherwise, request should be ok
    db = get_mysql_db()
    cur = db.cursor()

    jobID = MySQLdb.escape_string(request.json['jobID'])
    duration = float(MySQLdb.escape_string(request.json['duration']))

        

    sql = "SELECT * FROM jobs WHERE jobID=%s"
    num_rows = cur.execute(sql, (request.json['jobID'],) )

    flag = False
    
    if num_rows == 1:
        #ID exists
        row = cur.fetchall()[0]
        #indexes are known based on database schema. Will need to be updated if schema changes.
        # [jobID, t_total, num_runs]
        time = float(row[2]) + duration
        runs = row[1] + 1

        sql = "UPDATE jobs SET t_total=%s, numRuns=%s where jobID=%s"
        cur.execute(sql, (time, runs, request.json['jobID']) )

        flag = True
        #return "update successful", 200
    elif num_rows == 0:
        #ID DNE, make new entry

        sql = "INSERT INTO jobs VALUES (%s,%s,%s)"
        cur.execute(sql, ( request.json['jobID'], 1, float(duration) ) )

        flag = True
        #return "Entry successful", 201
    else:
        #Duplicate entries detected, or something else weird.
        abort(400)



    if not 't_started' in request.json or not 'weekday' in request.json or not 'run_date' in request.json:
        #We don't have the data to fill out the job-specific table entry
        flag = False;
        return "updated main entry, not enough data for job-specific update", 200

    if flag == True:
        #Now, update the job-specific table
        
        sql = "CREATE TABLE IF NOT EXISTS `{}` (id INT AUTO_INCREMENT primary key NOT NULL, sec_elapsed INT NOT NULL, t_started TIME, weekday VARCHAR(3), run_date DATE)".format(request.json['jobID'])
        cur.execute(sql)
        #Table known to exist

        sql = "INSERT INTO `{}` (sec_elapsed, t_started, weekday, run_date) VALUES (%s, %s, %s, %s)".format(request.json['jobID'])
        result = cur.execute(sql, (request.json['duration'], request.json['t_started'], request.json['weekday'], request.json['run_date'] ))
        
        db.commit() #forgot this, was troubleshooting for over an hour. Oops.
        return "Inserted {} rows".format(result), 200
        #if result == 0:
        #    return "Failed to update job-specific data", 200
        #else:
        #    return "Updated job-specific data", 200
    return "update successul", 200
    

###############################
# Displaying jobs/job details #
###############################
@app.route('/mysql_test')
def sql_jobs():

    #Get all job names
    cur = get_mysql_db().cursor()
    cur.execute("SELECT * FROM jobs ORDER BY jobID ASC")
    results = cur.fetchall()
    
    #Pluck out the actual names from the entries. Data always comes as a tuple.
    names = []
    for row in results:
        names.append(row[0])
        
    return render_template('sql_test.html', entries=names)

@app.route('/mysql_test/<path:jobname>')
def sql_job(jobname):
    
    t = time.perf_counter()     #If something is slow, we want to know it's not Python
    cur = get_mysql_db().cursor()

    #Avg seconds elapsed for the job on Mondays
    #For test purposes
    sql = "SELECT AVG(sec_elapsed) FROM `{}` WHERE weekday=%s".format(jobname)
    cur.execute(sql, ('MON',))
    monday=cur.fetchall()
    
    #All the raw data we have on this job's individual runs
    #for test purposes
    sql = "SELECT * FROM `{}` ORDER BY run_date ASC".format(jobname) #In case it has # in the name
    cur.execute(sql)
    all_runs = cur.fetchall()

    #Avg seconds elapsed, per starting hour.
    #Useful for final product.
    ## TODO Make sure we add 0's where data DNE, and make note of it to user.
    sql = "SELECT hour(t_started), AVG(sec_elapsed) FROM `{}` GROUP BY hour(t_started)".format(jobname)
    cur.execute(sql)
    by_hour_pre = list(cur.fetchall())
    by_hour = []
    for i in range(24):
        if len(by_hour_pre) > 0:
            if i == by_hour_pre[0][0]:
                item = by_hour_pre.pop(0)
                by_hour.append( (i, float(item[1])) )
            else:
                by_hour.append( (i, -1))
        else:
            by_hour.append( (i, -1))

    #Avg seconds elapsed, per MySQL-defined QUARTER()
        #Ask Sponsors about what dates they want to use for quarters
    sql = "SELECT QUARTER(run_date), AVG(sec_elapsed) FROM `{}` GROUP BY QUARTER(run_date)".format(jobname)
    cur.execute(sql)
    by_quarter_pre = list(cur.fetchall())
    by_quarter = []
    quarter = []
    for i in range(1, 5):
        if len(by_quarter_pre) > 0:
            if i == by_quarter_pre[0][0]:
                item = by_quarter_pre.pop(0)
                by_quarter.append(item[1])
                quarter.append(float(item[1]))
            else:
                by_hour.append(0)
                quarter.append(-1)
        else:
            by_hour.append(0)
            quarter.append(-1)
    
    #for item in by_quarter_pre:
     #   by_quarter.append( (item[0], float(item[1])) )
    
    t2 = time.perf_counter() - t
    return render_template('sql_job.html',
                           by_quarter=by_quarter, monday=monday, timer=t2, alltime=all_runs,
                           hour_avg=str(by_hour), jobName=jobname, quarter=quarter)


#############################
# Stuff from the sample app #
#############################
port = os.getenv('PORT', '5000')
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(port))
