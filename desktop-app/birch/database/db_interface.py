"""
Couchdb based result logger
"""

import logging
import datetime
from datetime import timezone
import zipfile
import tempfile
import os
from pubsub import pub


class DBInterface(object):
    DB_ENABLE = True
    event_logger = logging.getLogger("event_logger")
    """
    Abstract database interface
    """

    def __init__(self, host="127.0.0.1", port=5984, username="production", password="", product=""):
        self.enabled = False
        self.url = "http://%s:%s@%s:%d/" % (username, password, host, int(port))
        self.server = None
        self.database = None
        self.product = product

    def close(self):
        """
        Remove single instance of DBInterface
        """
        self.database = None

    def set_database(self, database_name):
        """
        Set the name of the active result database
        """
        self.database = database_name
        # TODO - does not check for existence

    def enable(self):
        self.enabled = True

    def disable(self):
        self.enabled = False

    def _save(self, doc):
        pass

    def log_device(self, device=None):
        return True

    def log_result(self, result):
        return True

    def db_export(self, config, fname):
        return True

    @staticmethod
    def create(db_type, *args, **kwargs):
        """
        Instantiate an instance of the named testcase by looking for a matching name in the
        subclasses of TestCase
        """
        if db_type is None:
            return DBInterface(*args, **kwargs)

        for cls in DBInterface.__subclasses__():
            if cls.__name__.lower() == (db_type + "Interface").lower():
                return cls(*args, **kwargs)
        raise Exception("Database interface %s not found" % db_type)


import json
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key, Attr
from boto3.dynamodb.types import TypeDeserializer, TypeSerializer


class DynamoDBInterface(DBInterface):
    """
    Interface to AWS DynamoDB for logging


    Boto3 will check these environment variables for credentials:

    AWS_ACCESS_KEY_ID - The access key for your AWS account.
    AWS_SECRET_ACCESS_KEY - The secret key for your AWS account.
    AWS_SESSION_TOKEN - The session key for your AWS account. This is only needed when you 
        are using temporary credentials. The AWS_SECURITY_TOKEN environment variable 
        can also be used, but is only supported for backwards compatibility purposes. 
        AWS_SESSION_TOKEN is supported by multiple AWS SDKs besides python.


    AWS_DEFAULT_REGION - The default AWS Region to use, for example, us-west-1 or us-west-2 or ca-central-1
    """

    def __init__(self, host=None, port=None, **args):
        self.event_logger.info("Created DynamoDBInterface")
        self.enabled = True
        if host is not None:
            self.url = "http://%s:%s/" % (host, int(port))
            self.server = boto3.resource('dynamodb', endpoint_url=self.url)
        else:
            self.server = boto3.resource('dynamodb')

        self.database = None

        self.enabled = True
        # self.check_connection()

    def create_device_table(self, name=""):
        """
        Internal function to create device table if it does not exist.
        """
        if not self.enabled:
            return
        try:
            table = self.server.create_table(
                TableName='device_%s' % name,
                KeySchema=[
                    {
                        'AttributeName': 'serial',
                        'KeyType': 'HASH'
                    },
                    {
                        'AttributeName': 'product',
                        'KeyType': 'RANGE'
                    }
                ],
                AttributeDefinitions=[
                    {
                        'AttributeName': 'serial',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'product',
                        'AttributeType': 'S'
                    }
                ],
                ProvisionedThroughput={
                    'ReadCapacityUnits': 1,
                    'WriteCapacityUnits': 1
                }
            )
            # Wait until the table exists.
            table.meta.client.get_waiter('table_exists').wait(TableName='device')
        # except Exception as e:
        except Exception as e:
            self.event_logger.info("DynamoDBInterface exception handled: %s" % e)
            # pub.sendMessage("system", message={
            #    "message": "DynamoDBInterface:\n%s"%e           
            #    })

            return False
        return True

    def create_result_table(self, table_name):
        if not self.enabled:
            return
        try:
            table = self.server.create_table(
                TableName=table_name,
                KeySchema=[
                    {
                        'AttributeName': 'serial',
                        'KeyType': 'HASH'
                    },
                    {
                        'AttributeName': 'timestamp',
                        'KeyType': 'RANGE'
                    }
                ],
                AttributeDefinitions=[
                    {
                        'AttributeName': 'serial',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'timestamp',
                        'AttributeType': 'S'
                    }
                ],
                ProvisionedThroughput={
                    'ReadCapacityUnits': 1,
                    'WriteCapacityUnits': 1
                }
            )
            # Wait until the table exists.
            table.meta.client.get_waiter('table_exists').wait(TableName=table_name)
        except Exception as e:
            self.event_logger.exception("DynamoDBInterface exception handled: %s" % e)
        return True

    def set_database(self, database_name):
        super().set_database(database_name)
        self.create_device_table(database_name)
        self.create_result_table(database_name)

    def log_result(self, result):
        """
        Log test run result.

        Use JSON encode/decode to put format data in a way that works for dynamodb
        """
        if not self.enabled:
            return
        table = self.server.Table(self.database)

        d = json.decoder.JSONDecoder(parse_float=str)
        a = json.dumps(result)
        item = d.decode(a)
        response = table.put_item(Item=item)

    def log_device(self, device):
        """
        Log device data

        TODO: validate incoming data
        """
        if not self.enabled:
            return
        table = self.server.Table('device_%s' % self.database)
        d = device.log_device_dict()
        response = table.put_item(Item=d)

    def db_export(self, config, fname):
        raise Exception("Not implemented")


class CouchDBInterface(DBInterface):
    """
    Interface to CouchDB for logging 
    """

    # for testing

    def __init__(self, host="127.0.0.1", port=5984, username="production", password="", product=""):
        import couchdb
        self.enabled = True
        self.url = "http://%s:%s@%s:%d/" % (username, password, host, int(port))
        self.server = couchdb.Server(self.url)
        self.database = None
        self.product = product

    def log_result(self, result):
        """
        Format test results and add to database
        """
        if self.database is None or not self.enabled:
            return True

        errors = set()
        if result["result"] != "PASS":
            last_step = ""
            last_errors = []
            for step in result['steps']:
                if last_step != step['test_id'] and len(last_errors) > 0:
                    errors.update(last_errors)
                last_step = step['test_id']
                last_errors = step['error_code']

            if len(last_errors) > 0:
                errors.update(last_errors)

        # result_doc["card_eui"] = result["card_eui"]
        result_doc = {}
        result_doc["errors"] = list(errors)
        result_doc["executed"] = result["timestamp"]
        result_doc["executedBy"] = result["operator_id"]
        result_doc["fixture"] = result["fixture"]
        result_doc["logs"] = result
        result_doc["product"] = self.product
        result_doc["serial"] = result["serial"]
        result_doc["slot"] = result["slot"]
        # result_doc["stage"] = 0
        result_doc["type"] = "test"
        try:
            self._save(result_doc)
            return True
        except:
            # couchdb error
            return False

    def log_device(self, device=None):
        if device is None:
            # no device
            return True

        if self.database is None or not self.enabled:
            return True

        d = device.log_device_dict()
        if d["_id"] == "" or d["_id"] is None:
            return True

        # TODO: we are updating the previous SN
        if d["_id"] in self.database:
            old = self.database[d["_id"]]
            d["_rev"] = old["_rev"]

        d["updated"] = datetime.datetime.now(timezone.utc).astimezone().isoformat()

        try:
            self._save(d)
            return True
        except Exception as e:
            # couchdb error
            self.event_logger.exception("CouchDBDBInterface: %s" % e)
            return False
