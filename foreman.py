#!/usr/bin/python
#
# Nagios plug-in to monitor Foreman hosts
#
# Version 1.0
#
# Author: Peter Pakos <peter.pakos@wandisco.com>
# Copyright (C) 2015 WANdisco

import sys, urllib2, base64, json

# Configuration
config = {
        'api_url': 'http://foreman.shdc.wandisco.com/api/v2',
        'api_user': 'api',
        'api_pass': 'Lood2ooPhi',
        'warning': 150,
        'critical': 200
        }

# Function encoding user:pass in headers and getting json data
def get_json_data(url):
    request = urllib2.Request(url)
    base64string = base64.encodestring('%s:%s' % (config['api_user'], config['api_pass'])).replace('\n', '')
    request.add_header("Authorization", "Basic %s" % base64string)   
    result = urllib2.urlopen(request)
    return json.load(result)

# Class ForemanServer
class ForemanServer(object):

    # Initialize object
    def __init__(self, api_url, api_user, api_pass):
        self.api_url = api_url
        self.api_user = api_user
        self.api_passwd = api_pass
        self.vmware_hosts = self.fetch_vmware_hosts()
        self.total_hosts = self.fetch_total_hosts()
    
    # Fetch number of vmware hosts
    def fetch_vmware_hosts(self, url = '/hosts?search=compute_resource_id=6'):
        url = self.api_url + url
        data = get_json_data(url)
        return int(data['subtotal'])

    # Fetch number of total hosts
    def fetch_total_hosts(self, url = '/dashboard'):
        url = self.api_url + url
        data = get_json_data(url)
        return int(data['total_hosts'])

# Class Status
class Status(object):

    # Initialize object
    def __init__(self, vmware_hosts, total_hosts):
        self.vmware_hosts = vmware_hosts
        self.total_hosts = total_hosts
        self.code, self.message = self.calculate()

    # Calculate status code and message
    def calculate(self):
        if 1 <= self.vmware_hosts and self.vmware_hosts < config['warning']:
            return 0, 'OK'
        elif config['warning'] <= self.vmware_hosts and self.vmware_hosts < config['critical']:
            return 1, 'WARNING'
        elif self.vmware_hosts >= config['critical']:
            return 2, 'CRITICAL'
        else:
            return 3, 'UNKNOWN'
    
    # Display status message
    def display(self):
        print "%s - VMware hosts: %s (Total %s)" % (self.message, self.vmware_hosts, self.total_hosts)

# Main code
foreman = ForemanServer(config['api_url'], config['api_user'], config['api_pass'])
status = Status(foreman.vmware_hosts, foreman.total_hosts)
status.display()
sys.exit(status.code)
