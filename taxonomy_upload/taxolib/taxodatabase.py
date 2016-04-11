
import psycopg2 as ppg2
from ConfigParser import RawConfigParser
from taxoconfig import ConfigError


def getDBCursor(conffile):
    # Read the database connection settings from the configuration file.
    cp = RawConfigParser()
    res = cp.read(conffile)
    if len(res) == 0:
        raise ConfigError('The database configuration file ' + conffile + ' could not be read.')

    dbhost = cp.get('database', 'host')
    dbport = cp.getint('database', 'port')
    dbuser = cp.get('database', 'user')
    dbpw = cp.get('database', 'pw')
    dbname = cp.get('database', 'dbname')
    dbschema = cp.get('database', 'schema')

    # Set up the database connection, get a connection cursor, and set the default schema.
    conn = ppg2.connect(host=dbhost, port=dbport, user=dbuser, password=dbpw, database=dbname)
    pgcur = conn.cursor()
    pgcur.execute('SET search_path TO ' + dbschema)

    return pgcur

