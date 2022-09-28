from __future__ import unicode_literals

# import avro
from avro_validator.schema import Schema
import os

class SchemaBuilder(object):

    def __init__(self, schema_name, schema_version):
        self.schema_name = schema_name
        self.schema_version = schema_version
        self.schema = None

    def load(self):
        project_root = os.path.dirname(os.path.dirname(__file__))
        schema_file = os.path.join(
            project_root,
            'config/schemas/{schema_name}-{schema_version}.avsc'.format(schema_name=self.schema_name, schema_version=self.schema_version)
        )
        with open(schema_file, 'rb') as fp:
            # self.schema = avro.schema.parse(fp.read())
            self.schema = Schema(schema_file).parse()
        return self

    def validate(self, payload):
        if self.schema is None:
            raise ValueError("No Schema has been loaded")
        self.schema.validate(payload)
