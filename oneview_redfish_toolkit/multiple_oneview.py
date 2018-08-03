# -*- coding: utf-8 -*-

# Copyright (2018) Hewlett Packard Enterprise Development LP
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

# 3rd party libs
from hpOneView import HPOneViewException

# Modules own libs
from oneview_redfish_toolkit.api.errors \
    import OneViewRedfishResourceNotFoundError
from oneview_redfish_toolkit import authentication
from oneview_redfish_toolkit import connection

# Globals vars:
#   globals()['map_resources_ov']


NOT_FOUND_ERROR = ['RESOURCE_NOT_FOUND', 'ProfileNotFoundException',
                   'DFRM_SAS_LOGICAL_JBOD_NOT_FOUND']


def init_map_resources():
    globals()['map_resources_ov'] = dict()


def get_map_resources():
    return globals()['map_resources_ov']


def set_map_resources_entry(resource_id, ip_oneview):
    get_map_resources()[resource_id] = ip_oneview


def query_ov_client_by_resource(resource_id, resource, function,
                                *args, **kwargs):
    """Query resource on OneViews.

        Query specific resource ID on multiple OneViews.
        Look resource ID on cached map ResourceID->OneViewIP for query
        on specific cached OneView IP.
        If the resource ID is not cached yet it searchs on all OneViews.

        Returns:
            dict: OneView resource
    """
    # Get cached OneView IP by resource ID
    ip_oneview = get_ov_ip_by_resource(resource_id)

    # If resource is not cached yet search in all OneViews
    if not ip_oneview:
        return search_resource_multiple_ov(resource, function, resource_id,
                                           *args, **kwargs)

    # Get cached OneView's token
    ov_token = authentication.get_oneview_token(ip_oneview)

    ov_client = connection.get_oneview_client(ip_oneview, token=ov_token)

    return execute_query_ov_client(ov_client, resource, function,
                                   *args, **kwargs)


def get_ov_ip_by_resource(resource_id):
    """Get cached OneView's IP by resource ID"""
    map_resources = get_map_resources()

    if resource_id not in map_resources:
        return None

    ip_oneview = map_resources[resource_id]

    return ip_oneview


def search_resource_multiple_ov(resource, function, resource_id,
                                *args, **kwargs):
    """Search resource on multiple OneViews

        Query resource on all OneViews.
        If it's looking for a specific resource:
            -Once resource is found it will cache the resource ID for the
                OneView's IP that was found;
            -If it is not found return NotFound exception.
        If it's looking for all resources(get_all):
            -Always query on all OneViews and return a list appended the
                results for all OneViews

        Args:
            resource: resource type (server_hardware)
            function: resource function name (get_all)
            resource_id: set only if it should look for a specific resource ID
            *args: original arguments for the OneView client query
            **kwargs: original keyword arguments for the OneView client query

        Returns:
            OneView resource(s)

        Exceptions:
            OneViewRedfishResourceNotFoundError: When resource was not found
            in any OneViews.

            HPOneViewException: When occur an error on any OneViews which is
            not an not found error.
    """
    # Get all OneView's IP and tokens cached by Redfish's token
    ov_ip_tokens = authentication.get_multiple_oneview_token()
    result = []

    # Loop in all OneView's IP and token
    for ov_ip, ov_token in ov_ip_tokens.items():
        ov_client = connection.get_oneview_client(ov_ip,
                                                  token=ov_token)

        try:
            # Query resource on OneView
            expected_resource = \
                execute_query_ov_client(ov_client, resource, function,
                                        *args, **kwargs)

            if expected_resource:
                # If it's looking for a especific resource and was found
                if resource_id:
                    set_map_resources_entry(resource_id, ov_ip)
                    return expected_resource
                else:
                    # If it's looking for a resource list (get_all)
                    result.extend(expected_resource)
        except HPOneViewException as e:
            # If get any error that is not a notFoundError
            if e.oneview_response["errorCode"] not in NOT_FOUND_ERROR:
                raise e

    # If it's looking for a specific resource returns a NotFound exception
    if resource_id:
        raise OneViewRedfishResourceNotFoundError(resource_id, resource)

    return result


def execute_query_ov_client(ov_client, resource, function, *args, **kwargs):
    """Execute query for resource on OneView client received as parameter"""
    ov_resource = object.__getattribute__(ov_client, resource)
    ov_function = object.__getattribute__(ov_resource, function)

    return ov_function(*args, **kwargs)