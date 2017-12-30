#!/usr/bin/env python
import json
from datetime import datetime, timedelta

try:
    import humanize
except ImportError:
    humanize = None

import requests
import os

from flask import Flask
from flask import request
from flask import make_response

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])

def webhook():
    data = main("34", "53235", "west", "1")
    res = json.dumps(data, indent=4)
    r = make_response(res)
    r.headers['Content-Type'] = 'application/json'
    return r

class STMBus(object):

    def __init__(self, line, stop, direction, maxResults=5):
        self.busLine = line
        self.busStop = stop
        self.direction = direction.lower()
        self._today = datetime.today().strftime(r'%Y%m%d')
        self._maxResults = maxResults
        self._userAgent = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.89 Safari/537.36'
        self._apiURLTemplate = 'https://api.stm.info/pub/i3/v1c/api/en/lines/{line}/stops/{stop}/arrivals?d={today}&t=0000&direction={direction}&wheelchair=0&limit={limit}'
        self._refererURLTemplate = 'http://beta.stm.info/en/info/networks/bus/shuttle/line-{line}-{direction}/{stop}'
        self._rawData = {}

    @property
    def api_url(self):
        return self._apiURLTemplate.format(
            line=self.busLine, stop=self.busStop, direction=self.direction[0].upper(), today=self._today, limit=self._maxResults)

    @property
    def referer_url(self):
        return self._refererURLTemplate.format(line=self.busLine, direction=self.direction, stop=self.busStop)

    @property
    def request_headers(self):
        return {'Origin': 'http://beta.stm.info', 'User-Agent': self._userAgent, 'Referer': self.referer_url}

    def getAPIResponse(self, asJSON=False):
        page = requests.get(self.api_url, headers=self.request_headers)
        text = page.content
        if asJSON:
            return json.loads(text)
        return text

    def getJSON(self, force=False):
        if not self._rawData or force:
            self._rawData = self.getAPIResponse(asJSON=True)
        return self._rawData

    @property
    def prettyJSON(self):
        return json.dumps(self.getJSON(), indent=4)

    @property
    def schedule(self):
        return self.getJSON()['result']

    @property
    def nextBusInRealtime(self):
        for entry in self.schedule:
            if entry['is_real']:
                return int(entry['time'].strip('<'))

    @staticmethod
    def futureHourMinToDatetime(hour, minute):
        now = datetime.now()
        then = datetime.now().replace(hour=hour, minute=minute)
        if then < now:
            then += timedelta(days=1)
        return then

    def printSchedule(self):
        #print('Next {line} bus going {direction} at stop {stop}:\n'.format(
            #line=self.busLine, direction=self.direction, stop=self.busStop))

        for entry in self.schedule:
            text = ''
            if entry['is_real']:
                text += 'Realtime:  {0} minutes'.format(entry['time'])
            else:
                text += 'Scheduled: {0} hour {1} minutes'.format(entry['time'][:2], entry['time'][2:])
                if humanize:
                    hour = int(entry['time'][:2])
                    minute = int(entry['time'][2:])
                    then = self.futureHourMinToDatetime(hour, minute)
                    text += ' ({0})'.format(humanize.naturaltime(then))

            if entry['is_cancelled']:
                text += ' but is CANCELLED! :('

            if entry['is_real'] and entry['is_congestion']:
                text += ' (but there is congestion!)'

            if entry['is_at_stop']:
                text += ' and IT IS AT THE STOP! (GO GO GO!!)'

            if text:
                return text

def main(line, stop, direction, max_results):
    """
    Print upcoming schedule and realtime data for an STM bus.

    Example: stmbus.py 715 52975 east
    """
    bus = STMBus(line, stop, direction, maxResults=max_results)
    return {
        "speech": bus.printSchedule(),
        "displayText": bus.printSchedule(),
        "source": "Alan_BusTool"
    }

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    print("Starting app on port %d" % port)
    app.run(debug=False, port=port, host='0.0.0.0')
