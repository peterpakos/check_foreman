This Nagios plug-in is made to monitor the Foreman server by accessing both its UI and API.

    foreman.py 0.1
    Usage: foreman.py [OPTIONS]

    AVAILABLE OPTIONS:
    -H <url>        URL address of the Foreman server
    -u <user>       Foreman username
    -p <pass>       Foreman password
    -t host/disk    Choose test to be run (default: host)

    -w              WARNING threshold
                    (Default host: 150, disk: 100GB)
    -c              CRITICAL threshold
                    (Default host: 200, disk: 50GB)
    -h              Print this help summary page
    -V              Print version number