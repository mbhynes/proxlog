from __future__ import unicode_literals

import os

import io
from avro.io import BinaryEncoder, DatumWriter
import json

from google.cloud import pubsub_v1
from google.pubsub_v1.types import Encoding

from proxlog.config import SchemaBuilder


class PubSubRequestLogger(object):
  """
  Proxy MITM logger addon to log request metadata to a pubsub topic in google cloud.

  This class is used with `mitmdump` or `mitmproxy` to log request activity to
  the topic specific in the class variable PUBSUB_TOPIC.
  """

  SUPPORTED_ENCODINGS = ['UTF-8']
  PROJECT = 'proxbox'
  PUBSUB_TOPIC = 'requests'
  SCHEMA_VERSION = '1.0'
  SCHEMA = SchemaBuilder(PUBSUB_TOPIC, SCHEMA_VERSION).load()

  def __init__(self, encoding='UTF-8'):
    assert encoding in self.SUPPORTED_ENCODINGS
    self.encoding = encoding
    self.publisher_client = pubsub_v1.PublisherClient()

  @property
  def topic_path(self):
    return self.publisher_client.topic_path(self.PROJECT, self.PUBSUB_TOPIC)

  @property
  def topic(self):
    return self.publisher_client.get_topic(request=dict(topic=self.topic_path))

  def request(self, flow):
    """
    Log an event for each request to MITM proxy.
    """
    payload = self._build_payload(flow)
    if self._validate_payload(payload):
      # self._test_publish_payload(payload)
      self._publish_payload(payload)

  def _build_payload(self, flow):
    user_payload = {
      'username': os.getenv('USER'),
      'hostname': os.uname().nodename,
    }

    flow_payload = {
      'flow_id':              flow.id,
      'flow_type':            flow.type,
      'flow_mode':            flow.mode,
      'client_ip':            flow.client_conn.address[0],
      'client_port':          flow.client_conn.address[1],
      'server_ip':            flow.server_conn.ip_address[0],
      'server_address':       flow.server_conn.address[0],
      'server_address_port':  flow.server_conn.address[1],
    }

    request_headers = dict(flow.request.headers.fields)

    request_payload = {
      'request_timestamp_start':  flow.request.data.timestamp_start,
      'request_timestamp_end':    flow.request.data.timestamp_end,
      'method':                   flow.request.data.method.decode(self.encoding),
      'scheme':                   flow.request.data.scheme.decode(self.encoding),
      'path':                     flow.request.data.path.decode(self.encoding),
      'authority':                flow.request.data.authority.decode(self.encoding),
      'http_version':             flow.request.data.http_version.decode(self.encoding),
      'user_agent':               request_headers.get('User-Agent'),
      'accept':                   request_headers.get('Accept'),
    }
    payload = {**user_payload, **flow_payload, **request_payload}
    return payload

  def _validate_payload(self, payload):
    try:
      self.SCHEMA.validate(payload)
    except ValueError as e:
      print(e)
      return False
    return True

  def _publish_payload(self, payload):
    encoding = self.topic.schema_settings.encoding
    encoded = self._encode_payload(payload, encoding)
    future = self.publisher_client.publish(self.topic_path, data=encoded)
    return future.result()

  @classmethod
  def _encode_json_payload(payload):
    return json.dumps(payload).encode("utf-8")

  @classmethod
  def _encode_binary_payload(payload):
    writer = DatumWriter(self.SCHEMA.schema)
    bytes_buffer = io.BytesIO()
    encoder = BinaryEncoder(bytes_buffer)
    writer.write(payload, encoder)
    encoded = bytes_buffer.getvalue()
    return encoded

  @classmethod
  def _encode_payload(cls, payload, encoding):
    if encoding == Encoding.BINARY:
      return cls._encode_binary_payload(payload)
    if encoding == Encoding.JSON:
      return cls._encode_json_payload(payload)
    if encoding == Encoding.ENCODING_UNSPECIFIED:
      return cls._encode_json_payload(payload)

  def _test_publish_payload(self, payload):
    with open('output.json', 'a') as fp:
      json.dump(payload, fp)
      fp.write(os.linesep)
    fp.close()
