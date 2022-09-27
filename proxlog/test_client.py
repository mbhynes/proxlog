import pytest
from unittest.mock import Mock

from proxlog.client import StreamingTableWriter


class SimpleWriter(StreamingTableWriter):

  table_repr = {
    'tableReference': {
      'datasetId': 'logs',
      'tableId': 'requests_test',
    },
    'schema': {
      'fields': [{
        "name" : "count",
        "type" : "INTEGER",
      }]
    },
  }
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.k = 0
  
  def build_payload(self, flow):
    self.k += 1
    return {
      'count': self.k,
    }


class TestRequestsWriter:

  def test_request(self):
    mock_client = Mock()
    mock_client.insert_rows = Mock(return_value=[])
    writer = SimpleWriter(client=mock_client, buffer_size=3)
    writer._table = Mock()
    writer.request(flow=Mock())
    writer.request(flow=Mock())
    assert writer._row_buffer == [
      {'count': 1},
      {'count': 2},
    ]
    writer.request(flow=Mock())
    mock_client.insert_rows.assert_called_with(writer.table, [
      {'count': 1},
      {'count': 2},
      {'count': 3},
    ])
    assert writer._row_buffer == []
