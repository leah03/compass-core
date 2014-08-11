#!/usr/bin/python
#
# Copyright 2014 Huawei Technologies Co. Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

__author__ = "Grace Yu (grace.yu@huawei.com)"


"""Test Chef installer functionalities regarding to chef server side.
"""

from copy import deepcopy
from mock import Mock
import os
import unittest2


os.environ['COMPASS_IGNORE_SETTING'] = 'true'

from compass.tests.deployment.test_data import config_data
from compass.utils import setting_wrapper as compass_setting
reload(compass_setting)


from compass.deployment.installers.pk_installers.chef_installer.chef_installer\
    import ChefInstaller


class TestChefInstaller(unittest2.TestCase):
    """Test installer functionality."""
    def setUp(self):
        super(TestChefInstaller, self).setUp()
        self.dist_sys_name = 'openstack_icehouse'
        self.chef_test_api = self._get_testchefapi()
        self.test_chef = self._get_chef_installer()
        self.objects = []

    def tearDown(self):
        import chef
        super(TestChefInstaller, self).tearDown()
        databag_names = self.test_chef.config_manager.get_chef_databag_names()
        del self.test_chef
        for obj in self.objects:
            try:
                obj.delete()
            except chef.exceptions.ChefError as ex:
                print ex

        for name in databag_names:
            temp = chef.DataBag(name, self.chef_test_api)
            if temp in chef.DataBag.list(api=self.chef_test_api):
                temp.delete()
        del self.chef_test_api

    def _get_testchefapi(self):
        import chef
        url = 'https://api.opscode.com/organizations/compasscheftest'
        return chef.ChefAPI(url, config_data.test_client_key, 'graceyu')

    def _register(self, obj):
        self.objects.append(obj)

    def _get_chef_installer(self):
        adapter_info = deepcopy(config_data.adapter_test_config)
        cluster_info = deepcopy(config_data.cluster_test_config)
        hosts_info = deepcopy(config_data.hosts_test_config)

        ChefInstaller.get_tmpl_path = Mock()
        test_tmpl_dir = os.path.join(os.path.join(config_data.test_tmpl_dir,
                                                  'chef_installer'),
                                     'openstack_icehouse')
        ChefInstaller.get_tmpl_path.return_value = test_tmpl_dir

        ChefInstaller._get_chef_api = Mock()
        ChefInstaller._get_chef_api.return_value = self.chef_test_api
        chef_installer = ChefInstaller(adapter_info, cluster_info, hosts_info)
        return chef_installer

    def test_update_node(self):
        import chef
        host_id = 2
        self.dist_sys_name = 'openstack_icehouse'
        cluster_name = self.test_chef.config_manager.get_clustername()
        node_name = self.test_chef.config_manager.get_host_fullname(host_id)
        roles = ['os-compute']
        env_name = self.test_chef.get_env_name(self.dist_sys_name,
                                               cluster_name)

        test_node = self.test_chef.get_node(node_name, env_name)
        self.assertIsNotNone(test_node)
        self._register(test_node)

        cluster_dict = self.test_chef._get_cluster_tmpl_vars()
        vars_dict = self.test_chef._get_host_tmpl_vars(host_id, cluster_dict)

        self.test_chef.update_node(test_node, roles, vars_dict)

        result_node = chef.Node(node_name, self.chef_test_api)

        self.assertListEqual(result_node.run_list, ['role[os-compute]'])
        self.assertEqual(result_node.chef_environment, env_name)
        expected_node_attr = {
            "override_attributes": {
                "endpoints": {
                    "compute-vnc-bind": {
                        "host": "12.234.32.101"
                    }
                }
            }
        }
        self.maxDiff = None
        self.assertDictEqual(expected_node_attr,
                             result_node.attributes.to_dict())

    def test_update_environment(self):
        import chef
        cluster_name = self.test_chef.config_manager.get_clustername()
        env_name = self.test_chef.get_env_name(self.dist_sys_name,
                                               cluster_name)
        vars_dict = self.test_chef._get_cluster_tmpl_vars()
        env_attrs = self.test_chef._get_env_attributes(vars_dict)
        test_env = self.test_chef.get_environment(env_name)
        self.assertIsNotNone(test_env)
        self._register(test_env)

        self.test_chef._update_env(test_env, env_attrs)
        expected_env = {
            "name": "openstack_icehouse-test",
            "description": "Environment",
            "cookbook_versions": {
            },
            "json_class": "Chef::Environment",
            "chef_type": "environment",
            "default_attributes": {
            },
            "override_attributes": {
                "compute": {
                    "syslog": {
                        "use": False
                    },
                    "libvirt": {
                        "bind_interface": "eth0"
                    },
                    "novnc_proxy": {
                        "bind_interface": "vnet0"
                    },
                    "xvpvnc_proxy": {
                        "bind_interface": "eth0"
                    }
                },
                "db": {
                    "bind_interface": "vnet0",
                    "compute": {
                        "host": "12.234.32.100"
                    },
                    "identity": {
                        "host": "12.234.32.100"
                    }
                },
                "mq": {
                    "user": "guest",
                    "password": "test",
                    "vhost": "/nova",
                    "network": {
                        "service_type": "rabbitmq"
                    }
                }
            }
        }
        chef_env = chef.Environment(env_name, self.chef_test_api)
        self.maxDiff = None
        self.assertDictEqual(expected_env, chef_env.to_dict())

    def test_update_databags(self):
        import chef
        vars_dict = {
            "cluster": {
                "deployed_package_config": {
                    "service_credentials": {
                        "nova": {
                            "username": "nova",
                            "password": "compute"
                        }
                    },
                    "users_credentials": {
                        "ksadmin": {
                            "username": "ksadmin",
                            "password": "ksadmin"
                        },
                        "demo": {
                            "username": "demo",
                            "password": "demo"
                        }
                    }
                }
            }
        }
        expected_output = {
            "user_passwords": {
                "admin": {
                    "admin": "admin",
                },
                "ksadmin": {
                    "ksadmin": "ksadmin"
                },
                "demo": {
                    "demo": "demo"
                }
            },
            "db_passwords": {
                "nova": {
                    "nova": "compute",
                },
                "horizon": {
                    "horizon": "horizon"
                },
                "keystone": {
                    "keystone": "keystone"
                }
            }
        }
        self.test_chef.update_databags(vars_dict)
        databag_names = self.test_chef.config_manager.get_chef_databag_names()

        for name in databag_names:
            test_databag = chef.DataBag(name, self.chef_test_api)
            self.maxDiff = None
            expected_items = expected_output[name]
            for item, value in test_databag.iteritems():
                self.assertDictEqual(expected_items[item], value)

    def test_add_roles(self):
        import chef
        test_node = chef.Node('testnode', api=self.chef_test_api)
        test_node.run_list.append('role[test_role_a]')
        test_node.save()
        self._register(test_node)

        input_roles = ['test_role_1', 'test_role_2', 'test_role_a']
        self.test_chef._add_roles(test_node, input_roles)

        expected_roles = [('role[%s]' % role) for role in input_roles]
        self.assertSetEqual(set(expected_roles), set(test_node.run_list))
