import os, sys, time, csv, re, requests, sqlite3
from datetime import datetime

param = {}                              # List to store settings from api_transmit.cfg
ts_fmt = '%Y-%m-%d %H:%M:%S'            # Timestamp format
debug = True                            # Running mode when module is invoked from terminal prompt (for debugging messages)

def init_start():

    # Open detections file in Read mode to generate new API transactions
    global detections
    detections = open("/home/pi/detections.csv", mode="r")

    # If processing has not started yet, create pointer to next line in detections.csv
    if not os.path.isfile("/home/pi/next_read.csv"):
        with open('/home/pi/next_read.csv', 'a') as c:
            c.write('1\n')

    # Load settings from configuration file - will vary depending on 3rd party race management used
    # API_endpoint to 3rd party race management software to insert passing times
    # loop_wait - delay in minutes between checks 
    # ev_start - required by RaceResult to provide relative checkpoint times
    # cp_name - Checkpoint name that must match the one defined in RaceResult
    global loop_wait, ev_start, cp_name
    with open('/home/pi/api_transmit.cfg', 'r') as c:
        for line in c:
            if re.match('^\s*$', line): continue
            elif re.match('^# ', line): (k, v) = (line, "")
            else: (k, v) = line.split('=')
            param[k.strip()] = v.strip()
    loop_wait = int(param["loop_wait"]) * 60
    ev_start = datetime.strptime(param['ev_start'], ts_fmt)
    cp_name = param["cp_name"]
    
    # Load lookup dictionary for matching EPCs with bib numbers
    global bibs_lookup
    with open('/home/pi/bibs_lookup.csv') as f:
        bibs_lookup = dict(filter(None, csv.reader(f))) 

    # Create or Connect to SqLite transactions database with Autocommit
    global conn, cur1, cur2
    conn = sqlite3.connect('/home/pi/detections.db', isolation_level=None)
    cur1 = conn.cursor()
    cur2 = conn.cursor()
    if os.path.getsize('/home/pi/detections.db') == 0:
        create_table =  """ CREATE TABLE api_reqs (cpname TEXT NOT NULL, epc TEXT NOT NULL, bibtime TEXT,
            rssi INT, bibno INT, rcode INT, PRIMARY KEY (cpname, epc) ON CONFLICT IGNORE ); """
        cur1.execute(create_table)

def my_print(s):
    # Display messages when launched via terminal prompt, otherwise recorded in syslog
    if debug: print(str(datetime.now()) + " " + s)
    else: print("SCapi_transmit - " + s)

def insert_reqs():
    # Bypass if no detections have been recorded yet
    if os.path.getsize('/home/pi/detections.csv') == 0: return
    # Retrieve line pointer to the next recorded detection to process
    s = open('/home/pi/next_read.csv', 'r').read()
    next_read = int(s)
    # Look for new detections since last time we checked
    new_detections = []
    with open('/home/pi/detections.csv', 'r') as file:
        reader = csv.reader(file)
        for i, line in enumerate(reader, 1):
            if i >= next_read:
                new_detections.append(line)
    if new_detections:
        for line in new_detections:
            # Insert a new row in the SQL table for each new passing time
            bibno = bibs_lookup.get(line[0],0) # Match bib number with EPC - if no match, bibno will be 0
            row = 'INSERT INTO api_reqs VALUES(\"'+cp_name+'\",\"'+line[0]+'\",\"'+line[2]+'\",'+line[1]+','+str(bibno)+',NULL)'
            cur1.execute(row)
        # Update file pointer for next check
        with open('/home/pi/next_read.csv', 'w') as c:
            new_read = str(next_read + len(new_detections))
            c.write(new_read+'\n')

def submit_api():
    # Submit all pending db transactions to the RaceResult API
    cur1.execute("SELECT * FROM api_reqs WHERE bibno IS NOT 0 and rcode IS NULL")
    nb_updates = 0
    for row in cur1:
        bibsecs = int((datetime.strptime(row[2], ts_fmt) - ev_start).total_seconds())
        rr12_api = "TimingPoint=" + row[0] + "&bib=" + str(row[4]) + "&Time=" + str(bibsecs) + "&addT0=0"
        for attempt in range(1, 4):
            resp = requests.get(url = param['API_endpoint'], params = rr12_api)
            if resp.status_code in (406,500) and attempt < 3:
                my_print('WARNING 406/500 Bib ' + str(row[4]) + ' @ ' + row[0] + ' - Upload failed...trying again')
                time.sleep(1) # Waiting one second between API calls - limit imposed by RaceResult
            else:
                cur2.execute('UPDATE api_reqs SET rcode = '+str(resp.status_code)+' WHERE cpname = \"'+row[0]+'\" AND epc = \"'+row[1]+'\"')
                nb_updates += 1
                my_print('INFO Bib # ' + str(row[4]) + ' @ ' + row[0] + ' - RR response: ' + str(resp.status_code))
                break
    if nb_updates > 0 : my_print('INFO Processing completed for ' + str(nb_updates) + ' passing times in RR')

# Main program loop with error handling
if __name__ == '__main__':
    if (len(sys.argv) > 1 and sys.argv[1] == "silent"): debug = False
    try:
        init_start()
        while True:
            insert_reqs()
            submit_api()
            print("Waiting " + str(loop_wait) + " seconds until next transmission to race management system")
            time.sleep(loop_wait)
    except Exception as e:
        my_print('ERROR api_transmit Exception: ' + str(e))