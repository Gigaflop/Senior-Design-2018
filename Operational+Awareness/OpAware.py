"""
Python Flask app for the IBM Operational Awareness SDP

Austin McKay

The updates listed below are the major ones that warrant description. Minor changes, like
function-specific tweaks aren't noted unless significant.

Update 4
    Added handling for a specific test case that improperly called something, getting an HTTP 500 error
    Merged Tom's introductory styles
    Integrated code for Slackbot
	Made JSON responses from API more consistent
	Cleaned up the template for the job page
	Added another one of Sam's graphs to the job page (Performance by day of the month)
	

    
Update 3, 3-20-2018:
    Rebuilt DB so that job duration is represented by a float
        Some duration values are still 0, but these should now be considered accurate
    Found out how to sort job times by quarter via SQL, and directly incorporate them into HTML templates
    Now using -1 to represent 'no data' for graphs and misc piles of data
    Graphs now have a lower-bound of -1 to look nicer
        If a job's average time is <3, it still looks weird, but this is the best I have at this time
    
    TODO:
        Write out a structure for all JSON responses to follow, for consistency's sake
            Then implement it
        Find out how Sam's graphs work, and find out how to feed them.
        Find out how to incorporate them in the styles
        Incorporate Tom's fancier-looking styles and formatting stuff on the frontend
        See if Merlina's POST call causes undefined behavior
        Slackbot integration in the realtime API?
        Deprecate/delete the API-based update, since there's no reason to have it in here
            After the actual project is functionally complete, create a separate update utility
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
    
.......



Server is visible to me at 127.0.0.1:5000

For future reference and later testing,
http://flask.pocoo.org/docs/0.12/quickstart/#public-server

This is now hosted on Bluemix, at operational-awareness.mybluemix.net
"""

import os
import json
import time
#import requests

import MySQLdb
from slackclient import SlackClient

from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash, make_response, jsonify

app = Flask(__name__)
app.config.from_object(__name__)

#Connection info for the MySQL database. Redact before posting to GitHub.
app.config.update(dict(
    HOST='',
    USER='',
    PORT=0,
    PASS='',
    DB='',

    SLACK_BOT_OAUTH_TOKEN='xoxb-',
    SLACK_BOT_CHANNEL='bot'
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

def get_slack_client():
    return SlackClient(app.config['SLACK_BOT_OAUTH_TOKEN'])

#########
# Context Processor for latest updated Templates
# Tom wrote this block to change page caching behavior
# 
@app.context_processor
def override_url_for():
    return dict(url_for=dated_url_for)

def dated_url_for(endpoint, **values):
    if endpoint == 'static':
        filename = values.get('filename', None)
        if filename:
            file_path = os.path.join(app.root_path,
                                     endpoint, filename)
            values['q'] = int(os.stat(file_path).st_mtime)
    return url_for(endpoint, **values)
#
#############

@app.teardown_appcontext
def close_db(error):
    #Closes database connection at end of request
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.disconnect()
    #Also close MySQL if we have it
    if hasattr(g, 'mysqldb'):
        g.mysqldb.close()

    
@app.route('/')
def home():
    return render_template("home.html")
    #return r"This is the first thing I was able to <b>accomplish</b>. Hooray."

"""
@app.route('/api')
def api_info():
    return r"At a later date, this will contain documentation about the API."
"""
#############
# API stuff #
#############


"""
This is the function that manages the realtime API.

Input: POSTed JSON
    ex. {'job_list': {'AIW42CJS': 4, 'DNE': 100}}
Output response:
    success: {'errors': {'DNE': 'KeyError'}, 'overtime': {'AIW42CJS': 1.0464788732394368}}
"""
@app.route('/api/realtime', methods=['POST'])
def api_check():
    #This is where current runtime data will be sent, i.e. runtime when a job is yet to complete.
    #This will compare it to historical data, and then 'say' something.
    
    if not request.get_json():# or not 'job_list' in request.json:
        return make_response(
            jsonify(
                {"error" :"no JSON," + str(request.values) + "," + str(request.get_json())}
                ), 200
            )
    if not 'job_list' in request.json:
        return make_response(
            jsonify(
                {"error": "No job_list in given JSON"}
                ), 200
            )
    """
    if not 'job_list' in request.values:
        return "job list not in request.values", 200
    """
    #We have a list of jobs, at minimum

    db = get_mysql_db()
    cur = db.cursor()

    sql = "SELECT * FROM jobs"
    num_rows = cur.execute(sql)

    if num_rows < 1:
        #something went wrong with the query, bail out
        return make_response(
            jsonify(
                {"error": "Database Query failure"}
                ), 200
            )
    #implicit else, continue


    #Convert results from tuples to a dict
    # ..., ('AIW42CJS', 71, 209.7), ...
    # ..., 'AIW42CJS' : 2.953521126760563, ...
    historical = dict(
        (name, time/runs) for name, runs, time in cur.fetchall()
        )
    #That's all we need from the database, will be closed at end of request


    #dicts instead of lists because we use jsonify later when crafting output
    overtime = {}
    errors = {}

    try:
        post_data = request.get_json()['job_list']#.to_dict()
    except TypeError:
        return make_response(
            jsonify(
                {"error": "TypeError in pulling out job_list"}
                ), 200
            )


    #following variables used to craft slack message later
    slack_jobs_total = len(post_data)
    slack_jobs_ok = 0
    slack_jobs_overtime = 0
    slack_jobs_errors = 0
    slack_error_types = {}
    slack_jobs_overtime_list = []

    for jobname in post_data:
        try:
            #1.2 used to represent the 20% longer threshold suggested by Mike

            try:
                #Separated like this because I was debugging something
                hist_limit = 1.2 * historical[jobname]
                t_current = post_data[jobname]
            except TypeError:
                slack_jobs_errors += 1
                
                #Error: job time not a number?
                #Below block increments the count for this particular error
                try:
                    slack_error_types['Given job time NaN'] += 1
                except KeyError:
                    slack_error_types['Given job time NaN'] = 1
                
            #Should this be moved to within the second try statement?
            if t_current >= hist_limit:
                #Job is overtime, add to overtime list
                overtime[jobname] = post_data[jobname] - historical[jobname]
                slack_jobs_overtime += 1
                slack_jobs_overtime_list.append((jobname, t_current, historical[jobname]))
            else:
                slack_jobs_ok += 1
                
                
        except KeyError:
            #Value not in dictionary. A new job appears? who knows.
            #Make note in response:
            slack_jobs_errors += 1
            errors[jobname] = 'KeyError'
            
            #Counting instances of error type
            try:
                slack_error_types['KeyError'] += 1
            except KeyError:
                slack_error_types['KeyError'] = 1
            
    #Done parsing through input


    #Crafting the Slack message
    line0 = "{} job times sent to API\n".format(slack_jobs_total)
    line1 = ":heavy_check_mark: {} jobs OK\n".format(slack_jobs_ok)
    line2 = ":question: {} jobs Overtime\n".format(slack_jobs_overtime)
    line3 = ":wavy_dash: {} jobs caused an error:\n".format(slack_jobs_errors)

    line4 = "Errors and counts: " + str(slack_error_types) + "\n"
    line5 = "Overtime Jobname, current runtime, average runtime:" + str(slack_jobs_overtime_list)

    message = line0 + line1 + line2 + line3 + line4 + line5
    
    #sending slack message
    slack_client = get_slack_client()
    if slack_client.rtm_connect(with_team_state=False):
        bot_id = slack_client.api_call("auth.test")["user_id"]
        slack_client.api_call(
                "chat.postMessage",
                channel=app.config['SLACK_BOT_CHANNEL'],
                text=message
            )
    else:
        #Connection failed, but continue
        #Make note of error in API response
        errors['Slackbot'] = "Failed to connect"

    #making API response        
    if len(overtime) == 0 and len(errors) == 0:
        #Nothing overtime, no errors
        return make_response(jsonify({"Message":"No overtime or errors"}), 200)
    elif len(overtime) > 0 and len(errors) > 0:
        #Some overtime, some errors
        return make_response(jsonify({"Message":"Overtime and Errors", 'overtime':overtime, 'errors':errors}), 200)
    elif len(overtime) > 0:
        #Only overtime
        return make_response(jsonify({"Message":"Only Overtime", 'overtime':overtime}), 200)
    elif len(errors) > 0:
        #Only errors
        return make_response(jsonify({"Message":"Only Errors", 'errors':errors}), 200)
    else:
        #All cases shouldbe covered, but just in case
        return make_response(jsonify({'Error':"Weird edge case. Something's broken?"}),200)

                                 
    return r"This is meant to be an API target in the future. You shouldn't see this text."


####
# I might remove this API method, since it doesn't really benefit us any more
# than writing a separate script to add updates. 
####
@app.route('/api/historical', methods=['POST'])
def api_insert():
    if not request.json or not 'jobID' in request.json or not 'duration' in request.json:
        #We don't have the name or duration of the job, or this isn't JSON.
        return make_response(jsonify({"Error":"No Job name or duration"}), 400)
        #abort(400)
        
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
        return make_response(jsonify({"Message":"None", "Error":"More than one row returned for {}".format(request.json['jobID'])}), 400)
        #abort(400)



    if not 't_started' in request.json or not 'weekday' in request.json or not 'run_date' in request.json:
        #We don't have the data to fill out the job-specific table entry
        flag = False;
        #return "updated main entry, not enough data for job-specific update", 200
        return make_response(jsonify({"Message":"Updated main table entry", "Error":"Unable to update detail table, not enough info"}), 200)

    if flag == True:
        #Now, update the job-specific table
        
        sql = "CREATE TABLE IF NOT EXISTS `{}` (id INT AUTO_INCREMENT primary key NOT NULL, sec_elapsed DOUBLE NOT NULL, t_started TIME, weekday VARCHAR(3), run_date DATE)".format(request.json['jobID'])
        cur.execute(sql)
        #Table known to exist

        sql = "INSERT INTO `{}` (sec_elapsed, t_started, weekday, run_date) VALUES (%s, %s, %s, %s)".format(request.json['jobID'])
        result = cur.execute(sql, (request.json['duration'], request.json['t_started'], request.json['weekday'], request.json['run_date'] ))
        
        db.commit() #forgot this, was troubleshooting for over an hour. Oops.
        #return "Inserted {} rows".format(result), 200
        return make_response(jsonify( {"Message":("Inserted {} rows".format(result)), "Error":"None"}), 200)
        #if result == 0:
        #    return "Failed to update job-specific data", 200
        #else:
        #    return "Updated job-specific data", 200
    #return "update successul", 200
    

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
    sql = "SELECT hour(t_started), AVG(sec_elapsed) FROM `{}` GROUP BY hour(t_started)".format(jobname)
    cur.execute(sql)
    by_hour_pre = list(cur.fetchall())
    #Above data is (hour, avg duration)
    
    by_hour = []
    for i in range(24):
        #24 hours in a day, and 24h clock is better than 12h
        if len(by_hour_pre) > 0:
            if i == by_hour_pre[0][0]:
                #First element of first tuple
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
    
    ###
    #This is for Sam's second graph - Job times by day of the month
    sql = "select DAY(run_date), AVG(sec_elapsed) from `{}` group by DAY(run_date)".format(jobname)
    num_rows = cur.execute(sql)
    results = list(cur.fetchall())

    #The loop below creates a list of lists, where each inner list is 2 elements
    #that represent a day of the month and the average elapsed time of the job for that day
    by_day = []
    #for i in range(31):
    for i in range(1, 32):
            if len(results) > 0:
                    if i == results[0][0]:
                            item = results.pop(0)
                            by_day.append([i, float(item[1])])
                    else:
                            by_day.append([i, -1])
            else:
                    by_day.append([i, -1])

    
    t2 = time.perf_counter() - t #'close off' the timer

    
    return render_template('sql_job.html',
                           by_quarter=by_quarter, monday=monday, timer=t2, alltime=all_runs,
                           hour_avg=str(by_hour), jobName=jobname, quarter=quarter, by_day=str(by_day))


#############################
# Stuff from the sample app #
#   Necessary for Bluemix   #
#############################
port = os.getenv('PORT', '5000')
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(port))
