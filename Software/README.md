This system is designed around a battery-powered Raspberry PI Zero 2W single-board computer paired with a ThinkMagic M6e Nano RFID reader
(capable of 150 reads per second). It detects multiple, simultaneous GEN2 RFID tags affixed to participant bibs, when passing across off-grid
checkpoints on a trail-running event. Checkpoint times are then transmitted by the Raspberry PI to a 3rd party event timing software (via API)
across Starlink, mobile hotspot or any other type of Wifi connection. The previous unpublished version supports low-speed IridiumGo
satellite technology via FTP file transfer and ETL (Extract, Transform, Load) processing.


| Identification        | Description                                                                                       |
| --------------------- | --------------------------------------------------------------------------------------------------|
| scan_bibs.py          | Reads RFID tags and stores checkpoint passing times in a local CSV file                           |
| detections.csv        | CSV file containing all tags & timestamps detected by scan_bibs.py (also read by api_transmit.py) |
|                       |                                                                                                   |
| api_transmit.py       | Periodic transmissions of checkpoint times to the race timing software via API                    |
| api_transmit.cfg      | Settings used by api_transmit.py                                                                  |
| detections.db         | SQLite database to process/track API calls to the 3rd party event timing management software      |
| bib_lookup.csv        | Lookup file to match bib numbers with EPC codes (when bib numbers are not present on RFID tags)   |
| last_read.csv         | Pointer to the most recent line processed from detections.csv                                      |
|                       |                                                                                                   |
| http_server.py        | HTTP script to display Raspberry PI status or initiate basic commands through a web browser       |
