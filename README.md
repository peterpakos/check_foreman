This Nagios plug-in is made to monitor the Foreman server by accessing both its UI and API.

    foreman.py 1.0
    Usage: foreman.py [OPTIONS]

    AVAILABLE OPTIONS:
    -H <url>        URL address of the Foreman server
    -u <user>       Foreman username
    -p <pass>       Foreman password
    -t host/disk    Choose test to be run (default: host)

    -w              WARNING threshold
                    default: 150 (host), 100GB (disk)
    -c              CRITICAL threshold
                    default: 200 (host), 50GB (disk)
    -h              Print this help summary page
    -V              Print version number

