#!/usr/bin/python
#
# Nagios plug-in to monitor Foreman hosts
#
version = '0.1'
#
# Author: Peter Pakos <peter.pakos@wandisco.com>
# Copyright (C) 2015 WANdisco

import sys
import urllib2
import base64
import json
import getopt
import os

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
        try:
            result = urllib2.urlopen(request)
        except urllib2.HTTPError as err:
            print "HTTP Error Code %s (%s)" % (err.code, err.reason)
            app.die(3)
        except urllib2.URLError as err:
            print "URL Error (%s)" % err.reason
            app.die(3)
        except ValueError:
            print "Incorrect API URL"
            app.die(3)

        return json.load(result)

    # Fetch number of vmware hosts
    def fetch_vmware_hosts(self, url='/hosts?search=compute_resource_id=6'):
        url = self.api_url + url
        data = self.get_json_data(url)
        try:
            return int(data['subtotal'])
        except TypeError:
            print "Incorrect data type returned by remote host"
            app.die(3)

    # Fetch number of total hosts
    def fetch_total_hosts(self, url='/dashboard'):
        url = self.api_url + url
        data = self.get_json_data(url)
        try:
            return int(data['total_hosts'])
        except TypeError:
            print "Incorrect data type returned by remote host"
            app.die(3)


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

        self.script_name = os.path.basename(argv[0])
        self.script_version = version
        self.argv = argv[1:]
        self.default_warning = config['warning']
        self.default_critical = config['critical']
        self.parse_options()

    def parse_options(self):

        try:
            options, args = getopt.getopt(self.argv, "w:c:h", [
                'help',
                'warning=',
                'critical='
                ])

        except getopt.GetoptError:
            self.usage()

        for opt, arg in options:
            if opt in ('-h', '--help'):
                self.usage()
            elif opt in ('-w', '--warning'):
                try:
                    config['warning'] = int(arg)
                except ValueError:
                    print "Incorrect value of WARNING threshold: %s" % arg
                    self.die(3)

            elif opt in ('-c', '--critical'):
                try:
                    config['critical'] = int(arg)
                except:
                    print "Incorrect value of CRITICAL threshold: %s" % arg
                    self.die(3)

            else:
                self.usage()

        if config['warning'] > config['critical']:
            print "Error: WARNING threshold is higher than CRITICAL threshold."
            self.die(3)

    def usage(self):
        print "%s %s" % (self.script_name, self.script_version)
        print "Usage: %s [OPTIONS]" % self.script_name
        print "AVAILABLE OPTIONS:"
        print "-h\tPrint this help summary page"
        print "-w\tWARNING threshold (default: %i)" % self.default_warning
        print "-c\tCRITICAL threshold (default: %i)" % self.default_critical
        self.die(3)

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

    def die(self, code=0):
        sys.exit(code)

# Run the script...
if __name__ == '__main__':
    app = Main(sys.argv)
    app.run()
