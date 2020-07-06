import smbus
import sys
from crccheck.crc import Crc
import time
from datetime import datetime
from MySQLdb import _mysql


# API for sht3x-dis Humidity and Temperature I2C sensor
# Reference datasheet:
# https://www.sensirion.com/fileadmin/user_upload/customers/sensirion/Dokumente/2_Humidity_Sensors/Datasheets/Sensirion_Humidity_Sensors_SHT3x_Datasheet_digital.pdf

class TempHumiditySensor:

    LOGGING_PATH = ''
    SQL_CREDS_PATH = ''
    IDX = 0

    # Sensor commands for performing single-shot measurement of temp & humidity
    # Format:  I2CAddr | W | Command MSB | Command LSB
    # Clock stretching can be enabled to hold the SCL line low until a measurement is ready
    # Disabling clock stretching allows sensor to return NACK to read requests until a measurement is ready
    # Measurement repeatability can be set to high, medium or low
    SINGLE_SHOT_CSOFF_HIGHR = [0x2C, 0x06]
    SINGLE_SHOT_CSOFF_MEDR = [0x2C, 0x0D]
    SINGLE_SHOT_CSOFF_LOWR = [0x2C, 0x10]
    SINGLE_SHOT_CSON_HIGHR = [0x24, 0x00]
    SINGLE_SHOT_CSON_MEDR = [0x24, 0x0B]
    SINGLE_SHOT_CSON_LOWR = [0x24, 0x16]

    # Sensor commands for performing periodic measurement of temp & humidity
    # Format: I2CAddr | W | Command MSB | Command LSB
    # Measurements per second can be set at 0.5, 1, 2, 4 or 10
    # Repeatability can be set at high, medium or low
    PERIODIC_05MPS_HIGHR = [0x20, 0x32]
    PERIODIC_05MPS_MEDR = [0x20, 0x24]
    PERIODIC_05MPS_LOWR = [0x20, 0x2F]
    PERIODIC_1MPS_HIGHR = [0x21, 0x30]
    PERIODIC_1MPS_MEDR = [0x21, 0x26]
    PERIODIC_1MPS_LOWR = [0x21, 0x2D]
    PERIODIC_2MPS_HIGHR = [0x22, 0x36]
    PERIODIC_2MPS_MEDR = [0x22, 0x20]
    PERIODIC_2MPS_LOWR = [0x22, 0x2B]
    PERIODIC_4MPS_HIGHR = [0x23, 0x34]
    PERIODIC_4MPS_MEDR = [0x23, 0x22]
    PERIODIC_4MPS_LOWR = [0x23, 0x29]
    PERIODIC_10MPS_HIGHR = [0x27, 0x37]
    PERIODIC_10MPS_MEDR = [0x27, 0x21]
    PERIODIC_10MPS_LOWR = [0x27, 0x2A]
    FETCH_DATA = [0xE0, 0x00]

    # ART (Accelerated Response Time)
    # Activating this feature sets the data acquisition rate of the sensor at 4Hz
    ART_ENABLE = [0x2B, 0x32]

    # Break command to stop periodic acquisition
    BREAK = [0x30, 0x93]

    # Reset command
    RESET = [0x30, 0xA2]

    # Heater enable for testing functionality
    HEATER_ENABLE = [0x30, 0x6D]
    HEATER_DISABLE = [0x30, 0x66]

    # Status register
    # Bit 15: Alert pending status - 0: none, 1: at least one pending alert
    # Bit 14: Reserved
    # Bit 13: Heater status - 0: OFF, 1: ON
    # Bit 12: Reserved
    # Bit 11: RH tracking alert - 0: none, 1: alert
    # Bit 10: T tracking alert - 0: none, 1: alert
    # Bit 9:5: Reserved
    # Bit 4: System reset detected - 0: none, 1: reset detected
    # Bit 3:2: Reserved
    # Bit 1: Command status - 0: last command executed successfully, 1: last command failed
    # Bit 0: Write data checksum status - 0: checksum of last write was correct, 1: checksum failed
    STATUS = [0xF3, 0x2D]

    # Clear status register
    CLEAR_STATUS = [0x30, 0x41]

    def __init__(self, i2cbus, addr):
        self.i2cbus = i2cbus
        self.addr = addr    #Default is 0x44 if pin 2 is logic low; 0x45 if pin 2 is logic high
        self.bus = smbus.SMBus(self.i2cbus)
        self.mode = "single-shot"
        self.rate = 1
        self.accuracy = "med"
        self.blocking = True
        self.Tready = False
        self.RHready = False
        self.T_degF = 0.0
        self.T_degC = 0.0
        self.RH = 0.0

    def set_mode(self, mode, rate=None, acc="med", blocking=False):
        if mode == "single-shot":
            self.mode = "single-shot"
            if rate is not None:
                print("INFO: Sample rate argument will be ignored in single-shot measurement mode")

            if acc != "med" and acc != "low" and acc != "high":
                print("WARNING: Invalid accuracy parameter supplied. Valid options are \"low\", \"med\" or \"high\"."
                      "Using default value of \"med\"")
                self.accuracy = "med"
            else:
                self.accuracy = acc

            self.blocking = blocking

        elif mode == "periodic":
            self.mode = "periodic"
            if rate is None:
                print("INFO: Sample rate argument not supplied; using default value of 1")
                self.rate = 1
            elif rate != 0.5 and rate != 1 and rate != 2 and rate != 4 and rate != 10:
                print("WARNING: Invalid sample rate argument supplied. Valid options are 0.5, 1, 2, 4 and 10. "
                      "Using default value of 1.")
                self.rate = 1
            else:
                self.rate = rate

            if acc != "med" and acc != "low" and acc != "high":
                print("WARNING: Invalid accuracy parameter supplied. Valid options are \"low\", \"med\" or \"high\"."
                      "Using default value of \"med\"")
                self.accuracy = "med"
            else:
                self.accuracy = acc

            if blocking is True:
                print("WARNING: Blocking is not available for periodic sampling mode.")
                self.blocking = False
        else:
            sys.exit("ERROR: Invalid mode parameter passed.  Valid options are \"single-shot\" or \"periodic\"")

    def init_read(self):

        if self.mode == "single-shot":
            if self.accuracy == "high":
                if self.blocking is True:
                    self.bus.write_byte_data(self.addr, TempHumiditySensor.SINGLE_SHOT_CSON_HIGHR[0], TempHumiditySensor.SINGLE_SHOT_CSON_HIGHR[1])
                    self.fetch_data()
                else:
                    self.bus.write_byte_data(self.addr, TempHumiditySensor.SINGLE_SHOT_CSOFF_HIGHR[0], TempHumiditySensor.SINGLE_SHOT_CSOFF_HIGHR[1])
            elif self.accuracy == "med":
                if self.blocking is True:
                    self.bus.write_byte_data(self.addr, TempHumiditySensor.SINGLE_SHOT_CSON_MEDR[0], TempHumiditySensor.SINGLE_SHOT_CSON_MEDR[1])
                    self.fetch_data()
                else:
                    self.bus.write_byte_data(self.addr, TempHumiditySensor.SINGLE_SHOT_CSOFF_MEDR[0], TempHumiditySensor.SINGLE_SHOT_CSOFF_MEDR[1])
            elif self.accuracy == "low":
                if self.blocking is True:
                    self.bus.write_byte_data(self.addr, TempHumiditySensor.SINGLE_SHOT_CSON_LOWR[0], TempHumiditySensor.SINGLE_SHOT_CSON_LOWR[1])
                    self.fetch_data()
                else:
                    self.bus.write_byte_data(self.addr, TempHumiditySensor.SINGLE_SHOT_CSOFF_LOWR[0], TempHumiditySensor.SINGLE_SHOT_CSOFF_LOWR[1])
        elif self.mode == "periodic":
            if self.accuracy == "high":
                if self.rate == 0.5:
                    self.bus.write_byte_data(self.addr, TempHumiditySensor.PERIODIC_05_MPS_HIGHR[0], TempHumiditySensor.PERIODIC_05MPS_HIGHR[1])
                elif self.rate == 1:
                    self.bus.write_byte_data(self.addr, TempHumiditySensor.PERIODIC_1MPS_HIGHR[0], TempHumiditySensor.PERIODIC_1MPS_HIGHR[1])
                elif self.rate == 2:
                    self.bus.write_byte_data(self.addr, TempHumiditySensor.PERIODIC_2MPS_HIGHR[0], TempHumiditySensor.PERIODIC_2MPS_HIGHR[1])
                elif self.rate == 4:
                    self.bus.write_byte_data(self.addr, TempHumiditySensor.PERIODIC_4MPS_HIGHR[0], TempHumiditySensor.PERIODIC_4MPS_HIGHR[1])
                elif self.rate == 10:
                    self.bus.write_byte_data(self.addr, TempHumiditySensor.PERIODIC_10MPS_HIGHR[0], TempHumiditySensor.PERIODIC_10MPS_HIGHR[1])
            elif self.accuracy == "med":
                if self.rate == 0.5:
                    self.bus.write_byte_data(self.addr, TempHumiditySensor.PERIODIC_05MPS_MEDR[0], TempHumiditySensor.PERIODIC_05MPS_MEDR[1])
                elif self.rate == 1:
                    self.bus.write_byte_data(self.addr, TempHumiditySensor.PERIODIC_1MPS_MEDR[0], TempHumiditySensor.PERIODIC_1MPS_MEDR[1])
                elif self.rate == 2:
                    self.bus.write_byte_data(self.addr, TempHumiditySensor.PERIODIC_2MPS_MEDR[0], TempHumiditySensor.PERIODIC_2MPS_MEDR[1])
                elif self.rate == 4:
                    self.bus.write_byte_data(self.addr, TempHumiditySensor.PERIODIC_4MPS_MEDR[0], TempHumiditySensor.PERIODIC_4MPS_MEDR[1])
                elif self.rate == 10:
                    self.bus.write_byte_data(self.addr, TempHumiditySensor.PERIODIC_10MPS_MEDR[0], TempHumiditySensor.PERIODIC_10MPS_MEDR[1])
            elif self.accuracy == "low":
                if self.rate == 0.5:
                    self.bus.write_byte_data(self.addr, TempHumiditySensor.PERIODIC_05MPS_LOWR[0], TempHumiditySensor.PERIODIC_05MPS_LOWR[1])
                elif self.rate == 1:
                    self.bus.write_byte_data(self.addr, TempHumiditySensor.PERIODIC_1MPS_LOWR[0], TempHumiditySensor.PERIODIC_1MPS_LOWR[1])
                elif self.rate == 2:
                    self.bus.write_byte_data(self.addr, TempHumiditySensor.PERIODIC_2MPS_LOWR[0], TempHumiditySensor.PERIODIC_2MPS_LOWR[1])
                elif self.rate == 4:
                    self.bus.write_byte_data(self.addr, TempHumiditySensor.PERIODIC_4MPS_LOWR[0], TempHumiditySensor.PERIODIC_4MPS_LOWR[1])
                elif self.rate == 10:
                    self.bus.write_byte_data(self.addr, TempHumiditySensor.PERIODIC_10MPS_LOWR[0], TempHumiditySensor.PERIODIC_10MPS_LOWR[1])

    def stop_read(self):
        if self.mode == "periodic":
            self.bus.write_byte_data(self.addr, TempHumiditySensor.BREAK[0], TempHumiditySensor.BREAK[1])
            time.sleep(0.05)
            print("Break command sent to sensor")

    def fetch_data(self):
        time.sleep(0.05)
        if self.mode == "single-shot":
            data = self.bus.read_i2c_block_data(self.addr, 0, 6)

        elif self.mode == "periodic":
            self.bus.write_byte_data(self.addr, TempHumiditySensor.FETCH_DATA[0], TempHumiditySensor.FETCH_DATA[1])
            time.sleep(0.1)
            data = self.bus.read_i2c_block_data(self.addr, 0, 6)

        ret = self.process_data(data)

        self.Tready = ret[0]
        self.RHready = ret[1]

    def isready(self):
        if self.Tready is True and self.RHready is True:
            return True
        else:
            return False

    def get_sample(self, degf=True):
        ret = []
        if self.Tready is True and self.RHready is True:
            self.Tready = False
            self.RHready = False
            if degf is True:
                ret.append(self.T_degF)
            else:
                ret.append(self.T_degC)
            ret.append(self.RH)
        else:
            self.fetch_data()
            if self.Tready is True and self.RHready is True:
                self.Tready = False
                self.RHready = False
                if degf is True:
                    ret.append(self.T_degF)
                else:
                    ret.append(self.T_degC)
                ret.append(self.RH)
            else:
                ret.append(None)
                ret.append(None)

        return ret

    def get_temp(self, degf=True):
        if self.Tready is True:
            self.Tready = False

        if degf is True:
            return self.T_degF
        else:
            return self.T_degC

    def get_rh(self):
        if self.RHready is True:
            self.RHready = False
        return self.RH

    def toggle_heater(self, state):
        if state is True:
            self.bus.write_byte_data(self.addr, TempHumiditySensor.HEATER_ENABLE[0], TempHumiditySensor.HEATER_ENABLE[1])
        else:
            self.bus.write_byte_data(self.addr, TempHumiditySensor.HEATER_DISABLE[0], TempHumiditySensor.HEATER_DISABLE[1])

    def process_data(self, data):

        temp_chk = TempHumiditySensor.crc_eval([data[0], data[1]], data[2])
        rh_chk = TempHumiditySensor.crc_eval([data[3], data[4]], data[5])

        if temp_chk is False:
            print("WARNING: Checksum failed on temperature value reported by sensor!")
            ret1 = False
        else:
            s_t = (data[0] << 8) | data[1]
            self.T_degF = round(-49 + 315.0 * (s_t / (2 ** 16 - 1)), 3)
            self.T_degC = round(-45 + 175.0 * (s_t / (2 ** 16 - 1)), 3)
            ret1 = True

        if rh_chk is False:
            print("WARNING: Checksum failed on humidity value reported by sensor!")
            ret2 = False
        else:
            s_rh = (data[3] << 8) | data[4]
            self.RH = round(100.0*(s_rh/(2**16-1)), 3)
            ret2 = True

        ret = [ret1, ret2]
        return ret

    @staticmethod
    def crc_eval(data, _crc):
        chksum = Crc(8, 0x31, initvalue=0xFF, reflect_input=False, xor_output=0x00)
        chksum.process(data)
        chk = chksum.final()

        if chk == _crc:
            return True
        else:
            return False

    def reset(self):
        self.bus.write_byte_data(self.addr, TempHumiditySensor.RESET[0], TempHumiditySensor.RESET[1])
        print("Reset command sent to sensor")

    def alert_status(self):
        status_byte = self.get_status_byte()
        if status_byte != 0xFFFF:
            status_bit = status_byte & 0x8000
            status_bit >>= 15
            if status_bit == 1:
                print('Alert pending!')
                return True
            else:
                return False
        else:
            print("WARNING: Checksum failed on status register")
            return False

    def get_alert(self):
        ret = ["null"]*3

        status_byte = self.get_status_byte()
        if status_byte != 0xFFFF:
            talert = status_byte & 0x200
            talert >>= 10
            rhalert = status_byte & 0x400
            rhalert >>= 11
            resetalert = status_byte & 0x08
            resetalert >>= 4

            if talert == 1:
                print('Temperature tracking alert!')
                ret[0] = "temp_alert"
            if rhalert == 1:
                print('Humidity tracking alert!')
                ret[1] = "rh_alert"
            if resetalert == 1:
                print('System reset detected')
                ret[2] = "reset_alert"

            self.bus.write_byte_data(self.addr, TempHumiditySensor.CLEAR_STATUS[0], TempHumiditySensor.CLEAR_STATUS[1])
            time.sleep(0.05)
        else:
            print("WARNING: Checksum failed on status register")

        return ret

    def command_status(self):
        status_byte = self.get_status_byte()
        if status_byte != 0xFFFF:
            cmd = status_byte & 0x02
            cmd >>= 1
            if cmd == 0:
                print('Last command to sensor completed successfully')
                return True
            else:
                print('Last command to sensor did not complete')
                return False
        else:
            print("WARNING: Checksum failed on status register")
            return False

    def chksum_status(self):
        status_byte = self.get_status_byte()
        if status_byte != 0xFFFF:
            chk = status_byte & 0x01
            if chk == 0:
                print('Write data checksum was correct')
                return True
            else:
                print('Write data checksum failed')
                return False
        else:
            print("WARNING: Checksum failed on status register")
            return False

    def get_heater_status(self):
        status_byte = self.get_status_byte()
        if status_byte != 0xFFFF:
            heater = status_byte & 0x2000
            heater >>= 13
            if heater == 1:
                print('Heater is ON')
                return True
            else:
                print('Heater is OFF')
                return False
        else:
            print("WARNING: Checksum failed on status register")
            return False

    def get_status_byte(self):
        self.bus.write_byte_data(self.addr, TempHumiditySensor.STATUS[0], TempHumiditySensor.STATUS[1])
        time.sleep(0.05)
        data = self.bus.read_i2c_block_data(self.addr, 0, 3)
        if TempHumiditySensor.crc_eval([data[0], data[1]], data[2]) is True:
            status_byte = data[0] << 8 | data[1]
        else:
            status_byte = 0xFFFF
        return status_byte

    def start_logging_file(self):
        if self.mode != "periodic":
            self.set_mode("periodic", rate=1, acc="med")

        print("Logging to file started!")
        if TempHumiditySensor.IDX == 0:
            self.init_read()
            TempHumiditySensor.IDX += 1
        while True:
            sample = self.get_sample()
            temp = sample[0]
            rh = sample[1]
            dtime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            f = open(TempHumiditySensor.LOGGING_PATH, "a")
            f.write(dtime + ',' + str(temp) + ',' + str(rh) + '\n')
            f.close()

    def start_logging_sql(self, host, port, db, tb, log_interval):
        db = _mysql.connect(host=host, port=port, db=db, table=tb, read_default_file=TempHumiditySensor.SQL_CREDS_PATH)

        print("Logging to SQL database started!")
        if self.mode != "periodic":
            self.set_mode("periodic", rate=1, acc="med")

        if TempHumiditySensor.IDX == 0:
            self.init_read()
            TempHumiditySensor.IDX += 1
        while True:
            sample = self.get_sample()
            temp = sample[0]
            rh = sample[1]
            dtime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            f = open(TempHumiditySensor.LOGGING_PATH, "w")
            f.write(dtime + ',' + str(temp) + ',' + str(rh) + '\n')
            f.close()
            query_str = "INSERT INTO " + tb + " (time, temp, rh) VALUES (" + "'" + dtime + "'" + "," + str(temp) + "," + str(rh) + ")"
            db.query(query_str)
            time.sleep(log_interval)


