import os
import time
import logging
import pandas as pd
from configparser import ConfigParser

import psycopg2
from sqlalchemy import create_engine


class Sql(object):
    def __init__(self, database, host="localhost", port=5432, filename="database.ini", section="postgresql"):
        try:
            config = ConfigParser()
            file_path = os.path.realpath(__file__)
            conf_path = os.path.join(os.path.dirname(file_path), filename)
            config.read(conf_path)
        except Exception as e:
            logging.error('Error parsing config file -> ' + str(e))
            config = ConfigParser()
            project_path = os.getcwd()
            module_path = filename
            config.read(os.path.join(project_path, module_path))

        # get connection parameters
        self.host = host
        self.port = port
        # get authentication parameters
        self.__user = config[section]['user']
        self.__pwd = config[section]['password']
        # get db and query
        self.db = database
        self.query = config[section]['query']

    def collectWithPsycopg2(self, table_name):
        """
        Query data from SQL using psycopg2.
        :param table_name: sql table to read.
        :return:
        """
        conn = None
        try:
            logging.info("Connecting to pgSql with psycopg2...")
            conn = psycopg2.connect(dbname=self.db, user=self.__user, password=self.__pwd, host=self.host, port=self.port)
            cur = conn.cursor()
            cur.execute(self.query.format(my_table=table_name))
            rows = cur.fetchall()
            cur.close()
            return rows
        except (Exception, psycopg2.DatabaseError) as error:
            logging.error(error)
        finally:
            if conn is not None:
                conn.close()

    def _initConnection(self):
        """
        Initialize connection to sql using create_engine.
        :return:
        """
        engine_string = "postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}".format(
            user=self.__user,
            password=self.__pwd,
            host=self.host,
            port=self.port,
            database=self.db)

        # create sqlalchemy engine
        self.engine = create_engine(engine_string)

    def collectDf(self, table_name):
        """
        Function that collect data from sql using pd.read_sql_query and create_engine.
        :param table_name: sql table to read.
        :return: a dataframe containing data from your request.
        """
        k = 0
        while True:
            try:
                logging.info('Trying to connect to db...')
                self._initConnection()
                logging.info('Trying to query data...')
                query = self.query.format(my_table=table_name)
                return pd.read_sql_query(query, self.engine)  # see also pd.read_sql_table
            except Exception as e:
                logging.error('Error connecting/querying data -> ' + str(e))
                time.sleep(120)
                k += 1
                if k == 10:
                    logging.error('Error querying data, return an empty data frame -> ' + str(e))
                    return pd.DataFrame()

    def dfToSql(self, df, table_name, if_exists, index):
        """
        Function that writes a df to sql.
        :param df: df to write.
        :param table_name: name of the sql table you want to write.
        :param if_exists: see https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.to_sql.html
        :param index: see above link.
        :return:
        """
        k = 0
        while True:
            try:
                logging.info('Trying to connect to db...')
                self._initConnection()
                logging.info('Trying to write df...')
                df.to_sql(table_name, self.engine, if_exists=if_exists, index=index)
                break
            except Exception as e:
                logging.error('Error writing df -> ' + str(e))
                time.sleep(120)
                k += 1
                if k == 10:
                    logging.error('Error writing df to sql after {} attempts -> '.format(k) + str(e))


if __name__ == "__main__":
    pg = Sql(database="pg_sample_restaurants")
    data = pg.collectWithPsycopg2(table_name="public.restaurants")
    df = pg.collectDf(table_name="public.restaurants")
    logging.info('Success')
