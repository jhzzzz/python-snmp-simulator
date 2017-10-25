#python_snmp_simulator

python SNMP protocol simulator.
python SNMP 协议模拟器，可基于任意 MIB 库文件进行设备的模拟，并可对模拟输出的数值进行定义，比如CPU负载动态数值，详情请参考下面的使用说明。

## 使用说明

------
### 一、环境安装

注：以下以CentOS7.0为例进行安装，如果是其他版本Linux，步骤基本相似，Python请先升级至2.7。

安装 pip
> \# curl -O https://bootstrap.pypa.io/get-pip.py
> \# python get-pip.py

安装依赖包
> \# yum install gcc #依赖gcc编译
> \# yum install python-devel
> \# pip install pysnmp

pysnmp 默认安装 pysmi 依赖库有些bug，我们卸载掉，并用最新的重新安装：

> \# pip uninstall pysmi
> \# unzip ./packages/pysmi-master.zip
> \# python setup.py install

### 二、导入MIB库

假设现在拿到一个MIB库文件：HUAWEI-SERVER-iBMC-MIB.mib
> \# mibdump.py --destination-format=json --destination-directory=./mibjson ./HUAWEI-SERVER-iBMC-MIB.mib

看到类似于下面的结果，说明一切正常，相关的json文件应该已经生成了，存储在./mibjson 目录下：
> 
Created/updated MIBs: HUAWEI-SERVER-IBMC-MIB, SNMP-FRAMEWORK-MIB
Pre-compiled MIBs borrowed: 
Up to date MIBs: RFC-1212, RFC1155-SMI, RFC1158-MIB, RFC1213-MIB, SNMPv2-CONF, SNMPv2-SMI, SNMPv2-TC
Missing source MIBs: 
Ignored MIBs: 
Failed MIBs: 

再运行一次，换个参数生成 .py 文件：
> \# mibdump.py --destination-directory=./mibpy ./HUAWEI-SERVER-iBMC-MIB.mib

这样我们需要的文件基本都已经有了，模拟器支持动态生成数值，比如CPU 使用率，系统负载等，我们希望每次是不一样的数值。
如果需要此功能，我们可以打开 json 文件手工进行编辑，下面以 1.3.6.1.4.1.2011.2.235.1.1.20.4 （powerConsumption）为例，此处主要有两个地方，首先，设置"dynamic": 1指定此数字每次动态生成，其次设置constraints range指定数据范围（可选）：

    "powerConsumption": {
    "name": "powerConsumption", 
    "oid": "1.3.6.1.4.1.2011.2.235.1.1.20.4", 
    "class": "objecttype", 
    "syntax": {
      "constraints": {
        "range": [
          {
            "min": 0, 
            "max": 100
          }
        ]
      },    
      "type": "DisplayString", 
      "class": "type",
      "dynamic": 1
    }

### 三、模拟器使用

模拟器运行非常简单：

> \# python snmpsim.py -d [MIB 库名称即可]
如：
> \# python snmpsim.py HUAWEI-SERVER-IBMC-MIB 

