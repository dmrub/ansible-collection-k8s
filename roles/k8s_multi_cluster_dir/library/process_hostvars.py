#!/usr/bin/env python

# Copyright: (c) 2020, Dmitri Rubinstein
# Apache 2.0 License, http://www.apache.org/licenses/
from __future__ import (absolute_import, division, print_function)
import sys
import os
import os.path
import re
from collections import defaultdict
from itertools import islice

__metaclass__ = type

DOCUMENTATION = r'''
---
module: process_hostvars

short_description: Process host variables to create inventory, extra variables, and vault files

# If this is part of a collection, you need to use semantic versioning,
# i.e. the version is of the form "2.5.0" and not "2.4".
version_added: "1.0.0"

description:
    - This C(process_hostvars) module allows to process host variables so that you can create inventory, extra variables and vault files

options:
  hostvars:
    description: Host variables, a dictionary which maps host name to the variable dictionary
    type: dict
    required: true

  pathvars:
    description: Path variables, a dictionary which maps variable names to paths
    type: dict
    required: false

  var_names:
    description: Names of variables to be processed
    type: list
    required: false

  vault_var_names:
      description: Names of variables to be put into a vault
      type: list
      required: false

  var_name_refs:
      description: Names of variables to be replaced by jinja2 template references
      type: list
      required: false

  path_var_names:
      description: Names of variables to be processed as paths
      type: list
      required: false

# Specify this value according to your collection
# in format of namespace.collection.doc_fragment_name
extends_documentation_fragment:
    - dmrub.util.process_hostvars

author:
    - Dmitri Rubinstein (@dmrub)
'''

EXAMPLES = r'''
- name: Process k8s_hostvars
  local_action:
    module: process_hostvars
    hostvars: "{{ k8s_hostvars }}"
    pathvars:
      project_root_dir: "{{ project_root_dir | default(none) }}"
  register: k8s_vars
'''

RETURN = r'''
# These are examples of possible return values, and in general should use other names for return values.
'''

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_bytes, to_native
from ansible.module_utils.six import PY3

FIX_NODE_NAME = re.compile(r"[-/]")


def run_module():
    # define available arguments/parameters a user can pass to the module
    module_args = dict(
        hostvars=dict(type='dict', required=True),
        pathvars=dict(type='dict', required=False, default={}),
        var_names=dict(type='list', required=False, default=[
            'ansible_host', 'ansible_port', 'ansible_user',
            'ansible_python_interpreter', 'ansible_ssh_common_args',
            'ansible_ssh_private_key_file',
            'kube_external_apiserver_address',
            'kube_external_apiserver_port',
            'supplementary_addresses_in_ssl_keys',
            'cluster_name', 'k8s_is_master']),
        vault_var_names=dict(type='list', required=False, default=[
            'ansible_become_pass', 'ansible_ssh_pass'
        ]),
        var_name_refs=dict(type='list', required=False, default=['ansible_ssh_private_key_file']),
        path_var_names=dict(type='list', required=False, default=['ansible_ssh_private_key_file'])
    )

    # seed the result dict in the object
    # we primarily care about changed and state
    # changed is if this module effectively modified the target
    # state will include any data that you want your module to pass back
    # for consumption, for example, in a subsequent task
    result = dict(
        changed=False,
    )

    # the AnsibleModule object will be our abstraction working with Ansible
    # this includes instantiation, a couple of common attr would be the
    # args/params passed to the execution, as well as if the module
    # supports check mode
    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    hostvars = module.params['hostvars']
    pathvars = module.params['pathvars']
    var_names = set(module.params['var_names'])
    vault_var_names = set(module.params['vault_var_names'])
    var_name_refs = set(module.params['var_name_refs'])
    path_var_names = set(module.params['path_var_names'])

    common_vars = dict()  # common variables
    common_vault_vars = dict()  # common vault variables
    inventory_vars = defaultdict(dict)  # variables per host

    # inventory_var_names and inventory_vault_var_names are used to store variable names that have different values on
    # different hosts and therefore need to be stored individually per node
    inventory_var_names = set()
    inventory_vault_var_names = set()

    hostvars_items = list(hostvars.items())

    # Fill common_vars and common_vault_vars with values for the first host
    for host, vars_dict in islice(hostvars.items(), 0, 1):
        for var_name in var_names:
            if var_name in vars_dict:
                common_vars[var_name] = vars_dict[var_name]

        for vault_var_name in vault_var_names:
            if vault_var_name in vars_dict:
                common_vault_vars[vault_var_name] = vars_dict[vault_var_name]

    # Compute inventory_vault_var_names
    for host, vars_dict in islice(hostvars.items(), 1, None):
        for var_name in var_names:
            var_value = vars_dict.get(var_name)
            stored_var_value = common_vars.get(var_name)
            if stored_var_value != var_value:
                inventory_var_names.add(var_name)

        for vault_var_name in vault_var_names:
            vault_var_value = vars_dict.get(vault_var_name)
            stored_var_value = common_vault_vars.get(vault_var_name)
            if stored_var_value != vault_var_value:
                inventory_vault_var_names.add(vault_var_name)

    # All variable names in inventory_var_names and inventory_vault_var_names have different values in some nodes and
    # cannot be in the common variable list and cannot be in common variable lists
    for var_name in inventory_var_names:
        del common_vars[var_name]

    for vault_var_name in inventory_vault_var_names:
        del common_vault_vars[vault_var_name]

    new_common_vault_vars = dict()
    for vault_var_name, vault_var_value in common_vault_vars.items():
        new_vault_var_name = 'vault_{}'.format(vault_var_name)
        common_vars[vault_var_name] = '{{ %s }}' % (new_vault_var_name,)
        new_common_vault_vars[new_vault_var_name] = vault_var_value
    del common_vault_vars
    common_vault_vars = new_common_vault_vars

    for host, vars_dict in hostvars.items():
        for var_name in inventory_var_names:
            var_value = vars_dict.get(var_name)
            if var_value is not None:
                inventory_vars[host][var_name] = var_value
        for vault_var_name in inventory_vault_var_names:
            vault_var_value = vars_dict.get(vault_var_name)
            if vault_var_value is not None:
                new_vault_var_name = 'vault_{}_{}'.format(FIX_NODE_NAME.sub('_', host), vault_var_name)
                inventory_vars[host][vault_var_name] = '{{ %s }}' % (new_vault_var_name,)
                common_vault_vars[new_vault_var_name] = vault_var_value

    def replace_str(value, old_value, new_value):
        if isinstance(value, str) and old_value in value:
            return value.replace(old_value, new_value)
        if isinstance(value, list):
            return [replace_str(i, old_value, new_value) for i in value]
        if isinstance(value, dict):
            new_dict = {}
            for k, v in value.items():
                new_dict[k] = replace_str(v, old_value, new_value)
            return new_dict
        return value

    # process variable references
    for var_name in var_name_refs:
        var_value = common_vars.get(var_name)
        var_ref = '{{ %s }}' % (var_name,)
        if var_value is not None:
            for host, host_vars_dict in inventory_vars.items():
                for host_var_name, host_var_value in host_vars_dict.items():
                    if host_var_name != var_name:
                        host_vars_dict[host_var_name] = replace_str(host_var_value, var_value, var_ref)
            for common_var_name, common_var_value in common_vars.items():
                if common_var_name != var_name:
                    common_vars[common_var_name] = replace_str(common_var_value, var_value, var_ref)

    # process path variables
    for pv_name, pv_value in pathvars.items():
        if not pv_value:
            continue
        for var_name in path_var_names:
            for host, host_vars_dict in inventory_vars.items():
                var_value = host_vars_dict.get(var_name)
                if var_value is None:
                    continue
                try:
                    cpath = os.path.commonpath([var_value, pv_value])
                    if cpath:
                        host_vars_dict[var_name] = os.path.join('{{ %s }}' % (pv_name,),
                                                                os.path.relpath(var_value, pv_value))
                except ValueError:
                    pass
            var_value = common_vars.get(var_name)
            if var_value is None:
                continue
            try:
                cpath = os.path.commonpath([var_value, pv_value])
                if cpath:
                    common_vars[var_name] = os.path.join('{{ %s }}' % (pv_name,),
                                                         os.path.relpath(var_value, pv_value))
            except ValueError:
                pass

    # if the user is working with this module in only check mode we do not
    # want to make any changes to the environment, just return the current
    # state with no modifications
    if module.check_mode:
        module.exit_json(**result)

    result['extra_vars'] = common_vars
    result['extra_vault_vars'] = common_vault_vars
    result['host_vars'] = inventory_vars

    # manipulate or modify the state as needed (this is going to be the
    # part where your module will do what it needs to do)
    # result['original_message'] = module.params['name']
    # result['message'] = 'goodbye'

    # use whatever logic you need to determine whether or not this module
    # made any modifications to your target
    # if module.params['new']:
    #    result['changed'] = True

    # during the execution of the module, if there is an exception or a
    # conditional state that effectively causes a failure, run
    # AnsibleModule.fail_json() to pass in the message and the result
    # if module.params['name'] == 'fail me':
    #    module.fail_json(msg='You requested this to fail', **result)

    # in the event of a successful module execution, you will want to
    # simple AnsibleModule.exit_json(), passing the key/value results
    module.exit_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()
