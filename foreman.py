#!/usr/bin/python
#
# Nagios plug-in to monitor Foreman hosts
#
# Author: Peter Pakos <peter.pakos@wandisco.com>
# Copyright (C) 2015 WANdisco

try:
    import sys
    import urllib2
    import base64
    import json
    import getopt
    import os
    from requests import session
    from lxml import html
    from requests.packages.urllib3 import disable_warnings
    disable_warnings()
except ImportError as err:
    print "Import Error: %s" % err
    sys.exit(3)


# Global config class (uninstantiated)
class config:
    app_version = "0.1"
    url = "https://foreman.shdc.wandisco.com"
    api_url = url + '/api/v2'
    login_url = url + '/users/login'
    ds_url = url + '/compute_profiles/1' \
                   '/compute_resources/6-SHDC_ALM_VC' \
                   '/compute_attributes/new'
    api_user = "api"
    api_pass = "Lood2ooPhi"
    host_warning = 150
    host_critical = 200
    disk_warning = 100
    disk_critical = 50


# Class ForemanServer
class ForemanServer(object):

    # Constructor method
    def __init__(self, api_url, api_user, api_pass):
        self.api_url = api_url
        self.api_user = api_user
        self.api_pass = api_pass

    def fetch_datastore_info(self):
        payload = {
            'authenticity_token':
            'Zq7o/8Ap9F0uSWLTUcEx/4ezcsz+HXIQ76LoE/A7jDc=',
            'login[login]': self.api_user,
            'login[password]': self.api_pass
        }

        headers = {
            'Content-Type': None,
            'Accept': 'text/html',
            'User-Agent': None
        }

        with session() as s:
            s.post(
                config.login_url,
                headers=headers,
                data=payload,
                verify=False
            )
            page = s.get(
                config.ds_url,
                headers=headers,
                verify=False
            )
        tree = html.document_fromstring(page.text).getroottree()
        stores = tree.xpath(
            '//select[@name="compute_attribute[vm_attrs]'
            '[volumes_attributes][0][datastore]"]/option'
        )

        datastores = {}
        for store in stores:
            # EQL_VSPHERE_DS1 (free: 243 GB, prov: 481 GB, total: 500 GB)
            if "EQL_VSPHERE_" in store.text:
                line = store.text.split()
                datastores.update({line[0]: {
                    'free': float(line[2]),
                    'free_unit': line[3].replace(',', ''),
                    'prov': float(line[5]),
                    'prov_unit': line[6].replace(',', ''),
                    'total': float(line[8]),
                    'total_unit': line[9].replace(',', '')
                }})

        return datastores

    # Encode user:pass in headers and get json data
    def get_json_data(self, url):
        request = urllib2.Request(url)
        base64string = base64.encodestring("%s:%s" % (
            config.api_user,
            config.api_pass
            )).replace('\n', '')
        request.add_header("Authorization", "Basic %s" % base64string)
        try:
            result = urllib2.urlopen(request)
        except urllib2.HTTPError as err:
            app.die(3, "HTTP Error Code %s (%s)" % (err.code, err.reason))
        except urllib2.URLError as err:
            app.die(3, "URL Error (%s)" % err.reason)
        except ValueError:
            app.die(3, "Incorrect API URL")

        return json.load(result)

    # Fetch number of vmware hosts
    def fetch_vmware_hosts(self, url="/hosts?search=compute_resource_id=6"):
        url = self.api_url + url
        data = self.get_json_data(url)
        try:
            return int(data['subtotal'])
        except TypeError as err:
            app.die(3, "Unknown data type returned by remote host (%s)" % err)

    # Fetch number of total hosts
    def fetch_total_hosts(self, url="/dashboard"):
        url = self.api_url + url
        data = self.get_json_data(url)
        try:
            return int(data['total_hosts'])
        except TypeError as err:
            app.die(3, "Unknown data type returned by remote host (%s)" % err)


# Main class
class Main(object):

    # Constructor method
    def __init__(self):

        self.app_name = os.path.basename(sys.argv[0])
        self.app_version = config.app_version
        self.default_host_warning = config.host_warning
        self.default_host_critical = config.host_critical
        self.default_disk_warning = config.disk_warning
        self.default_disk_critical = config.disk_critical
        self.test = self.parse_options()

    # Parse arguments and select test to be run
    def parse_options(self):
        test = 'host'
        warning = None
        critical = None
        try:
            options, args = getopt.getopt(sys.argv[1:], "t:w:c:hV", [
                'help',
                'warning=',
                'critical=',
                'test=',
                'version'
            ])

        except getopt.GetoptError:
            self.usage()

        for opt, arg in options:
            if opt in ('-t', '--test'):
                if arg == 'disk':
                    test = arg
                elif arg == 'host':
                    test = arg
                else:
                    self.die(3, "Unknown test %s, terminating..." % arg)
            if opt in ('-h', '--help'):
                self.usage()
            if opt in ('-V', '--version'):
                self.die(3, "%s version %s" % (
                    self.app_name, self.app_version)
                )
            elif opt in ('-w', '--warning'):
                try:
                    warning = int(arg)
                except ValueError:
                    self.die(3, "Incorrect value of WARNING: %s" % arg)
            elif opt in ('-c', '--critical'):
                try:
                    critical = int(arg)
                except ValueError:
                    self.die(3, "Incorrect value of CRITICAL: %s" % arg)

        if test == 'host':
            if warning is not None:
                config.host_warning = warning
            if critical is not None:
                config.host_critical = critical
        elif test == 'disk':
            if warning is not None:
                config.disk_warning = warning
            if critical is not None:
                config.disk_critical = critical

        if config.host_warning > config.host_critical:
            self.die(3, "Error: WARNING is higher than CRITICAL")
        if config.disk_warning < config.disk_critical:
            self.die(3, "Error: WARNING is lower than CRITICAL")

        return test

    # Display help page
    def usage(self):
        print "%s %s" % (self.app_name, self.app_version)
        print "Usage: %s [OPTIONS]" % self.app_name
        print "AVAILABLE OPTIONS:"
        print "-t host/disk\tChoose test to be run (default: host)"
        print "-w\t\tWARNING threshold"
        print "\t\t(Default host: %i, disk: %iGB)" % (
            self.default_host_warning,
            self.default_disk_warning
        )
        print "-c\t\tCRITICAL threshold"
        print "\t\t(Default host: %i, disk: %iGB)" % (
            self.default_host_critical,
            self.default_disk_critical
        )
        print "-h\t\tPrint this help summary page"
        print "-V\t\tPrint version number"
        self.die(3)

    # App code to be run
    def run(self):

        foreman = ForemanServer(
            config.api_url,
            config.api_user,
            config.api_pass,
        )

        if self.test == 'host':
            vmware_hosts = foreman.fetch_vmware_hosts()
            total_hosts = foreman.fetch_total_hosts()

            if 0 <= vmware_hosts and vmware_hosts < config.host_warning:
                status = 'OK'
                code = 0
            elif config.host_warning <= vmware_hosts and \
                    vmware_hosts < config.host_critical:
                status = 'WARNING'
                code = 1
            elif vmware_hosts >= config.host_critical:
                status = 'CRITICAL'
                code = 2
            else:
                status = 'UNKNOWN'
                code = 3

            message = "%s - VMware hosts: %s (Total %s)" % (
                status,
                vmware_hosts,
                total_hosts
            )

        elif self.test == 'disk':
            datastores = foreman.fetch_datastore_info()
            code = -1
            mlist = []
            for ds, v in sorted(datastores.iteritems()):
                free = v['free']
                if 0 <= free and free <= config.disk_critical:
                    if code < 2:
                        status = 'CRITICAL'
                        code = 2
                elif config.disk_critical < free and \
                        free <= config.disk_warning:
                    if code < 1:
                        status = 'WARNING'
                        code = 1
                elif free > config.disk_warning:
                    if code < 0:
                        status = 'OK'
                        code = 0
                else:
                    status = 'UNKNOWN'
                    code = 3

                mlist.append("%s: %.0fGB" % (ds, free))

            message = "%s - %s" % (
                status,
                ', '.join(mlist)
            )
        else:
            self.die(3, "Incorrect test type, terminating...")

        self.die(code, message)

    # Exit app
    def die(self, code=0, message=None):
        if message is not None:
            print message
        sys.exit(code)

# Instantiate main class and run it
if __name__ == '__main__':
    app = Main()
    app.run()
