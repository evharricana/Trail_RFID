
import os, re, time
from http.server import BaseHTTPRequestHandler, HTTPServer

port_number = 80    # Must launch with elevated security ("sudo...") when using port 80

class MyServer (BaseHTTPRequestHandler):
    def do_GET(self):
        
        # http://hostname/help - Display list of possible commands
        if self.path == "/help":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(bytes("/stat   : Display current status of Raspberry PI unit\n", "utf-8"))
            # self.wfile.write(bytes("/send   : Trigger an immediate and complete transmission of all passing times\n", "utf-8"))
            self.wfile.write(bytes("/csv    : Download a copy of the detections.csv file on your device\n", "utf-8"))
            self.wfile.write(bytes("/reboot : Restart Raspberry PI - requires about 1 minute\n", "utf-8"))
            self.wfile.write(bytes("/down   : Shutdown Raspberry PI - make sure to physically turn OFF device afterwards\n", "utf-8"))
            self.wfile.write(bytes("\n", "utf-8"))
       
        # http://hostname/stat - Display various status information from Raspberry PI
        elif self.path == "/stat":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            # Uptime and count/last passing detected/transmitted
            self.wfile.write(bytes("UPTIME and DETECTIONS/TRANSMISSIONS:\n", "utf-8"))
            os.system('/usr/bin/uptime > /tmp/RPI_stat')
            os.system('/usr/bin/wc -l /home/pi/detections.csv >> /tmp/RPI_stat')
            os.system("/usr/bin/tail -1 /home/pi/detections.csv >> /tmp/RPI_stat")
            with open('/tmp/RPI_stat', 'r') as f:
                c = f.read()
            self.wfile.write(bytes(c, "utf-8"))
            # Status of services (not necessary to check http_serveur)
            self.wfile.write(bytes("\nSERVICES:\n", "utf-8"))
            os.system('/usr/bin/systemctl --no-pager -n5 -l status SCscan_rfid.service > /tmp/RPI_stat')
            os.system('/usr/bin/systemctl --no-pager -n5 -l status SCsend_times.service >> /tmp/RPI_stat')
            with open('/tmp/RPI_stat', 'r') as f:
                c = f.read()
                c = re.sub(r'[^\x00-\x7F]', '', c)
            self.wfile.write(bytes(c, "utf-8"))
            # Recent errors logged
            self.wfile.write(bytes('\nRECENT ERRORS LOGGED:\n', "utf-8"))
            os.system('/usr/bin/journalctl --no-page -n5 -u SCscan_rfid | fgrep ERROR > /tmp/RPI_stat')
            os.system('/usr/bin/journalctl --no-page -n5 -u SCsend_times | fgrep ERROR >> /tmp/RPI_stat')
            with open('/tmp/RPI_stat', 'r') as f:
                c = f.read()
            self.wfile.write(bytes(c, "utf-8"))
            
        # http://hostname/send - Trigger an immediate and complete transmission of all passing times
        # elif self.path == "/send":
        #    self.send_response(200)
        #    self.send_header("Content-Type", "text/plain")
        #    self.end_headers()
        #    os.system("touch /home/pi/sendnow")
        #    self.wfile.write(bytes('EXPRESS TRANSMISSION REQUEST ACCEPTED\n', "utf-8"))

        # http://hostname/csv - Download a copy of the detections.csv file on your device
        elif self.path == "/csv":
            if os.path.isfile('/home/pi/detections.csv') == True:
                self.send_response(200)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                with open('/home/pi/detections.csv', 'r') as f:
                    content = f.read()
                self.wfile.write(bytes(content, "utf-8"))
            else:
                self.send_response(400)
                self.end_headers()          
        
        # http://hostname/reboot - Restart Raspberry PI - requires about 1 minute
        elif self.path == "/reboot":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(bytes('RESTART INITIATED... WAIT 60 SECONDS', "utf-8"))
            os.system("sudo /usr/sbin/reboot")

        # http://hostname/down" - Shutdown Raspberry PI - make sure to physically turn off device
        elif self.path == "/down":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(bytes('SHUTDOWN INITIATED...\n', "utf-8"))
            self.wfile.write(bytes('MAKE SURE TO SWITCH UNIT *OFF* BEFORE DISCONNECTING ANTENNA\n', "utf-8"))
            os.system("sudo /usr/sbin/shutdown now")

        # Reject any other request
        else:
            self.send_response(400)
            self.end_headers()

if __name__ == '__main__':
    webServer = HTTPServer(('', port_number), MyServer)
    print("Server started http://%s:%s" % ('', port_number))
    try:
        webServer.serve_forever()
    except KeyboardInterrupt:
        pass
    webServer.server_close()
    print("Server stopped.")
