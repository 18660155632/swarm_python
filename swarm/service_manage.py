#coding:utf-8
import json
import docker
import requests
from tools.shell_cmd import create_process

class ConnDocker:

    def __init__(self,docker_host):
        self.host_url = 'tcp://%s:2375' %(docker_host)
        self.docker_client = docker.DockerClient(base_url = self.host_url)
        self.docker_api_client = docker.APIClient(base_url = self.host_url)
        self.services = self.docker_client.services.list()


    def list_service_id_name(self):
        service_id_name = []
        for service in self.services:
            service_id_name.append({service.id:service.name})
        return service_id_name

    def list_service_attrs(self,service_id = None):
        if service_id is None:
            service_attrs = [{'service_name':x.name,'service_attrs':x.attrs} for x in self.services]
            return service_attrs
        else:
            service = self.docker_client.services.get(service_id)
            service_attrs = {'service_name':service.name,'service_attrs':service.attrs}
            return service_attrs

    def list_tasks(self,service_id):
        service = self.docker_client.services.get(service_id)
        tasks = service.tasks()
        return tasks

    def remove_service(self,service_id):
        service = self.docker_client.services.get(service_id)
        service.remove()
        return service_id

    # def create_service(self,image,command = None,**def_json):
    def create_service(self,def_json):
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
    # print a.list_service_id_name()
    # print a.remove_service('test2')
    # image = 'tomcat:latest'
    ajson = {
        'iamge':'tomcat:latest',
        'options':
            {
            'name':'tomcat8',
            'labels': {'project': 'oms'},
            'networks':['testoverlay'],
            'mode': {
                'mode': 'replicated',
                'replicas':2
            },
            'endpoint_spec': {
                'mode': 'vip',
                'ports': {8898:8080}
            }
        }
    }
    print a.create_service(ajson)
    #print json.dumps([x.attrs for x in a.services])
    # print a.scal_service('tomcat1',new_replicas = 1)
    print json.dumps(a.list_service_attrs('jrvgonrqbg'))
    # print a.list_host_ports()
    # print json.dumps(a.list_tasks('tomcat2'))
