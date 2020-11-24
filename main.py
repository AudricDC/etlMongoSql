from src.lib_mongo_manager.mongo import MongoDB
from src.lib_pg_retriever.pg import Sql

if __name__ == "__main__":
    # object to interact with databases
    mongo_atlas = MongoDB(database="sample_restaurants", collection="restaurants", config_file="mongo_atlas.ini",
                          connection="atlas")
    mongo_local = MongoDB(database="sample_restaurants", collection="restaurants", config_file="mongo.ini",
                          connection="local")

    sql_manager = Sql(database="pg_sample_restaurants")

    # from mongoDB atlas, to pgsql
    mongo_df = mongo_atlas.getDf('grades', ['name', 'cuisine', ['address', 'building'], ['address', 'street'],
                                            ['address', 'zipcode']], nb_records=100)

    sql_manager.dfToSql(df=mongo_df, table_name="restaurants", if_exists="replace", index=False)

    # from pgsql, to local mongoDB
    pg_df = sql_manager.collectDf(table_name="public.restaurants")
    schema = {'first_level_records': ['name', 'cuisine', 'address'],
              'columns_to_merge_into_dict': {
                  'address': {'address.building': 'building', 'address.street': 'street',
                              'address.zipcode': 'zipcode'}},
              'columns_to_merge_into_list': {'grades': ['grade', 'score', 'date']}}
    restaurants_json = mongo_local.dfToJsonList(input_df=pg_df, schema=schema)
    mongo_local.insert(json_or_json_list=restaurants_json)
