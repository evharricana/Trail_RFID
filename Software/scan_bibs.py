import sys
import time
import _thread
import mercury
import RPi.GPIO as GPIO
from datetime import datetime
from gpiozero import CPUTemperature

rfid_baudrate = 57600       # Speed of M6e Nano serial port (max. 115200)
rfid_readpower = 2700       # RF power setting (max. 5dBm board antenna or 27dBm external antenna)
rfid_powermode = "MAXSAVE"  # M6e Nano standby power setting (FULL .84W<8ms or MAXSAVE .04W<20ms)
pir_gpio = 24               # Motion sensor input (PIN 17 3.3v, pin 18 GPIO, PIN 20 ground)
pir_start = 5               # Motion sensor signal stabilization delay (seconds)
led_red_gpio = 21           # RED LED output to indicate RFID detections (PIN 40 GPIO, PIN 39 ground)
led_green_gpio = 20         # GREEN LED output to indicate status, also used by send_times.py (PIN 38 GPIO, PIN 39 ground)
fan_gpio = 23               # Fan control output (PIN 16 GPIO, 5vdc and ground from voltage regulator)
temp_high = 70              # Temperature upper limit (Celsius) for M6e Nano or RPI over which the fan is activated
temp_low = 60               # Temperature lower limit (Celsius) for M6e or RPI below which the fan is deactivated
temp_m6e = 0                # Global variable to store current temperature of the M6e Nano
temp_check = 180            # Time interval (seconds) between temperature checks
lag_wait = 5                # Delay (seconds) before M6e Nano goes in standby after motion sensor returns low
debug = True                # Running mode when module is invoked from terminal prompt (for debugging messages)
epc_sav = b'0'              # Global variable storing most recent tag detected, to eliminate consecutive duplicate reads

def init_start():
    # Configure motion sensor, both LEDs and fan control
    GPIO.setwarnings(False) 
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(pir_gpio, GPIO.IN)
    GPIO.setup(led_green_gpio, GPIO.OUT)
    GPIO.setup(led_red_gpio, GPIO.OUT)
    GPIO.setup(fan_gpio, GPIO.OUT)
    # Motion sensor signal stabilization
    time.sleep(pir_start)
    # Initialize M6e Nano RFID reader and adjust settings
    global reader
    reader = mercury.Reader("tmr:///dev/ttyUSB0", baudrate=rfid_baudrate)
    reader.set_region("NA2")
    reader.set_read_plan([1], "GEN2", bank=["epc"], read_power=rfid_readpower)
    reader.set_gen2_session(2)
    reader.set_gen2_tagencoding(3)
    reader.set_powermode(rfid_powermode)
    reader.enable_stats(m6e_stats)
    reader.enable_exception_handler(m6e_exceptions)
    # Create/open file to store tags read in Append mode
    global detections
    detections = open("/home/pi/detections.csv", mode="a")
    # Verify M6e Nano settings (during testing only)
    if debug:
        print("BLF 0=250kHz): ", reader.get_gen2_blf())
        print("Tari 0=25us, 1=12.5us, 2=6.25us : ", reader.get_gen2_tari())
        print("Tag Encoding 0=FM0, 1=M2, 2=M4, 3=M8 : ", reader.get_gen2_tagencoding())
        print("Tag Session 0=illimited, 1=delay 0.5-5 secs, 2= delay 2 secs : ", reader.get_gen2_session())
        print("Tag Target 0=A(tags ready to answer), 1=B(tags waiting), 2=AB, 3=BA : ", reader.get_gen2_target())
        print("Q Type (0,x)=Dynamic, (1,x)=Static : ", reader.get_gen2_q())
    # Blink both LEDs 5 times to confirm successful start and make entry in syslog
    for i in range(1,6):
        GPIO.output(led_green_gpio, True)
        GPIO.output(led_red_gpio, True)
        time.sleep(0.5)
        GPIO.output(led_green_gpio, False)
        GPIO.output(led_red_gpio, False)
        time.sleep(0.5)
    my_print('INFO M6e Reader initialized')

def m6e_stats(stats):
    # Save the current M6e Nano temperature, invoked at each tag read
    global temp_m6e
    temp_m6e = stats.temperature

def m6e_exceptions(e):
    # Exception error handling invoked by the M6e Nano - to notify via LEDs of critical failures
    if (str(e) == 'Timeout'):
        my_print("ERROR M6e Timeout Exception")
        if 'detections' in globals(): detections.flush()
        led_except()
    else:
        my_print("ERROR M6e Other Exception: " + str(e))

def my_print(s):
    # Display messages when launched via terminal prompt, otherwise recorded in syslog
    if debug: print(str(datetime.now()) + " " + s)
    else: print("SCscan_bibs - " + s)

def led_except():
    # Red and Green LEDs blink continuously at 3 seconds interval to indicate critical failure
    while True:
        GPIO.output(led_green_gpio, True)
        GPIO.output(led_red_gpio, True)
        time.sleep(3)
        GPIO.output(led_green_gpio, False)
        GPIO.output(led_red_gpio, False)
        time.sleep(3)

def fan_control_thread():
    # Monitor temperature of M6e Nano and RPI, and start/stop fan based on set limits
    fan_on = False
    while True:
        temp_rpi = int(str(CPUTemperature())[44:46])
        if (temp_rpi > temp_high or temp_m6e > temp_high) and not fan_on:
            fan_on = True 
            GPIO.output(fan_gpio, True)
            my_print("ALERT High Temp - Fan started  RPI: " + str(temp_rpi) + "  M6e: " + str(temp_m6e))
        elif fan_on and (temp_rpi < temp_low and temp_m6e < temp_low):
            fan_on = False
            GPIO.output(fan_gpio, False)
            my_print("ALERT Normal Temp - Fan Stopped  RPI: " + str(temp_rpi) + "  M6e: " + str(temp_m6e))
        time.sleep(temp_check)

def tag_detected(epc,tagtime,rssi):
    # Save only consecutive unique tags. M6e doesn't eliminate duplicates during async. reads (also see gen2_session)
    # If bib numbers have been written to the RFID tags, extract that field directly and bypass the lookup function in api_transmit.py
    global epc_sav
    if epc_sav != epc:
        epc_sav = epc
        detections.write(str(epc)+','+str(rssi)+','+str(datetime.fromtimestamp(tagtime).strftime("%Y-%m-%d %H:%M:%S"))+'\n')
        
# Main program loop with error handling
if __name__ == '__main__':
    if (len(sys.argv) > 1 and sys.argv[1] == "silent"): debug = False
    try:
        # Initialization tasks
        init_start()
        # Launch fan control thread
        _thread.start_new_thread(fan_control_thread, ())
        # Endless loop to perform RFID tag reads triggered by the motion sensor
        active_rfid = False
        while True:
            if GPIO.input(pir_gpio) and not active_rfid:
                # Launch async RFID detections - Runs "tag_detected" function for each tag read
                active_rfid = True
                reader.start_reading(lambda tag: tag_detected(tag.epc, tag.timestamp, tag.rssi), on_time=250, off_time=0)
                # Turn on Red LED during async RFID detections
                GPIO.output(led_red_gpio, True)
                if debug: print("Motion sensor and async RFID detection activated - Red LED ON")
            elif not GPIO.input(pir_gpio) and active_rfid:
                # Wait set delay before returning M6e Nano to standby after motion sensor is no longer actived
                time.sleep(lag_wait)
                if not GPIO.input(pir_gpio):
                    reader.stop_reading()
                    detections.flush()
                    active_rfid = False
                    # Turn off Red LED when M6e Nano is in standby mode
                    GPIO.output(led_red_gpio, False)
                    if debug: print("Motion sensor and async RFID detection deactivated - Red LED OFF")
    except Exception as e:
        if 'reader' in globals(): 
            reader.stop_reading()
            reader.destroy()
        if 'detections' in globals(): 
            detections.flush()
            detections.close()
        my_print('CRITICAL ERROR Unknown Exception: ' + str(e))
        led_except()