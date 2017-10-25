#_*_coding:utf-8_*_

"""
This file is part of SNMP agent simulator,
which used for simulate HUAWEI server iBMC/HMM SNMP interfaces.

author: Jack Zhang
crated: 2017/4/5
"""

import sys
import random
from pysnmp.entity import engine, config
from pysnmp.entity.rfc3413 import cmdrsp, context, ntforg
from pysnmp.carrier.asynsock.dgram import udp
from pysnmp.smi import compiler, builder, view, error
from pysnmp.smi.rfc1902 import ObjectIdentity
from pysnmp import debug
from pyasn1.type import univ
from value_generator import createVariable
from value_generator import generateValue
from value_generator import loadMibJson
from value_generator import mibJsons

#debug.setLogger(debug.Debug('dsp', 'msgproc', 'secmode'))
automaticValues = 5000
maxTableSize = 3
tableSize = 2


"""
This class is used to host the SNMP agent server at 161 port,
meanwhile it will export all symbols of the input mib libraries.
"""
class SNMPAgent(object):
    def __init__(self, mibFiles, port, verboseFlag):

        self.verboseFlag = verboseFlag
        self.port = port

        # init SNMP engine and MIB builder
        self.init_snmp_engine()
        self.init_mib_builder()

        # our variables will subclass this since we only have scalar types
        # can't load this type directly, need to import it
        MibScalarInstance, = self.mibBuilder.importSymbols('SNMPv2-SMI', 'MibScalarInstance')

        # load MIB tree foundation classes
        (MibScalar, MibTable, MibTableRow, MibTableColumn) = self.mibBuilder.importSymbols(
            'SNMPv2-SMI', 'MibScalar',
            'MibTable', 'MibTableRow', 'MibTableColumn')

        skip = True
        # traverse our mib library and export all objects
        for mibFile in mibFiles:
            if self.verboseFlag:
                sys.stderr.write('# + START MIB module: %s\r\n' % mibFile)

            loadMibJson(mibFile)

            oid = ObjectIdentity(mibFile).resolveWithMib(self.mibViewController)
            hint = rowHint = ''
            rowOID = None
            suffix = ()
            rowIndices = {}
            val = None
            thisTableNum = 1

            while True:
                try:
                    oid, label, _ = self.mibViewController.getNextNodeName(oid)
                except error.NoSuchObjectError:
                    break

                if rowOID and not rowOID.isPrefixOf(oid):
                    thisTableNum += 1
                    if automaticValues:
                        if thisTableNum <= tableSize:
                            oid = tuple(rowOID)
                            if self.verboseFlag:
                                sys.stderr.write('# |____|____Synthesizing row #%d of table %s\r\n' % (thisTableNum, rowOID))
                        else:
                            if self.verboseFlag:
                                sys.stderr.write('# |____Finished table %s (%d rows)\r\n' % (rowOID, thisTableNum))
                            rowOID = None
                    else:
                        while True:
                            sys.stderr.write('# Synthesize row #%d for table %s (y/n)? ' % (thisTableNum, rowOID))
                            sys.stderr.flush()
                            line = sys.stdin.readline().strip()
                            if line:
                                if line[0] in ('y', 'Y'):
                                    oid = tuple(rowOID)
                                    break
                                elif line[0] in ('n', 'N'):
                                    if self.verboseFlag:
                                        sys.stderr.write('# |____Finished table %s (%d rows)\r\n' % (rowOID, thisTableNum))
                                    rowOID = None
                                    break

                mibName, symName, _ = self.mibViewController.getNodeLocation(oid)
                if mibName != mibFile:
                    if self.verboseFlag:
                        sys.stderr.write('# + END MIB module: %s\r\n' % mibFile)
                    break

                node, = self.mibBuilder.importSymbols(mibName, symName)
                #mibSymbol.syntax.getSubtypeSpec().getValueMap()

                #if node.label == 'smmTemperatureDescriptionTable': #DEBUG only
                #    skip = False
                #if skip:
                #    continue

                if isinstance(node, MibTable):
                    hint = ''
                    thisTableNum = 1

                    tableSize = random.randrange(2, maxTableSize)
                    oid_str = str(node.name).replace(', ', '.').strip('()')
                    if oid_str in mibJsons:
                        customNode = mibJsons[oid_str]
                        if 'rownum' in customNode:
                            tableSize = customNode['rownum']

                    if self.verboseFlag:
                        sys.stderr.write('# |____ Starting table %s::%s (%s)\r\n' % (mibName, symName, univ.ObjectIdentifier(oid)))
                    continue

                elif isinstance(node, MibTableRow):
                    #rowIndices = {}
                    suffix = ()
                    rowHint = hint + '# |____Row %s::%s\r\n' % (mibName, symName)

                    for impliedFlag, idxModName, idxSymName in node.getIndexNames():
                        idxNode, = self.mibBuilder.importSymbols(idxModName, idxSymName)
                        rowHint += '# |____Index %s::%s (type %s, oid %s)\r\n' % (
                            idxModName, idxSymName, idxNode.syntax.__class__.__name__, idxNode.name)
                        #avoid duplicate
                        existVal = None
                        if idxNode.name in rowIndices:
                            existVal = rowIndices[idxNode.name]
                        rowIndices[idxNode.name] = generateValue(idxNode, thisTableNum)
                        while existVal == rowIndices[idxNode.name]:
                            rowIndices[idxNode.name] = generateValue(idxNode, thisTableNum)

                        suffix = suffix + node.getAsName(rowIndices[idxNode.name], impliedFlag)
                        break #multi-index have bugs

                    if self.verboseFlag and rowOID is None:
                        sys.stderr.write(rowHint)

                    if not rowIndices:
                        if self.verboseFlag:
                            sys.stderr.write('# |____WARNING: %s::%s table has no index!\r\n' % (mibName, symName))

                    #if rowOID is None:
                    #    thisTableNum = 1
                    rowOID = univ.ObjectIdentifier(oid)
                    continue

                elif isinstance(node, MibTableColumn):
                    oid = node.name
                    if oid in rowIndices:
                        val = rowIndices[oid]
                    else:
                        val = generateValue(node, -1)

                elif isinstance(node, MibScalar):
                    hint = ''
                    oid = node.name
                    suffix = (0,)
                    val = generateValue(node, -1)

                # others: MibIdentifier, don't export it
                else:
                    hint = ''
                    continue

                # need to export as <var name>Instance
                instanceKey = str(oid+suffix) + "Instance"
                instance = createVariable(MibScalarInstance, node.name, suffix, node.syntax, val)
                instanceDict = { instanceKey: instance }
                if not instanceKey in self.mibBuilder.mibSymbols[mibFile]:
                    self.mibBuilder.exportSymbols(mibFile, **instanceDict)
                if self.verboseFlag:
                    sys.stderr.write('# |____|____|____Object exported: %s (%s)\r\n' % (node.label, str(oid+suffix)))

                #break


    def init_snmp_engine(self):
        # each SNMP-based application has an engine
        self._snmpEngine = engine.SnmpEngine()

        # config.addTransport(self._snmpEngine, udp.domainName, udp.UdpSocketTransport().openClientMode())
        config.addSocketTransport(self._snmpEngine, udp.domainName,
                                  udp.UdpTransport().openServerMode(('', self.port)))

        # SecurityName <-> CommunityName mapping.
        # config.addV1System(self._snmpEngine, 'my-area', 'public')

        # Allow read MIB access for this user / securityModels at VACM
        # config.addVacmUser(self._snmpEngine, 2, 'my-area', 'noAuthNoPriv', (1, 3, 6))

        # ===== SNMP v2c =====
        # SecurityName <-> CommunityName mapping
        config.addV1System(self._snmpEngine, "public-v1-sec", "public")
        config.addVacmUser(self._snmpEngine, 2, 'public-v1-sec', 'noAuthNoPriv', (1, 3, 6))

        # ===== SNMP v3 support =====
        config.addV3User(self._snmpEngine, 'user1', config.usmHMACMD5AuthProtocol, 'authkey1')
        config.addVacmUser(self._snmpEngine, 3, 'user1', 'authNoPriv', (1, 3, 6))

        # each app has one or more contexts
        self._snmpContext = context.SnmpContext(self._snmpEngine)

    def init_mib_builder(self):
        #the builder is used to load mibs. tell it to look in the
        #current directory for our new MIB. We'll also use it to
        #export our symbols later
        self.mibBuilder = self._snmpContext.getMibInstrum().getMibBuilder()
        mibSources = self.mibBuilder.getMibSources() + (builder.DirMibSource('./mibpy'),)
        self.mibBuilder.setMibSources(*mibSources)

        self.mibViewController = view.MibViewController(self.mibBuilder)

    def serve_forever(self):
        print "SNMP agent started!"

        # tell pysnmp to respotd to get, getnext, and getbulk
        cmdrsp.GetCommandResponder(self._snmpEngine, self._snmpContext)
        cmdrsp.SetCommandResponder(self._snmpEngine, self._snmpContext)
        cmdrsp.NextCommandResponder(self._snmpEngine, self._snmpContext)
        cmdrsp.BulkCommandResponder(self._snmpEngine, self._snmpContext)

        self._snmpEngine.transportDispatcher.jobStarted(1)

        try:
            self._snmpEngine.transportDispatcher.runDispatcher()
        except:
            self._snmpEngine.transportDispatcher.closeDispatcher()
            raise


if __name__ == '__main__':
    sys.stderr.write('Please run hwsim.py to start SNMP simulator!')
    sys.exit(-1)