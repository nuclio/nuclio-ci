import libs.nuclio_sdk.test
import os
import libs.common.psycopg2_functions

class TestCase(libs.nuclio_sdk.test.TestCase):

    def setUp(self):
        super().setUp()

        os.environ['PGINFO'] = 'postgres:pass@172.17.0.1:5432'
        setattr(self._platform.context.user_data, 'conn', libs.common.psycopg2_functions.get_psycopg2_connection())

        # create a client for the test
        # self._cosmosdb_client = common.cosmosdb.create_client()

        # create a client for the test
        # setattr(self._platform.context.user_data, 'client', self._cosmosdb_client)

        # clear all collections
        # common.cosmosdb.ensure_collections(self._platform.context, clear=True)
