# Trail_RFID
A battery-powered high-speed RFID reader controlled by a Raspberry PI 2W for off-grid use

Low-cost RFID-based system providing for better tracking of participants to trail running, like Ultra-Trail Harricana (UTHC), or other events. Ideally suited where significant sections of the track are located in areas outside the reach of cellular networks.

•	Raspberry PI 2W quad-core single-board computer, executing three concurrent Python scripts,
on-demand cooling fan to keep components within normal operating temperature range,
infrared sensor to reduce power consumption from 5.6 Wh to 0.7 Wh when no runners are in the detection field.

•	JADAK M6E Nano RFID decoder with a read rate up to 150 tags/sec,
can read RFID tags up to 20 ft away with external antenna,
design compatible with newly released M7E Hecto.

Transmits passing times to a 3rd party race management software via customizable API across any Wifi access point (Starlink, mobile hotspot, etc.). Field proven in four events, with a total of 1,000+ participants using Race Result 12.

A previous unpublished version of this design transmitted passing times across low-bandwidth IridiumGo! satellite hotspots. That version requires an ETL (Extract-Transform-Load) Python module running on MS-Azure VM or other. 

The RFID reader delivers up to 65 hours of continuous battery operation, at a 10% active scan mode and using a 96 Wh LiFePO4 battery. Power requirements for Internet access (Starlink, hotspot, IridiumGo!, etc) are not included.

![Trail RFID Components Diagram v3 1](https://github.com/user-attachments/assets/d0814c55-18b5-43c0-89cc-b65fa65e314a)
