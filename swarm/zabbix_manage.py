#coding:utf-8
import json
import docker
import requests
from  swarm_manage import ConnDocker
import time

class ConnZbx:

    def __init__(self,zbx_url,zbx_token,swarm_host = '172.16.1.111'):
        self.file_get_HG = 'zabbix_api/get_HG.json'
        self.file_create_HG = 'zabbix_api/create_HG.json'
        self.file_delete_HG = 'zabbix_api/delete_HG.json'
        self.file_get_hosts = 'zabbix_api/get_host.json'
        self.file_create_host = 'zabbix_api/create_host.json'
        self.file_delete_host = 'zabbix_api/delete_host.json'

        self.zbx_url = zbx_url
        self.zbx_token = zbx_token
        self.swarm_conn = ConnDocker(swarm_host)
        self.headers = {'Content-Type':'application/json'}

        self.reserve_HGs = ['Templates','Linux servers','Zabbix servers','Discovered hosts',
                           'Virtual machines','Hypervisors']
        self.reserv_hosts = ['Zabbix server']


    def deal_with_api(self,json_file, *args):
        with open(json_file) as f:
            data_t = f.readlines()[0]
            replace_str = (self.zbx_token,) + args
            data = data_t % replace_str
            return data

    '''
    下面代码用于自动对比swarm中的service和zabbix的host group，并根据对比结果在zabbix中创建、删除host group
    '''
    def get_all_services(self):
        # 获得swarm中所有的服务名
        return self.swarm_conn.list_service_id_name()

    def get_all_HGs(self):
        # 获得zabbix中的所有host group，并以group name：group id的形式组成字典（因为删除组的时候要用到组ID）
        data = self.deal_with_api(self.file_get_HG)
        r = requests.get(self.zbx_url, headers = self.headers, data = data)
        HGs_name_id = {x['name']:x['groupid'] for x in r.json()['result']}
        return HGs_name_id

    def create_HG(self):
        # 找出不在zabbix组中的swarm服务名，并以此创建zabbix组
        result = []
        create_HGs = set(self.get_all_services().values()) - set(self.get_all_HGs().keys())
        if len(create_HGs) != 0:
            for HG in create_HGs:
                data = self.deal_with_api(self.file_create_HG,HG)
                r = requests.post(self.zbx_url, headers = self.headers, data = data)
                result.append(r.json())
            return result

    def delete_HG(self):
        # 找出swarm中已删除但zabbix中还存在的组，在zabbix中删除
        result = []
        delete_HGs = set(self.get_all_HGs().keys()) - set(self.get_all_services().values()) - set(self.reserve_HGs)
        if len(delete_HGs) != 0:
            for HG in delete_HGs:
                HG_id = self.get_all_HGs()[HG]
                data = self.deal_with_api(self.file_delete_HG, HG_id)
                r = requests.post(self.zbx_url, headers = self.headers, data = data)
                result.append(r.json())
            return result


    '''
    下面的代码用于对比swarm中的容器和zabbix中的host，并根据对比结果创建或删除zabbix host
    '''

    def get_all_containers(self):
        # self.create_HG()
        containers = []
        for service in self.get_all_services().values():
            tasks = self.swarm_conn.list_tasks(service)
            containers += {x['Status']['ContainerStatus']['ContainerID'][:12]:self.get_all_HGs()[service]
                               for x in tasks}.items()
        self.all_containers = dict(containers)
        return self.all_containers

    def get_all_hosts(self):
        data = self.deal_with_api(self.file_get_hosts)
        r = requests.post(self.zbx_url, headers = self.headers, data = data)
        host_name_id = {x['host']:x['hostid'] for x in r.json()['result']}
        # print host_name_id
        return host_name_id

    def create_host(self):
        self.get_all_containers()
        result = []
        create_hosts = set(self.all_containers.keys()) - set(self.get_all_hosts().keys())
        if len(create_hosts) !=0:
            for host in create_hosts:
                data = self.deal_with_api(self.file_create_host,host,self.all_containers[host])
                r = requests.post(self.zbx_url, headers = self.headers, data = data)
                result.append(r.json())
            return result

    def delete_host(self):
        result = []
        delete_hosts = set(self.get_all_hosts().keys()) - set(self.all_containers) - set(self.reserv_hosts)
        if len(delete_hosts) != 0:
            for host in delete_hosts:
                hostid = self.get_all_hosts()[host]
                data = self.deal_with_api(self.file_delete_host,hostid)
                r = requests.post(self.zbx_url,headers = self.headers,data = data)
                result.append(r.json())
            return result

    def mgr_zbx(self):
        create_HGs = self.create_HG()
        create_hosts = self.create_host()
        delete_hosts = self.delete_host()
        delete_HGs = self.delete_HG()
        return create_HGs,create_hosts,delete_hosts,delete_HGs








if __name__ == '__main__':
    zbx_token = '8bac858cfe416fc69df82d5aa4957788'
    zbx_url = 'http://172.16.3.62/zabbix/api_jsonrpc.php'
    a = ConnZbx(zbx_url,zbx_token)
    print a.mgr_zbx()
    # print a.delete_host()
    # print a.create_host()
    # print a.all_containers
    # print a.all_services
    # print a.get_all_hosts()
    # print a.all_services

    # print a.headers
    # print a.mgr_zbx_HG()
    # # time.sleep(10)
    # print a.mgr_zbx_hosts()
    # headers = {'Content-Type':'application/json'}
    # with open('zabbix_api/get_token.json') as f:
    #     data = f.readlines()[0]
    # r = requests.post(zbx_url, headers = headers, data = data)
    # # # r = requests.post(zbx_url)
    # # print r.headers
    # print r.status_code
    # print r.json()
