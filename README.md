# proxlog

`proxlog` is a DIY web traffic monitoring tool, so you can monitor yourself like you're at work, at home!

The repo contains addons for [mitmproxy](https://mitmproxy.org/) that monitor your HTTP traffic and stream it into BigQuery in a Google cloud project for your later analytical pleasure, if that's the sort of thing you're into.

## Setup

This repo contains code specifically built to run on Mac, using the network configuration tool `networksetup`. (Similar tools exist on other systems, of course).

To install the dependencies and build a cloud project, use the following:
```
./dev up
```

## Running the Monitor

To run the monitor, use the command:
```
./dev run
```

This will run a proxy instance of `mitmdump` on your local machine, streaming intercepted HTTP traffic to BigQuery.
