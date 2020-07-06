from MySQLdb import _mysql
import sys
import argparse

# Command line script that can be used to export sensor data to file

host = ''
port = 3306
dbase = ''
user = ''
passwd = ''


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--file", help="Output filename")
    parser.add_argument("-t", "--table", help="Database table to select")
    parser.add_argument("--maxsamples", help="Maximum number of samples to fetch", type=int, default=1000)

    args = parser.parse_args()

    fpath = args.file
    samples = args.maxsamples
    table = args.table

    if fpath is None or table is None:
        print("Must provide file path [-f] and data table [-t]")
        sys.exit()

    db = _mysql.connect(host=host, port=3306, user=user, passwd=passwd, db=dbase)
    query_str = "SELECT * FROM " + table + " ORDER BY time DESC LIMIT " + str(samples)
    db.query(query_str)
    res = db.store_result()
    data = res.fetch_row(maxrows=0)

    with open(fpath, 'w') as file:
        for _tuple in data:
            file.write(_tuple[0].decode('utf-8'))
            file.write(",")
            file.write(_tuple[1].decode('utf-8'))
            file.write(",")
            file.write(_tuple[2].decode('utf-8'))
            file.write('\n')

    print("Data export complete!")

if __name__ == "__main__":
    main(sys.argv[1:])


