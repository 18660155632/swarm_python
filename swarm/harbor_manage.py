#coding:utf-8
import json
import docker
import requests


class ConnHabor:

    '''
    初始化一个harbor连接实例
    传递参数为harbot主机IP，harbor用户名和密码，以及处理镜像的机器IP
    '''
    def __init__(self,harbor_host,harbor_user,harbor_password,image_host):
        self.harbor_host_baseapi = 'http://%s/api' %(harbor_host)
        self.harbor_host = harbor_host
        self.harbor_user = harbor_user
        self.harbor_password = harbor_password
        self.image_host_url = 'tcp://%s:2375' % (image_host)
        self.docker_api_client = docker.APIClient(base_url=self.image_host_url)
        self.docker_client = docker.DockerClient(base_url=self.image_host_url)
        self.harbor_session = requests.Session()
        self.harbor_session.auth = (self.harbor_user,self.harbor_password)

    '''
    hub_2_harbor
    用来将docker hub的镜像pull到本地，并push到私有库
    方法接收参数为一个json，json模板参考.json_tmp/hub_2_harbor;为了避免json和字典的频繁转换，也可传递同内容的字典，程序会自己判断
    hub_2_harbor调用4个方法，分别用来pull、tag、push、check
    操作成功将返回True;不成功将返回原因
    '''
    def hub_2_harbor(self,a_json):

        if isinstance(a_json, dict):
            hub_2_harbor_def = a_json
        else:
            hub_2_harbor_def = json.loads(a_json)
        hub_repo_name = hub_2_harbor_def['dockerhub']['project_repo']
        hub_tag = hub_2_harbor_def['dockerhub']['tag']
        harbor_host = self.harbor_host
        harbor_project = hub_2_harbor_def['harbor']['harbor_project']
        harbor_repo = hub_2_harbor_def['harbor']['harbor_repo']
        harbor_tag = hub_2_harbor_def['harbor']['harbor_tag']
        harbor_project_repo = '%s:80/%s/%s' % (harbor_host, harbor_project, harbor_repo)

        pulled_image_id = self.hub_pull(hub_repo_name, hub_tag)
        if pulled_image_id is not False:
            self.hub_tag(pulled_image_id, harbor_project_repo, harbor_tag)
            pushed_image = self.harbor_push(harbor_project_repo, harbor_tag)
            check_repo_name = '%s/%s' % (harbor_project, harbor_repo)
            if self.harbor_check(check_repo_name,harbor_tag) == 200:
                return True
            else:
                return pushed_image
        else:
            return 'image can not be pulled'

    def hub_pull(self,hub_repo_name,hub_tag):
        # 接收repo_name和tag
        # pull镜像，成功返回镜像的ID，不成功返回False
        try:
            pull_image = self.docker_client.images.pull(hub_repo_name, hub_tag)
            pull_result = pull_image.attrs
            return pull_result['Id'].split(':')[1]

        except docker.errors.APIError:
            pull_result = False
            return pull_result

    def hub_tag(self,image_id,harbor_project_repo,harbor_tag):
        # 接收镜像ID，完整的repo信息，如"IP:PORT/project/repo"和tag
        # 对镜像打标签
        self.docker_api_client.tag(image_id,harbor_project_repo,harbor_tag)
        tag_result = '%s:%s' %(harbor_project_repo,harbor_tag)
        return tag_result

    def harbor_push(self,repo_name,tag):
        # push镜像到harbor，返回push结果，push结果是没有固定格式的str
        harbor_auth = {'username': self.harbor_user, 'password': self.harbor_password}
        pushed_result = self.docker_client.images.push(repo_name, tag, auth_config=harbor_auth)
        return pushed_result

    def harbor_check(self, repo_name, tag):
        # 因为push的返回值是没有固定格式的str，push成功与否只能到harbor上去验证
        # 验证成功会返回镜像的属性，不成功返回错误
        check_url = '%s/repositories/%s/tags/%s' %(self.harbor_host_baseapi,repo_name,tag)
        request = self.harbor_session.get(check_url)
        return request.status_code


    def harbor_list_projects(self, project_key='project_id'):
        # 获得项目名的列表，并且根据project_key（默认project_id）得到相应的属性，
        # 返回类似：[{u'k8s': 2}, {u'library': 1}]
        # project_result = []
        # list_project_url = '%s/projects' % (self.harbor_host_baseapi)
        # request = self.harbor_session.get(list_project_url)
        # harbor_projects = request.json()
        # for project in harbor_projects:
        #     project_result.append({project['name']: project[project_key]})
        # return project_result
        project_result = {}
        list_project_url = '%s/projects' %(self.harbor_host_baseapi)
        request = self.harbor_session.get(list_project_url)
        harbor_projects = request.json()
        for project in harbor_projects:
            project_result[project['name']] = project[project_key]
        return project_result

    def harbor_list_repos(self,project_id,repo_key = 'name'):
        #获得指定project_id项目的repo列表，根据repo_key（默认name）得到相应属性
        #默认返回类似：["k8s/pause-amd64", "k8s/nginx", "k8s/k8s-dns-sidecar-amd64"]
        repo_result = []
        list_repo_url = '%s/repositories' %(self.harbor_host_baseapi)
        payload = {'project_id':project_id}
        request = self.harbor_session.get(list_repo_url,params = payload)
        harbor_repos = request.json()
        for repo in harbor_repos:
            repo_result.append(repo[repo_key])
        return repo_result

    def harbor_list_tags(self,repo_name,tag_key = 'name'):
        # 获得指定repo项目的tag列表，根据repo_key（默认name）得到相应属性
        # 默认返回类似：["1.10", "1.11", "1.12", "latest"]
        tag_result = []
        list_tag_url = '%s/repositories/%s/tags' %(self.harbor_host_baseapi,repo_name)
        request = self.harbor_session.get(list_tag_url)
        harbor_tags = request.json()
        for tag in harbor_tags:
            tag_result.append(tag[tag_key])
        return tag_result

    def harbor_del_tag(self,repo_name,tag):
        del_tag_url = '%s/repositories/%s/tags/%s' %(self.harbor_host_baseapi,repo_name,tag)
        request = self.harbor_session.delete(del_tag_url)
        return request.status_code

    def harbor_del_repo(self,repo_name):
        del_repo_url = '%s/repositories/%s' %(self.harbor_host_baseapi,repo_name)
        request = self.harbor_session.delete(del_repo_url)
        return request.status_code


    def harbor_get_volumes_info(self):
        get_volumes_info_url = '%s/systeminfo/volumes' %(self.harbor_host_baseapi)
        request = self.harbor_session.get(get_volumes_info_url)
        return request.json()

    def harbor_get_system_info(self):
        get_system_info_url = '%s/systeminfo' %(self.harbor_host_baseapi)
        request = self.harbor_session.get(get_system_info_url)
        return request.json()


if __name__ == '__main__':
    host = '172.16.3.61'
    user = 'admin'
    password = 'Harbor12345'
    image_host = '172.16.1.111'

    a = ConnHabor(host,user,password,image_host)
    # a.harbor_del_tag()

    a_json = {
        "dockerhub": {
            "project_repo": "centos",
            "tag": "6"
        },
        "harbor": {
            "harbor_host": "172.16.3.61",
            "harbor_project": "k8s",
            "harbor_repo": "centos",
            "harbor_tag": "6"
        }

    }


    print a.hub_2_harbor(a_json)
    # print a.harbor_list_projects()
    # print a.harbor_list_repos(2)
    # print a.harbor_list_tags('k8s/centos')
    # print a.harbor_del_tag('k8s/centos','6')
    # print a.harbor_list_tags('k8s/ubuntu')
    # print a.harbor_get_volumes_info()
    # print a.harbor_get_system_info()
    # print a.harbor_del_repo('library/centos')
