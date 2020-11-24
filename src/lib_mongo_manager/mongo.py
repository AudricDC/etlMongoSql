import os
import logging
from configparser import ConfigParser

import json
from pandas import json_normalize

from pymongo import MongoClient


class MongoDB(object):
    def __init__(self, database, collection, connection, config_file, host="localhost", port=27017, cluster="cluster0"):
        try:
            config = ConfigParser()
            file_path = os.path.realpath(__file__)
            conf_path = os.path.join(os.path.dirname(file_path), config_file)
            config.read(conf_path)
        except:
            config = ConfigParser()
            project_path = os.getcwd()
            module_path = config_file
            config.read(os.path.join(project_path, module_path))
        # get authentication parameters
        self.__username = config['MONGO_AUTHENTICATION']['USER']
        self.__pwd = config['MONGO_AUTHENTICATION']['PWD']
        self.__auth_source = config['MONGO_AUTHENTICATION']['AUTH_SOURCE']
        # get connection parameters
        self.host = host
        self.port = int(port)
        self.cluster = cluster  # only used for an atlas connection !
        # get connection type
        self.connection = connection
        # connection to client
        if self.connection == "local":
            self.client = self._localConnection()
        elif self.connection == "atlas":
            self.client = self._atlasConnection(database=database)
        else:
            raise ValueError(f"'{self.connection}' is not valid for connection - choose between 'local' and 'atlas'")
        # access to db and collection
        self.db = self.client[database]
        self.collection = self.db[collection]

    def _localConnection(self):
        """
        Initialize a local connection. Requires authsource.
        :return: MongoClient object.
        """
        return MongoClient(username=self.__username, password=self.__pwd, host=self.host, port=self.port,
                           authSource=self.__auth_source)

    def _atlasConnection(self, database):
        """
        Initalize a remote connection mongodb+srv. Useful for an atlas connection. Need the database name.
        :param database: database name.
        :return: MongoClient object.
        """
        return MongoClient(
            'mongodb+srv://{username}:{pwd}@{cluster}.qlwam.mongodb.net/{dbname}>?retryWrites=true&w=majority'.format(
                username=self.__username, pwd=self.__pwd, cluster=self.cluster, dbname=database))

    def query(self, query=None, projection=None, nb_records=None):
        """
        Method to query data from mongoDB.
        See : https://docs.mongodb.com/manual/reference/method/db.collection.find/
        :param query: mongo query (see doc)
        :param projection: mongo projection (see doc)
        :param nb_records: nb of records to collect. Will select the first n records of the database.
        :return: list of json documents.
        """
        if query is None:
            query = {}
        if nb_records is None:
            return list(self.collection.find(query, projection))
        else:
            return list(self.collection.find(query, projection).limit(nb_records))

    def getSortedRecords(self, key_or_list, direction, query=None, projection=None, nb_records=None):
        """
        Same as query, but sort documents according to key_or_list.
        See : https://docs.mongodb.com/manual/reference/method/cursor.sort/
        :param query: mongo query.
        :param projection: mongo projection.
        :param nb_records: nb of records to collect. Will select the first n records of the database.
        :return: list of json documents.
        """
        if query is None:
            query = {}
        if nb_records is None:
            return list(
                self.collection.find(query, projection).sort(key_or_list=key_or_list, direction=direction))
        else:
            return list(
                self.collection.find(query, projection).sort(key_or_list=key_or_list, direction=direction).limit(
                    nb_records))

    def getDf(self, *schemas, query=None, projection=None, nb_records=None):
        """
        Normalize semi-structured JSON data into a flat table
        See : https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.json_normalize.html
        :param schemas: list of arguments. See doc for examples.
        :param query: mongo query.
        :param projection: mongo projection.
        :param nb_records: nb of records to collect. Will select the first n records of the database.
        :return: a dataframe (flatted).
        """
        if query is None:
            query = {}
        if nb_records is None:
            data = list(self.collection.find(query, projection))
        else:
            data = list(self.collection.find(query, projection).limit(nb_records))
        return json_normalize(data, *schemas)

    def _buildDict(self, x, items):
        mydict = {}
        list(map(lambda y: mydict.update({y[1]: x[y[0]]}) or mydict, items))
        return mydict

    def dfToJsonList(self, input_df, schema):
        """
        Transform a dataframe into a list of Json.
        :param input_df: dataframe to load into json records.
        :param schema: dict containing the structure of the desired documents.
        :return: a list of Json (dict)
        """
        df = input_df.copy()
        for key, records in schema['columns_to_merge_into_dict'].items():
            df[key] = df.apply(
                lambda x: json.dumps(self._buildDict(x=x, items=records.items())), axis=1)
        for key, record_list in schema['columns_to_merge_into_list'].items():
            df = df.groupby(by=schema['first_level_records'], as_index=False).apply(
                lambda x: x[record_list].to_json(orient='records')).rename(columns={None: key})
        for record in list(schema['columns_to_merge_into_dict'].keys()) + list(
                schema['columns_to_merge_into_list'].keys()):
            df[record] = df.apply(lambda x: json.loads(x[record]), axis=1)
        dict_list = df.to_dict('records')
        return dict_list

    def update(self, query, update=None, upsert=False, multi=False):
        """
        Modifies an existing document or documents in a collection, that match query.
        See : https://docs.mongodb.com/manual/reference/method/db.collection.update/
        :param query: mongo query.
        :param update: modifications to apply.
        :param upsert: If set to true, creates a new document when no document matches the query criteria
        :param multi: If set to true, updates multiple documents that meet the query criteria.
        :return: None.
        """
        self.collection.update(spec=query, document=update, upsert=upsert, multi=multi)

    def insert(self, json_or_json_list):
        """
        Inserts a document or documents into a collection.
        See : https://docs.mongodb.com/manual/reference/method/db.collection.insert/
        :param json_or_json_list: documents to be inserted.
        :return: None.
        """
        self.collection.insert(doc_or_docs=json_or_json_list)


if __name__ == "__main__":
    ascMongoAtlas = MongoDB(database="sample_restaurants", collection="restaurants", config_file=r"mongo_atlas.ini",
                            connection='atlas')
    restaurants_df = ascMongoAtlas.getDf('grades', ['name', 'cuisine', ['address', 'building'], ['address', 'street'],
                                                    ['address', 'zipcode']], nb_records=50)
    schema = {
        'first_level_records': ['name', 'cuisine', 'address'],
        # list of first level records that are not a list of second level records
        'columns_to_merge_into_dict': {
            'address': {'address.building': 'building', 'address.street': 'street', 'address.zipcode': 'zipcode'}},
        # pandas columns to merge into a first level dictionary in mongo
        # {first_level_key_names : {pandas_columns_to_merde: second_level_key_names}}
        'columns_to_merge_into_list': {'grades': ['grade', 'score', 'date']}
        # pandas columns to merge into a first level list of records in mongo
        # {first_level_key_names : [pandas_columns_to_be_merged]}
    }
    json_list = ascMongoAtlas.dfToJsonList(input_df=restaurants_df, schema=schema)
    logging.info('Success')
