#!/usr/bin/python
#
# Nagios plug-in to monitor Foreman hosts
#
# Version 0.1
#
# Author: Peter Pakos <peter.pakos@wandisco.com>
# Copyright (C) 2015 WANdisco

import sys
import urllib2
import base64
import json
import getopt

# Configuration
config = {
    'api_url': 'http://foreman.shdc.wandisco.com/api/v2',
    'api_user': 'api',
    'api_pass': 'Lood2ooPhi',
    'warning': 150,
    'critical': 200
    }


# Class ForemanServer
class ForemanServer(object):

    # Initialize object
    def __init__(self, api_url, api_user, api_pass):
        self.api_url = api_url
        self.api_user = api_user
        self.api_pass = api_pass
        self.vmware_hosts = self.fetch_vmware_hosts()
        self.total_hosts = self.fetch_total_hosts()

    # Function encoding user:pass in headers and getting json data
    def get_json_data(self, url):
        request = urllib2.Request(url)
        base64string = base64.encodestring('%s:%s' % (
            config['api_user'],
            config['api_pass']
            )).replace('\n', '')
        request.add_header("Authorization", "Basic %s" % base64string)
        result = urllib2.urlopen(request)
        return json.load(result)

    # Fetch number of vmware hosts
    def fetch_vmware_hosts(self, url='/hosts?search=compute_resource_id=6'):
        url = self.api_url + url
        data = self.get_json_data(url)
        return int(data['subtotal'])

    # Fetch number of total hosts
    def fetch_total_hosts(self, url='/dashboard'):
        url = self.api_url + url
        data = self.get_json_data(url)
        return int(data['total_hosts'])


# Class Status
class Status(object):

    # Initialize object
    def __init__(self, warning, critical, vmware_hosts, total_hosts):
        self.vmware_hosts = vmware_hosts
        self.total_hosts = total_hosts
        self.warn = warning
        self.crit = critical
        self.code, self.message = self.calculate()

    # Calculate status code and message
    def calculate(self):
        if 0 <= self.vmware_hosts and self.vmware_hosts < self.warn:
            return 0, 'OK'
        elif self.warn <= self.vmware_hosts and self.vmware_hosts < self.crit:
            return 1, 'WARNING'
        elif self.vmware_hosts >= self.crit:
            return 2, 'CRITICAL'
        else:
            return 3, 'UNKNOWN'

    # Display status message
    def display(self):
        print "FOREMAN %s - VMware hosts: %s (Total %s)" % (
            self.message,
            self.vmware_hosts,
            self.total_hosts
            )


# Main class
class Main(object):

    def __init__(self, argv):

        self.script_name = argv[0]
        self.argv = argv[1:]
        self.parse_options()

    def parse_options(self):

        try:
            options, args = getopt.gnu_getopt(self.argv, "w:c:h", ['help'])

        except getopt.GetoptError:
            self.die(3)

        for opt, arg in options:
            if opt in ('-h', '--help'):
                self.usage()
            elif opt == '-w':
                config['warning'] = int(arg)
            elif opt == '-c':
                config['critical'] = int(arg)
            else:
                print "ERROR, exiting..."
                sys.exit()

    def usage(self):
        print 'Usage: %s -w <warning> -c <critical>' % self.script_name
        self.die(0)

    def run(self):
        foreman = ForemanServer(
            config['api_url'],
            config['api_user'],
            config['api_pass']
        )

        status = Status(
            config['warning'],
            config['critical'],
            foreman.vmware_hosts,
            foreman.total_hosts
        )

        status.display()
        self.die(status.code)

    def die(self, code):
        sys.exit(code)

# Run the script...
if __name__ == '__main__':
    app = Main(sys.argv)
    app.run()
