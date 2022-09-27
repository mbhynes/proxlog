import asyncio
from copy import deepcopy
import datetime
import logging
import os

from google.api_core.exceptions import NotFound

import google.cloud.bigquery as bq

client = bq.Client()

REF_DATE = datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc) 

def epoch_ms_to_datetime(ms):
  return REF_DATE + datetime.timedelta(milliseconds=int(1000 * ms))


class StreamingTableWriter:

  table_repr = {}

  def __init__(self, client, buffer_size=2**2, logger=logging):
    self.client = client
    self.buffer_size = buffer_size
    self.logger = logger
    self._table = None
    self._row_buffer = []

  @property
  def project(self):
    return self.client.project

  @property
  def dataset(self):
    return self.table_repr["tableReference"]["datasetId"]

  @property
  def table_reference(self):
    table = self.table_repr["tableReference"]["tableId"]
    return f"{self.project}.{self.dataset}.{table}"

  @property
  def table(self):
    if self._table is not None:
      return self._table
    try:
      self.client.get_dataset(self.dataset)
    except NotFound:
      self.client.create_dataset(bq.Dataset(f"{self.project}.{self.dataset}"))

    try:
      table = client.get_table(self.table_reference)
    except NotFound:
      table_repr = deepcopy(self.table_repr)
      table_repr["tableReference"]["projectId"] = self.project
      table = bq.Table.from_api_repr(table_repr)
      table = self.client.create_table(table)
    self._table = table
    return self._table

  def build_payload(self, flow):
    raise NotImplementedError

  def request(self, flow):
    """
    Log an event for each request to MITM proxy.
    """
    payload = self.build_payload(flow)
    # asyncio.create_task(self._post(payload))
    self._insert_buffered_rows(payload)

  async def _post(self, payload):
    errors = await asyncio.coroutine(self.client.insert_rows)(self.table, [{}])
    for e in errors:
      self.log.error(e)
    await asyncio.sleep(1)

  def _insert_buffered_rows(self, payload):
    self._row_buffer.append(payload)
    nrows = len(self._row_buffer) 
    if nrows < self.buffer_size:
      return
    self.logger.error(f"Flushing buffer; posting {nrows} rows to BQ")
    errors = self.client.insert_rows(self.table, self._row_buffer)
    self._row_buffer = []
    for e in errors:
      self.logger.error(f"Encountered exception {e} during client.insert_rows")


class RequestsStreamingTableWriter(StreamingTableWriter):

  encoding = 'UTF-8'

  table_repr = {
    "tableReference": {
      "datasetId": "logs",
      "tableId": "requests",
    },
    "timePartitioning": {
      "type": "DAY",
      "field": "request_timestamp_start",
    },
    "schema": {
      "fields": [{
          "name" : "username",
          "type" : "STRING",
        }, {
          "name" : "hostname",
          "type" : "STRING",
        }, {
          "name" : "flow_id",
          "type" : "STRING",
        }, {
          "name" : "flow_type",
          "type" : "STRING",
        }, {
          "name" : "flow_mode",
          "type" : "STRING",
        }, {
          "name" : "client_ip",
          "type" : "STRING",
        }, {
          "name" : "client_port",
          "type" : "INTEGER",
        }, {
          "name" : "server_ip",
          "type" : "STRING",
        }, {
          "name" : "server_address",
          "type" : "STRING",
        }, {
          "name" : "server_address_port",
          "type" : "INTEGER",
        }, {
          "name" : "request_timestamp_start",
          "type" : "TIMESTAMP"
        }, {
          "name" : "request_timestamp_end",
          "type" : "TIMESTAMP"
        }, {
          "name" : "method",
          "type" : "STRING",
        }, {
          "name" : "scheme",
          "type" : "STRING",
        }, {
          "name" : "path",
          "type" : "STRING",
        }, {
          "name" : "authority",
          "type" : "STRING",
        }, {
          "name" : "headers",
          "type" : "STRING",
        }, {
          "name" : "http_version",
          "type" : "STRING",
        }, {
          "name" : "user_agent",
          "type" : "STRING",
        }, {
          "name" : "accept",
          "type" : "STRING",
        }
      ],
    }
  }

  def build_payload(self, flow):
    user_payload = {
      "username": os.getenv("USER"),
      "hostname": os.uname().nodename,
    }

    flow_payload = {
      "flow_id":              flow.id,
      "flow_type":            flow.type,
      "flow_mode":            flow.mode,
      "client_ip":            flow.client_conn.address[0],
      "client_port":          flow.client_conn.address[1],
      "server_ip":            flow.server_conn.ip_address[0] if flow.server_conn.ip_address else None,
      "server_address":       flow.server_conn.address[0] if flow.server_conn.address else None,
      "server_address_port":  flow.server_conn.address[1] if flow.server_conn.address else None,
    }

    request_headers = dict(flow.request.headers.fields)

    request_payload = {
      "request_timestamp_start":  epoch_ms_to_datetime(flow.request.data.timestamp_start),
      "request_timestamp_end":    epoch_ms_to_datetime(flow.request.data.timestamp_end),
      "method":                   flow.request.data.method.decode(self.encoding),
      "scheme":                   flow.request.data.scheme.decode(self.encoding),
      "path":                     flow.request.data.path.decode(self.encoding),
      "authority":                flow.request.data.authority.decode(self.encoding),
      "http_version":             flow.request.data.http_version.decode(self.encoding),
      "user_agent":               request_headers.get("User-Agent"),
      "accept":                   request_headers.get("Accept"),
    }
    payload = {**user_payload, **flow_payload, **request_payload}
    return payload
