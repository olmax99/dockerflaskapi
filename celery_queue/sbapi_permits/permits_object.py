import os

import pandas as pd

from botocore.exceptions import ClientError
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)

RUN_MODE = os.getenv('RUN_MODE', 'DEVELOPMENT')


class Error(Exception):
    """Base class for exceptions in this module"""
    pass


class AthenaInitializationException(Error):
    """Exception raised for errors in SyncBQ"""
    def __init__(self, message, errors=None):
        super(AthenaInitializationException, self).__init__(str(self.__class__.__name__) + ': ' + message)
        self.errors = errors

    def __repr__(self):
        return "AthenaInitializationException"


class PermitsAthena(object):
    """
    Container for all resources and activities related for processing
    permits data from the serverlessbaseapi project.

    """
    def __init__(self,
                 current_uuid,
                 partitiontime=None,
                 s3client=None,
                 base_bucket=None,
                 base_data_store=None,
                 permits_database=None,
                 permits_table=None,
                 base_region=None,
                 base_data_dir='/queue/data/'
                 ):
        if RUN_MODE == 'DEVELOPMENT':
            base_bucket = 'flaskapi-dev-rexray-data'
            base_data_store = 'flaskapi-dev-datastore-eu-central-1/permits/parquet'
            permits_database = 'dev_flaskapi_01'
            permits_table = 'dev_permits_01'
            base_region = 'us-east-1'
        else:
            base_bucket = 'flaskapi-staging-rexray-data-vol'
            base_data_store = 'flaskapi-staging-datastore-eu-central-1/permits/parquet'
            permits_database = 'staging_flaskapi_01'
            permits_table = 'staging_permits_01'
            base_region = 'eu-central-1'

        self.job_uuid = current_uuid
        self._partitiontime = partitiontime
        self.s3_client = s3client

        self.base_bucket = base_bucket
        self.base_data_dir = base_data_dir
        self.base_data_store = base_data_store
        self.base_region = base_region

        self.permits_database = permits_database
        self.permits_table = permits_table

    def __repr__(self):
        # TODO: Add Athena credentials, i.e. service name, table id
        return f"aws.Athena.Client: 'uuid.{self.job_uuid}'"

    def permits_to_parquet(self, source_iterable, parquet_file, chunks=False, log=False):
        """
        Saving the permits data locally (S3 mount) as parquet
        :param source_iterable: <generator object HttpHook>
        :param parquet_file: local parquet output file
        :param chunks: NOT IMPLEMENTED YET
        :return: parquet file containing report data
        """
        # PARQUET - Only in combination with S3 !!
        if not chunks:
            # ----------- 1. Run column checks--------------------------------
            # TODO: Prepare Athena Table for column check
            # checked_payload, missing_cols = self.pandas_athena_column_check(source_iterable)

            # json_data = list(checked_payload)
            json_data = list(source_iterable)[0]
            pandas_df = pd.DataFrame(json_data).reset_index().drop(columns=['index'])

            # ----------- 2. Fill missing mandatory columns with NaN values---
            # TODO: Requires Athena column check - Remove enum for no chunks
            # for enum, chunk in enumerate(checked_payload):
            #     for t in missing_cols:
            #         if t[0] == enum:
            #             for new_col in t[1]:
            #                 pandas_df[new_col] = pd.np.nan

            # ----------- 3. Map from json to pandas dtypes-------------------
            mapped_pandas_df = self.map_df_to_parquet(pandas_df)

            # ----------- 4. Save Parquet locally-----------------------------
            # TODO: Enable/test with compression snappy
            if log:
                logger.info(f"Writing DataFrame to {os.path.join(self.base_data_dir, f'{parquet_file}.parquet')}")
            mapped_pandas_df.to_parquet(os.path.join(self.base_data_dir, f"{parquet_file}.parquet"), engine='pyarrow', compression=None)

        else:
            for _i, chunk in enumerate(source_iterable):
                # checked_chunk, missing_cols = self.pandas_athena_column_check(chunk)
                # json_data = list(checked_chunk)
                json_data = chunk
                chunk_df = pd.DataFrame(json_data).reset_index().drop(columns=['index'])
                # for enum, chunk in enumerate(checked_df):
                #     for t in missing_cols:
                #         if t[0] == enum:
                #             for new_col in t[1]:
                #                 chunk_df[new_col] = pd.np.nan
                mapped_pandas_df = self.map_df_to_parquet(chunk_df)
                mapped_pandas_df.to_parquet(f"{parquet_file}_{_i:03}.parquet", engine='pyarrow', compression=None)

    def map_df_to_parquet(self, df_in):
        df_map = df_in.copy(deep=True)
        df_map.rename(columns={'estimated_cost': 'permit_est_cost',
                               'expiration_date': 'permit_expiration_date',
                               'file_date': 'permit_file_date',
                               'description': 'permit_description',
                               'proposed_use': 'estate_proposed_use',
                               'record_id': 'permit_record_id',
                               'address': 'estate_address',
                               'existing_use': 'estate_existing_use',
                               'status': 'application_status'},
                      inplace=True)
        # Type mapping
        df_map['application_number'] = df_map['application_number'].astype('str', errors='ignore').replace('nan', pd.np.nan)
        df_map['permit_record_id'] = pd.to_numeric(df_map['permit_record_id'], downcast='integer', errors='coerce')
        df_map['estate_address'] = df_map['estate_address'].astype('str', errors='ignore').replace('nan', pd.np.nan)
        df_map['permit_description'] = df_map['permit_description'].astype('str', errors='raise').replace('nan', pd.np.nan)
        df_map['permit_est_cost'] = pd.to_numeric(df_map['permit_est_cost'], downcast='float', errors='coerce')
        df_map['permit_expiration_date'] = pd.to_datetime(df_map['permit_expiration_date'], errors='coerce').dt.date
        df_map['permit_file_date'] = pd.to_datetime(df_map['permit_file_date'], errors='coerce').dt.date
        df_map['revised_cost'] = pd.to_numeric(df_map['revised_cost'], downcast='float', errors='coerce')
        df_map['application_status'] = df_map['application_status'].astype('str', errors='ignore').replace('nan', pd.np.nan)
        df_map['status_date'] = df_map['status_date'].astype('str', errors='ignore').replace('nan', pd.np.nan)
        df_map['estate_existing_use'] = df_map['estate_existing_use'].astype('str', errors='ignore').replace('nan', pd.np.nan)
        df_map['estate_proposed_use'] = df_map['estate_proposed_use'].astype('str', errors='ignore').replace('nan', pd.np.nan)
        # Keep order for athena
        df_map = df_map[['application_number', 'permit_record_id', 'estate_address',
                         'permit_description', 'permit_est_cost', 'permit_expiration_date', 'permit_file_date',
                         'revised_cost', 'application_status', 'status_date', 'estate_existing_use',
                         'estate_proposed_use']]

        return df_map

    def confirm_key_exist(self, log=False):
        try:
            object_summary = self.s3_client.head_object(Bucket=self.base_bucket,
                                                        Key=f'data/{self.job_uuid}.parquet')
            if log:
                logger.info(f"PermitsObject: response {object_summary}")
        except ClientError as e:
            if e.response['Error']['Code'] == "404":
                if log:
                    logger.info("PermitsObject: Object not found.")
        else:
            return object_summary
