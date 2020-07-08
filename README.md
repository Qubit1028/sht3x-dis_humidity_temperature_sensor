Python (>3.6) API for Sensirion humidity and temperature sensor SHT3x-DIS which has I2C communication

# Basic Usage
## Instantiate sensor object:
```python
import sht3xdis
sensor = sht3xdis.TempHumiditySensor(1, 0x44)
```

## Set sensor acquisition mode:
```python
sensor.set_mode("single-shot", acc="high", blocking=True)
```
Accuracy can be set to "low", "med" or "high", Blocking set to True waits for sensor reading to become available before proceeding

```python
sensor.set_mode("periodic", rate=4, acc="high")
```
Sampling rate on-board sensor can be 0.5, 1, 4 or 10 Hz

## Start sample acquisition on sensor:
```python
# Single-shot mode (non-blocking)
sensor.init_read()
while True:
  if sensor.isready():
    data = get_sample(degf=True)
    temp = data[0]
    rh = data[1]
  
# Single-shot mode (blocking)
sensor.init_read()
data = sensor.get_sample(degf=True)
  
# Periodic mode
sensor.init_read()
while True:
    data = sensor.get_sample(degf=True)   

```

# Data Logging
API includes logging features for logging temperature and humidity data to file or SQL database

## Log to file
```python
sensor.start_logging_file()
```
Add file path to `TempHumiditySensor.LOGGING_PATH`

## Log to MySQL
```python
sensor.start_logging_sql('192.168.1.1', 3306, "sampledatabase", "sampletable", 60)
```
Add MySQL credentials to `my.cnf` and set path `TempHumiditySensor.SQL_CREDS_PATH`

# Command-line script for exporting MySQL sensor data
Usage example: `sensor_data_export.py -f <path-to-outfile> -t <table> --maxsamples 1000`

