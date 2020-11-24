# ETL between MongoDB and SQL databases.

One example of how to use lib_sql_manager and lib_mongo_manager 
to transfer data from one tech to another.


## Requirements

See requirements.txt


## Development setup

This script uses config files named database.ini for postgreSQL 
and mongo.ini, mongo_atlas.ini for mongo authentications.

database.ini looks like :
```
[postgresql]
user=user_name 
password=one_secret_password
query=SELECT * FROM {my_table}
```

mongo.ini and mongo_atlas.ini :

```
[MONGO_AUTHENTICATION]
USER = user_name
PWD = one_secret_password
AUTH_SOURCE = auth_source
; AUTH_SOURCE is only used for a local connection.
```

## Data set 

Atlas provides sample data you can load into your Atlas clusters.
To utilize the sample data provided by Atlas, you must create an Atlas cluster to load data into.
To get started with Atlas : https://docs.atlas.mongodb.com/getting-started/
Then load sample data : https://docs.atlas.mongodb.com/sample-data/

I created a cluster named "cluster0" (default name when following the step while getting started with Atlas) 
and loaded all the sample datasets. 
I now have several databases including : sample_restaurants, containing two collections : 
neighborhood and restaurants.
Now I will focus on restaurants collection.

The data must look like :

![Alt text](docs/initial_atlas_data.PNG?raw=true "Title")

## First install requirements.txt

Run in command line :

```
pip install requirements.txt
```

## Atlas mongo manager

I create a mongo_atlas.ini which contains my authentication informations to connect to my cluster.
Then I create an instance of MongoDB with python from lib_mongo_manager to connect to Atlas :

```python
from src.lib_mongo_manager.mongo import MongoDB
mongo_atlas = MongoDB(database="sample_restaurants", collection="restaurants", config_file="mongo_atlas.ini", connection="atlas")
```
Note : default cluster is cluster0, 
you have to specify a cluster to your MongoDB object if you picked up a different name.

 
## SQL manager
 
I created an empty database within postgreSQL using pgAdmin4 named pg_sample_restaurants.
Then I instantiate a Sql object to connect to this database :
 
  ```python
from src.lib_pg_retriever.pg import Sql
sql_manager = Sql(database="pg_sample_restaurants")
```

## Local mongo manager 

I do the same as in Atlas mongo manager,
but I choose a local connection to interact with my local mongo later.

```python
mongo_local = MongoDB(database="sample_restaurants", collection="restaurants", config_file="mongo.ini", connection="local")
```

## From Atlas to postgreSQL

I load the first 100 records from Atlas restaurants into a data frame, using my mongo_atlas object,
and then I load it into a postgreSQL table named "restaurants" using my sql_manager. 

```python
mongo_df = mongo_atlas.getDf('grades', ['name', 'cuisine', ['address', 'building'], ['address', 'street'], ['address', 'zipcode']], nb_records=100)

sql_manager.dfToSql(df=mongo_df, table_name="restaurants", if_exists="replace", index=False)
```

In postgreSQL, I now have table "restaurants" in my database "pg_sample_restaurants".

![Alt text](docs/pg_data.PNG?raw=true "Title")

## From postgreSQL to mongoDB

I load every sample from the table "restaurants" into a new dataframe using my sql_manager.
Then, I do the opposite transformation than the one from mongo_atlas.getDf (which Normalize semi-structured JSON data into a flat table),
to transform my data frame into a list of JSON documents, using method dfToJsonList from MongoDB object.
This transformation requires a specific schema to parse the data frame into a list of JSON.
Finally I insert this list into local mongoDB using insert method.

```python
pg_df = sql_manager.collectDf(table_name="public.restaurants")
schema = {'first_level_records': ['name', 'cuisine', 'address'],
          'columns_to_merge_into_dict': {
              'address': {'address.building': 'building', 'address.street': 'street',
                          'address.zipcode': 'zipcode'}},
          'columns_to_merge_into_list': {'grades': ['grade', 'score', 'date']}}
restaurants_json = mongo_local.dfToJsonList(input_df=pg_df, schema=schema)
mongo_local.insert(json_or_json_list=restaurants_json)
```

I find back my 100 records from Atlas, but now in a local mongoDB.

![Alt text](docs/mongo_data.PNG?raw=true "Title")