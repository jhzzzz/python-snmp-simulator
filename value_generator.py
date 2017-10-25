"""
This file is part of SNMP agent simulator,
which used for simulate HUAWEI server iBMC/HMM SNMP interfaces.

author: Jack Zhang
crated: 2017/4/7
"""

import sys
import random
import json
from pyasn1.type import univ
from pyasn1.error import PyAsn1Error
from pysnmp.proto import rfc1902

stringPool = 'Love is a flower that lives on the cliff You can pick up the flower with nothing but your courage and adventurousness'.split()
counterRange = (0, 0xffffffff)
counter64Range = (0, 0xffffffffffffffff)
gaugeRange = (0, 0xffffffff)
timeticksRange = (0, 0xffffffff)
unsignedRange = (0, 65535)
int32Range = (0, 100)  # these values are more likely to fit constraints
automaticValues = 5000
mibJsons = {} #used for hold all custom special values


def loadMibJson(mibFile):
    jsonFile = 'mibjson/' + mibFile + '.json'
    with open(jsonFile) as jsonData:
        jsonObject = json.load(jsonData)
        for key, obj in jsonObject.iteritems():
            if key == 'imports' or key == 'meta':
                continue
            if not 'oid' in obj:
                continue;

            mibJsons[obj['oid']] = obj
    jsonData.close()

def generateCustomValue(node):
    oid = str(node.name).replace(', ', '.').strip('()')
    if not oid in mibJsons:
        oid = oid[:oid.rfind(".")]
    if not oid in mibJsons:
        return None

    customNode = mibJsons[oid]
    if not 'syntax' in customNode:
        return None
    if not 'constraints' in customNode['syntax']:
        return None

    constraints = customNode['syntax']['constraints']
    if 'enumeration' in constraints:
        count = len(constraints['enumeration'])
        if count > 1:
            return constraints['enumeration'].values()[random.randrange(0, count)]

    elif 'range' in constraints:
        ranges = constraints['range']
        if len(ranges) > 0:
            min = 0
            max = 100
            if 'min' in ranges[0]:
                min = ranges[0]['min']
            if 'max' in ranges[0]:
                max = ranges[0]['max']
            return random.randrange(min, max+1)

    return None

def generateValue(node, rowNum):
    syntax = node.syntax

    # first try to generate a accurate value according json settings
    val = generateCustomValue(node)
    try:
        if val is not None:
            return syntax.clone(val)
    except PyAsn1Error:
        pass

    makeGuess = automaticValues
    while True:
        if makeGuess:
            # Pick a value
            if isinstance(syntax, rfc1902.IpAddress):
                val = '.'.join([str(random.randrange(1, 256)) for x in range(4)])
            elif isinstance(syntax, rfc1902.TimeTicks):
                val = random.randrange(timeticksRange[0], timeticksRange[1])
            elif isinstance(syntax, rfc1902.Gauge32):
                val = random.randrange(gaugeRange[0], gaugeRange[1])
            elif isinstance(syntax, rfc1902.Counter32):
                val = random.randrange(counterRange[0], counterRange[1])
            elif isinstance(syntax, rfc1902.Integer32):
                if rowNum > -1: #for integer, table row index
                    val = rowNum
                else:
                    val = random.randrange(int32Range[0], int32Range[1])
            elif isinstance(syntax, rfc1902.Unsigned32):
                val = random.randrange(unsignedRange[0], unsignedRange[1])
            elif isinstance(syntax, rfc1902.Counter64):
                val = random.randrange(counter64Range[0], counter64Range[1])
            elif isinstance(syntax, univ.OctetString):
                maxWords = 2 if rowNum > -1 else 10
                val = ' '.join([stringPool[random.randrange(0, len(stringPool))] for i in range(random.randrange(1, maxWords))])
            elif isinstance(syntax, univ.ObjectIdentifier):
                val = '.'.join(['1', '3', '6', '1', '3'] + [
                    '%d' % random.randrange(0, 255) for x in range(random.randrange(0, 10))])
            elif isinstance(syntax, rfc1902.Bits):
                val = [random.randrange(0, 256) for x in range(random.randrange(0, 9))]
            else:
                val = '?'

        try:
            if val is not None:
                return syntax.clone(val)
        except PyAsn1Error:
            if makeGuess == 1:
                sys.stderr.write(
                    '*** Inconsistent value: %s\r\n*** See constraints and suggest a better one for:\r\n' % (
                        sys.exc_info()[1],)
                )
            if makeGuess:
                makeGuess -= 1
                continue

        sys.stderr.write('%s# Value [\'%s\'] ? ' % (node.name, (val is None and '<none>' or val),))
        sys.stderr.flush()

        line = sys.stdin.readline().strip()
        if line:
            if line[:2] == '0x':
                if line[:4] == '0x0x':
                    line = line[2:]
                elif isinstance(syntax, univ.OctetString):
                    val = syntax.clone(hexValue=line[2:])
                else:
                    val = int(line[2:], 16)
            else:
                val = line


"""
This class is used for generate SNMP object values,
the value generation is dynamic, we'll first check constraints,
then generate value according the object type.
"""
def createVariable(SuperClass, typeName, instId, syntax, val):

    class ScalarInstance(SuperClass):
        def readGet(self, name, *args):
            oid = str(self.name).replace(', ', '.').strip('()')
            if not oid in mibJsons:
                oid = oid[:oid.rfind(".")]
            if oid in mibJsons:
                customNode = mibJsons[oid]
                if 'syntax' in customNode:
                    if ("dynamic" in customNode['syntax']) and (customNode['syntax']['dynamic'] == 1):
                        return name, self.getValue()

            if val is not None:
                return name, val
            else:
                return name, self.getValue()

        # getValue is a function to call to retreive the value of the scalar
        def getValue(self):
            return generateValue(self, -1)

    return ScalarInstance(typeName, instId, syntax)


if __name__ == '__main__':
    sys.stderr.write('Please run hwsim.py to start SNMP simulator!')
    sys.exit(-1)