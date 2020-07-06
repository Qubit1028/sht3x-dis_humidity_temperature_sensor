import sht3xdis

# Script to log sensor data to MySQL database

interval = 60       # Logging interval in secs
host = ''           # MySQL host
port = 3306         # MySQL port
db = ''             # MySQL database
table = ''          # MySQL table name


if __name__ == "__main__":
    sensor = sht3xdis.TempHumiditySensor(1, 0x44)
    sensor.start_logging_sql(host, port, db, table, interval)