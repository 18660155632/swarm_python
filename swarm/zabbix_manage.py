#coding:utf-8
import requests
import Queue
from  swarm_manage import ConnDocker
import tools.shell_cmd
import tools.m_thread
import protobix

class ConnZbx:

    def __init__(self,zbx_url,zbx_token,swarm_host = '172.16.1.111'):
        self.file_get_HG = 'zabbix_api/get_HG.json'
        self.file_create_HG = 'zabbix_api/create_HG.json'
        self.file_delete_HG = 'zabbix_api/delete_HG.json'
        self.file_get_hosts = 'zabbix_api/get_host.json'
        self.file_create_host = 'zabbix_api/create_host.json'
        self.file_delete_host = 'zabbix_api/delete_host.json'
        self.file_get_template = 'zabbix_api/get_template.json'

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

    def get_template(self,templat_name = 'docker',one_key = 'templateid'):
        # 默认所有容器在zabbix中使用docker模板，模板需提前创建
        # 此方法获取docker模板的模板ID，创建主机时会用到
        data = self.deal_with_api(self.file_get_template,templat_name)
        r = requests.post(self.zbx_url, headers = self.headers, data = data)
        return r.json()['result'][0][one_key]
        # return r.json()['result'][0]

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
        # 通过获取swarm service的task属性，找到属于这个service的docker容器ID，这个ID可以作为zabbix的主机名
        # 因为创建zabbix主机的时候需要指定主机组（使用组ID），索性将这个容器ID（zabbix主机名）和zabbix组ID组成一个字典
        containers = []
        for service in self.get_all_services().values():
            tasks = self.swarm_conn.list_tasks(service)
            containers += {x['Status']['ContainerStatus']['ContainerID'][:12]:self.get_all_HGs()[service]
                               for x in tasks
                               if x['Status']['State'] == 'running'
                          }.items()
        self.all_containers = dict(containers)
        return self.all_containers

    def get_all_hosts(self):
        # 从zabbix中获取当前存在的所有zabbix主机，结果为主机名：主机ID的字典
        # 主机名为了与容器名（ID）关联，主机ID用于zabbix的操作
        data = self.deal_with_api(self.file_get_hosts)
        r = requests.post(self.zbx_url, headers = self.headers, data = data)
        host_name_id = {x['host']:x['hostid'] for x in r.json()['result']}
        # print host_name_id
        return host_name_id

    def create_host(self):
        # 当前所有容器 - 当前所有zbx主机 = 需要创建的容器
        # 以此结果创建容器,使用主机名，主机组ID，docker模板ID做参数
        self.get_all_containers()
        result = []
        create_hosts = set(self.all_containers.keys()) - set(self.get_all_hosts().keys())
        if len(create_hosts) !=0:
            for host in create_hosts:
                data = self.deal_with_api(self.file_create_host,host,self.all_containers[host],self.get_template())
                r = requests.post(self.zbx_url, headers = self.headers, data = data)
                result.append(r.json())
            return result

    def delete_host(self):
        # 当前所有zbx主机 - 当前所有容器 - 保留的主机 = 需要删除的主机
        # 通过主机ID删除主机
        result = []
        delete_hosts = set(self.get_all_hosts().keys()) - set(self.all_containers) - set(self.reserv_hosts)
        if len(delete_hosts) != 0:
            for host in delete_hosts:
                hostid = self.get_all_hosts()[host]
                data = self.deal_with_api(self.file_delete_host,hostid)
                r = requests.post(self.zbx_url,headers = self.headers,data = data)
                result.append(r.json())
            return result


    '''
    执行顺序：创建组、创建主机、删除主机、删除组
    '''
    def mgr_zbx(self):
        create_HGs = self.create_HG()
        create_hosts = self.create_host()
        delete_hosts = self.delete_host()
        delete_HGs = self.delete_HG()
        return create_HGs,create_hosts,delete_hosts,delete_HGs


    '''
    在worker节点获取数据
    '''
    def get_nodes_ip(self,host_role = 'worker'):
        '''
        获得节点IP，默认是worker节点的
        '''
        if host_role in ['worker','manager']:
            filters = {'role':host_role}
        else:
            print 'no role'
        nodes = self.swarm_conn.list_nodes(filters = filters)
        for node in nodes:
            # print node.attrs
            node_ip = node.attrs['Status']['Addr']
            yield node_ip

    def get_worker_datas(self,worker_host):
        '''
        获得某个worker节点的监控数据，这里调用docker stats命令，没有用相关api，因为api获得的数据还要进行计算……不擅长计算
        docker stats命令执行稍慢，2-5秒，如果节点很多，有必要在线程中同时执行
        '''
        agent_cmd = 'docker -H tcp://%s:2375  stats --no-stream' %(worker_host)
        get_stats = tools.shell_cmd.create_process(agent_cmd)[0]
        return get_stats.split('\n')[1:]

    def get_all_workers_datas(self):
        '''
        使用多线程同时连接到所有worker节点，获得监控数据，把监控数据发送到队列中
        待所有线程都执行完毕，收集所有监控数据进行简单处理
        '''
        q = Queue.Queue()
        thread_objects = []
        datas = []
        # 定义一个子函数，获取某个worker节点数据并发到队列
        def in_thread(ip):
            a_thread = self.get_worker_datas(ip)
            q.put(a_thread)
        # 循环在线程中执行上面的子函数
        for node_ip in self.get_nodes_ip():
            a = tools.m_thread.do_in_thread(in_thread,node_ip)
            thread_objects.append(a)
        for thread_object in thread_objects:
            thread_object.join()
        # 所有线程执行完毕后，读取队列中数据，直到队列为空
        while not q.empty():
            datas += q.get()
        return [x for x in datas if x != '']

    def deal_with_datas(self):
        '''
        将worker上的监控数据处理成zabbix sender协议要求的格式
        '''
        datas = self.get_all_workers_datas()
        zbx_sender_datas = {}
        for data in datas:
            _ = data.split()
            # print _
            host_name = _[0]
            cpu_p = _[1].split("%")[0]
            if _[3] == 'MiB':
                mem_u = _[2]
            elif _[3] == 'GiB':
                mem_u = float(_[2]) * 1024
            mem_t = _[5]
            mem_p = _[7].split("%")[0]
            zbx_sender_data = {host_name:{"CPU_P":float(cpu_p),"MEM_U":float(mem_u),"MEM_T":float(mem_t),"MEM_P":float(mem_p)}}
            zbx_sender_datas.update(zbx_sender_data)
        return zbx_sender_datas



if __name__ == '__main__':


