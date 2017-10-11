from swarm_manage import ConnDocker
import json

host = '172.16.1.111'
swarm_conn = ConnDocker(host)

def get_service_info(role = None,):
    if role != None:
        my_services_names = swarm_conn.list_service_name_role(role).values()[0]
        service_task_info = []
        for service_name in my_services_names:
            service_attrs = swarm_conn.list_service_attrs(service_name)
            tasks_attrs = swarm_conn.list_tasks(service_name)
            endpoint_port = [x['PublishedPort'] for x in service_attrs['service_attrs']['Endpoint']['Ports']]
            service_image = service_attrs['service_attrs']['Spec']['TaskTemplate']['ContainerSpec']['Image']
            task_info = [{'task_id':x['ID'],'container_id':x['Status']['ContainerStatus']['ContainerID'],
                          'node_id':x['NodeID'],'status':x['Status']['State']} for x in tasks_attrs]
            service_task_info.append({'service_name':service_name,'endpoint_port':endpoint_port,'image':service_image,
                                      'task_info':task_info})
        return {role:service_task_info}

    else:
        all_info = []
        return [get_service_info(y) for y in swarm_conn.list_service_name_role().keys()]

def remove_service(service_name):
    swarm_conn.remove_service(service_name)

def scale_service(service_name,new_replicas = 1):
    swarm_conn.scal_service(service_name,new_replicas)


if __name__ == '__main__':
     # a = get_service_info()
     a = get_service_info('oms')
     print json.dumps(a)
     b = scale_service('tomcat1',5)
     print json.dumps(a)
