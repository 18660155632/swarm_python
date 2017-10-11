#coding:utf-8
from swarm_manage import ConnDocker
import json

host = '172.16.1.111'
swarm_conn = ConnDocker(host)

def get_service_info(role = None,):
    '''
    某用户登录后，根据其所属角色，列出此角色创建的所有服务、任务的详细信息
    传入参数为角色名role，如果是admin用户，role = None
    如果是非admin用户，输出是一个字典。
    如果是admin用户，输出的是一个列表。列表的元素是各个非admin用户的字典。
    字典样本参考json_tmp/role_service_task
    '''
    if role != None:
        my_services_names = swarm_conn.list_service_name_role(role).values()[0]
        service_task_info = []
        for service_name in my_services_names:
            service_attrs = swarm_conn.list_service_attrs(service_name)
            tasks_attrs = swarm_conn.list_tasks(service_name)
            endpoint_port = [x['PublishedPort'] for x in service_attrs['service_attrs']['Endpoint']['Ports']]
            service_image = service_attrs['service_attrs']['Spec']['TaskTemplate']['ContainerSpec']['Image']
            task_info = [{'task_id':x['ID'],'container_id':x['Status']['ContainerStatus']['ContainerID'],
                          'node_name':swarm_conn.node_id_2_name(x['NodeID']),'status':x['Status']['State']} for x in tasks_attrs]
            service_task_info.append({'service_name':service_name,'endpoint_port':endpoint_port,'image':service_image,
                                      'task_info':task_info})
        return {role:service_task_info}

    else:
        all_info = []
        return [get_service_info(y) for y in swarm_conn.list_service_name_role().keys()]

def remove_service(service_name):
    '''
    不解释:)
    '''
    swarm_conn.remove_service(service_name)

def scale_service(service_name,new_replicas = 1):
    '''
    不解释:)
    '''
    swarm_conn.scal_service(service_name,new_replicas)

def list_service_all_attrs(service_name):
    '''
    不解释:)
    '''
    swarm_conn.list_service_attrs(service_name)

def list_service_task_attrs(service_name):
    '''
    不解释:)
    '''
    swarm_conn.list_tasks(service_name)


if __name__ == '__main__':
     # a = get_service_info()
     a = get_service_info('oms')
     print json.dumps(a)
     # b = scale_service('tomcat1',5)
     # print json.dumps(a)
