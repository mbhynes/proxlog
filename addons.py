from mitmproxy import ctx

from proxlog.client import client
from proxlog.client import RequestsStreamingTableWriter

addons = [
  RequestsStreamingTableWriter(client=client, logger=ctx.log),
]
