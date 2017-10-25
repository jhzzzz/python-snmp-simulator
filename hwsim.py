"""
This file is part of SNMP agent simulator,
which used for simulate HUAWEI server iBMC/HMM SNMP interfaces.

author: Jack Zhang
crated: 2017/4/5
"""

import sys
import getopt
import json
import threading
import collections
import time
from snmp_agent import SNMPAgent

# below code is for remote debug only
# import pydevd
# import ptvsd

# pydevd.settrace('192.168.99.240', port=9002, stdoutToServer=True, stderrToServer=True)
# ptvsd.settrace(None, ('0.0.0.0', 9002))
# debug.setLogger(debug.Debug('all'))
# time.sleep(5)

if __name__ == '__main__':
    helpMessage = """
    SNMP Agent Simulator by HUAWEI enterprise.

    Usage: %s [-h]
        [-v]
        [-d]
        [-p=<port>]
        [-a=<trap receiver agent ip address>]
        [-P=<trap receiver agent port>]""" % (sys.argv[0])

    try:
        opts, params = getopt.getopt(sys.argv[1:], 'hvdp:a:P:', ['help','version','debug','port=','agent=','agent-port='])
    except Exception:
        sys.stderr.write('ERROR: %s\r\n%s\r\n' % (sys.exc_info()[1], helpMessage))
        sys.exit(-1)

    verboseFlag = False
    port = 161
    agentHost = '127.0.0.1'
    agentPort = 161
    mibFiles = []

    for opt in opts:
        if opt[0] == '-v' or opt[0] == '--version':
            sys.stderr.write('SNMP Simulator VERSION 1.0')
            sys.exit(-1)
        if opt[0] == '-h' or opt[0] == '--help':
            sys.stderr.write(helpMessage)
            sys.exit(-1)
        if opt[0] == '-d' or opt[0] == '--debug':
            verboseFlag = True
        if opt[0] == '-p' or opt[0] == '--port':
            port = int(opt[1])
        if opt[0] == '-a' or opt[0] == '--agent':
            agentHost = opt[1]
        if opt[0] == '-P' or opt[0] == '--agent-port':
            agentPort = int(opt[1])

    mibFiles = params
    if len(mibFiles) == 0:
        mibFiles = ['HUAWEI-SERVER-IBMC-MIB'] #'HWSMM-MIB', 'HW-PDUM-MIB'
    agent = SNMPAgent(mibFiles, port, verboseFlag)

    # Currently needn't this function
    # agent.setTrapReceiver('192.168.99.237', 'traps')
    # Worker(agent, mib).start()

    try:
        agent.serve_forever()

    except KeyboardInterrupt:
        print "Shutting down SNMP agent now!"
