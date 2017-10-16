#coding:utf-8
from zabbix_manage import ConnZbx
import protobix
'''
注意protobix不要用pip install安装，版本差太大
github地址:https://github.com/jbfavre/python-zabbix
'''

zbx_server = '172.16.3.62'
zbx_token = '8bac858cfe416fc69df82d5aa4957788'
zbx_url = 'http://%s/zabbix/api_jsonrpc.php' %(zbx_server)
zbx_conn = ConnZbx(zbx_url, zbx_token)

'''
按照创建hostgroup、创建hosts、删除hosts、删除hostgroup的顺序同步
swarm中service、container的状态到zabbix,建议每分钟执行一次
'''
zbx_conn.mgr_zbx()

'''
通过导入的protobix使用zabbix sender协议发送数据
数据采集和发送,测试环境耗时2~5S,建议30~60秒执行一次
'''

data = zbx_conn.deal_with_datas()
zbx_container = protobix.DataContainer("items",zbx_server,10051)
zbx_container.add(data)
ret = zbx_container.send(zbx_container)
if not ret:
    print "Ooops. Something went wrong when sending data to Zabbix"


