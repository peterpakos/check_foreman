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
except ImportError as err:
    print "Import Error: %s" % err
    sys.exit(3)


# Global config class (uninstantiated)
class config:
    app_version = "0.1"
    host_warning = 150
    host_critical = 200
    disk_warning = 100
    disk_critical = 50


# Class ForemanServer
class ForemanServer(object):

    # Constructor method
    def __init__(self, foreman_url, foreman_user, foreman_pass):
        self.foreman_url = foreman_url
        self.foreman_api_url = foreman_url + '/api/v2'
        self.foreman_user = foreman_user
        self.foreman_pass = foreman_pass

    def fetch_datastore_info(self):
        payload = {
            'authenticity_token':
            'Zq7o/8Ap9F0uSWLTUcEx/4ezcsz+HXIQ76LoE/A7jDc=',
            'login[login]': self.foreman_user,
            'login[password]': self.foreman_pass
        }

        headers = {
            'Content-Type': None,
            'Accept': 'text/html',
            'User-Agent': None
        }

        with session() as s:
            try:
                s.post(
                    self.foreman_url + '/users/login',
                    headers=headers,
                    data=payload,
                    verify=False
                )
            except:
                app.die(3, "Error: Problem with logging in to Foreman UI")
            page = s.get(
                self.foreman_url + '/compute_profiles/1'
                                   '/compute_resources/6-SHDC_ALM_VC'
                                   '/compute_attributes/new',
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
            self.foreman_user,
            self.foreman_pass
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
    def fetch_vmware_hosts(self):
        url = self.foreman_api_url + "/hosts?search=compute_resource_id=6"
        data = self.get_json_data(url)
        try:
            return int(data['subtotal'])
        except TypeError as err:
            app.die(3, "Unknown data type returned by remote host (%s)" % err)

    # Fetch number of total hosts
    def fetch_total_hosts(self):
        url = self.foreman_api_url + "/dashboard"
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
        self.foreman_url = None
        self.foreman_user = None
        self.foreman_pass = None
        self.test = self.parse_options()

    # Parse arguments and select test to be run
    def parse_options(self):
        test = 'host'
        warning = None
        critical = None
        try:
            options, args = getopt.getopt(sys.argv[1:], "H:u:p:t:w:c:hV", [
                'help',
                'warning=',
                'critical=',
                'test=',
                'version'
                'host=',
                'user=',
                'pass='
            ])

        except getopt.GetoptError:
            self.usage()

        for opt, arg in options:
            if opt in ('-H', '--host'):
                self.foreman_url = arg
            if opt in ('-u', '--user'):
                self.foreman_user = arg
            if opt in ('-p', '--pass'):
                self.foreman_pass = arg
            if opt in ('-t', '--test'):
                if arg == 'disk':
                    test = arg
                elif arg == 'host':
                    test = arg
                else:
                    self.die(3, "Error: Unknown test %s" % arg)
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
                    self.die(3, "Error: Incorrect value of WARNING: %s" % arg)
            elif opt in ('-c', '--critical'):
                try:
                    critical = int(arg)
                except ValueError:
                    self.die(3, "Error: Incorrect value of CRITICAL: %s" % arg)

        if self.foreman_url is None:
            self.die(3, "Error: Foreman URL not specified")
        if self.foreman_user is None:
            self.die(3, "Error: Foreman user not specified")
        if self.foreman_pass is None:
            self.die(3, "Error: Foreman URL not specified")

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
            self.die(3, "Error: WARNING threshold is higher than CRITICAL")
        if config.disk_warning < config.disk_critical:
            self.die(3, "Error: WARNING threshold is lower than CRITICAL")

        return test

    # Display help page
    def usage(self):
        print "%s %s" % (self.app_name, self.app_version)
        print "Usage: %s [OPTIONS]" % self.app_name
        print "AVAILABLE OPTIONS:"
        print "-H <url>\tURL address of the Foreman server"
        print "-u <user>\tForeman username"
        print "-p <pass>\tForeman password"
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
            self.foreman_url,
            self.foreman_user,
            self.foreman_pass,
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

            message = "%s - VMware hosts: %i, Total hosts: %i" % (
                status,
                vmware_hosts,
                total_hosts
            )
            message = "%s|'VMware hosts'=%i;%i;%i;%i;%i 'Total hosts'=%i" % (
                message,
                vmware_hosts,
                config.host_warning,
                config.host_critical,
                0,
                500,
                total_hosts
            )

        elif self.test == 'disk':
            datastores = foreman.fetch_datastore_info()
            code = -1
            mlist = []
            status = 'UNKNOWN'
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

            if len(datastores) > 0:
                message = "%s - %s" % (status, ', '.join(mlist))
                mlist = []
                for ds, v in sorted(datastores.iteritems()):
                    free = v['free']
                    total = v['total']
                    mlist.append("'%s'=%.0fGB;%i;%i;%i;%i" % (
                        ds,
                        free,
                        config.disk_warning,
                        config.disk_critical,
                        0,
                        total
                    ))
                message = "%s|%s" % (
                    message,
                    ' '.join(mlist)
                )

            else:
                self.die(3, "%s - No datastores found" % status)

        else:
            self.die(3, "Incorrect test type, terminating...")

        self.die(code, message)

    # Exit app with code and optional message
    def die(self, code=0, message=None):
        if message is not None:
            print message
        sys.exit(code)

# Instantiate main class and run it
if __name__ == '__main__':
    app = Main()
    app.run()
