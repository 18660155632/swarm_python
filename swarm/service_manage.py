#coding:utf-8
import json
import docker
import requests
from tools.shell_cmd import create_process

class ConnDocker:

    def __init__(self,docker_host):
        '''
        传入docker swarm manager的地址，初始化一个连接类
        包含DockerClient和APIClient连接
        并且初始化一个services属性，获得属性列表    
        '''
        self.host_url = 'tcp://%s:2375' %(docker_host)
        self.docker_client = docker.DockerClient(base_url = self.host_url)
        self.docker_api_client = docker.APIClient(base_url = self.host_url)
        self.services = self.docker_client.services.list()


    def list_service_id_name(self):
        '''
        列出所有service的id和name，返回一个包含字典元素的列表
        字典样本：{u'g6qisz1kichs4b6n37mbqh1p7': u'tomcat8'}
        其实在操作service的操作中，使用过name和id是等效的，可以只输出其中一种。
        '''
        service_id_name = []
        for service in self.services:
            service_id_name.append({service.id:service.name})
        return service_id_name

    def list_service_attrs(self,service_name = None):
        '''
        获取服务的属性，如果指定具体服务名，则只输出对应的服务属性
        属性样本参考json_tmp/servicce_attrs
        用api和cmd创建的服务，其属性输出格式不一样，本阶段建议不要深度解析
        '''
        if service_name is None:
            service_attrs = [{'service_name':x.name,'service_attrs':x.attrs} for x in self.services]
            return service_attrs
        else:
            service = self.docker_client.services.get(service_name)
            service_attrs = {'service_name':service.name,'service_attrs':service.attrs}
            return service_attrs

    def list_tasks(self,service_id):
        '''
        列出指定service的tasks，可以用service_id也可以用name
        输出是个包含字典的列表，样式参考json_tmp/list_tasks
        '''
        service = self.docker_client.services.get(service_id)
        tasks = service.tasks()
        return tasks

    def remove_service(self,service_id):
        '''
        删除指定service，可以用service_id也可以用name
        '''
        service = self.docker_client.services.get(service_id)
        service.remove()
        return service_id

    # def create_service(self,image,command = None,**def_json):
    def create_service(self,def_json):
        '''
        创建个service，通过字典或者json
        模板参考json_tmp/create_service
        '''
        if isinstance(def_json, dict):
            service_def = def_json
        else:
            service_def = json.loads(def_json)
        image = service_def['iamge']
        if 'command' in service_def.keys():
            command = service_def['command']
        else:
            command = None
        for k,v in service_def['options'].items():
            if k == 'endpoint_spec':
                if v['mode'] == 'dnsrr':
                    en_ports = None
                elif v['mode'] == 'vip':
                    en_ports = v['ports']
                def_endpoint = docker.types.EndpointSpec(mode = v['mode'],ports = en_ports)
                service_def['options'][k] = def_endpoint
            elif k == 'mode':
                if v['mode'] == 'global':
                    mode_replicas = None
                elif v['mode'] == 'replicated':
                    mode_replicas = v['replicas']
                def_mode = docker.types.ServiceMode(v['mode'],replicas = mode_replicas)
                service_def['options'][k] = def_mode
            elif k == 'resources':
                pass
            elif k == 'restart_policy':
                pass
            elif k == 'update_config':
                pass
        try:
            new_service = self.docker_client.services.create(image,command = None,**service_def['options'])
            return new_service
        except:
            return 'service create failed'

    def scal_service(self,service_id,new_replicas = 1):
        '''
        对service扩容，传入service_id或者name，以及扩容后的数量
        因为api执行update有bug，所以直接调用的cmd
        '''
        service = self.docker_client.services.get(service_id)
        if 'Replicated' in service.attrs['Spec']['Mode'].keys():
            scale_cmd = 'docker -H tcp://172.16.1.111:2375 service update --replicas ' + str(
                new_replicas) + ' ' + service_id
            scale_result = create_process(scale_cmd)
            if scale_result[1] == 0:
                return 'scale %s to %d replicas successful' %(service_id,new_replicas)
            else:
                return 'scale failed'
        else:
            return 'global mode,do nothing'

    def list_host_ports(self):
        '''
        列出所有已经使用的端口，仅含swarm环境
        '''
        host_used_ports = []
        def func(my_list):
            b = []
            for c in my_list:
                for d in c:
                    b.append(d)
            return b
        for service in self.services:
            try:
                # ports_info = service.attrs['Spec']['EndpointSpec']['Ports']
                ports_info = service.attrs['Endpoint']['Ports']
                used_ports = [x['PublishedPort'] for x in ports_info]
                host_used_ports.append(used_ports)
            except:
                pass
        return func(host_used_ports)









if __name__ == '__main__':
    host = '172.16.1.111'
    a = ConnDocker(host)
    print json.dumps(a.list_tasks('tomcat7'))
    # print a.list_service_id_name()
    # print a.remove_service('test2')
    # image = 'tomcat:latest'
    # ajson = {
    #     'iamge':'tomcat:latest',
    #     'options':
    #         {
    #         'name':'tomcat8',
    #         'labels': {'project': 'oms'},
    #         'networks':['testoverlay'],
    #         'mode': {
    #             'mode': 'replicated',
    #             'replicas':2
    #         },
    #         'endpoint_spec': {
    #             'mode': 'vip',
    #             'ports': {8898:8080}
    #         }
    #     }
    # }
    # print a.create_service(ajson)
    # #print json.dumps([x.attrs for x in a.services])
    # # print a.scal_service('tomcat1',new_replicas = 1)
    # print json.dumps(a.list_service_attrs('jrvgonrqbg'))
    # # print a.list_host_ports()
    # # print json.dumps(a.list_tasks('tomcat2'))
