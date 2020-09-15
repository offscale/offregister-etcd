#!/usr/bin/env python

__author__ = "Samuel Marks"
__version__ = "0.0.2"

from etcd import EtcdKeyNotFound
from fabric.api import run, sudo

from offregister_fab_utils.fs import cmd_avail

from offutils_strategy_register import _get_client as get_client


def get_etcd_discovery_url(client, discovery_path):
    try:
        return client.get(discovery_path).value
    except EtcdKeyNotFound:
        return None


def set_etcd_discovery_url(client, discovery_path, size):
    etcd_discovery = run(
        "curl https://discovery.etcd.io/new?size={size}".format(size=size)
    )
    client.set(discovery_path, etcd_discovery)
    return etcd_discovery


def get_or_set_etcd_discovery_url(client, discovery_path, size):
    etcd_discovery = get_etcd_discovery_url(client, discovery_path)
    if not etcd_discovery:
        etcd_discovery = set_etcd_discovery_url(client, discovery_path, size)
    return etcd_discovery


def shared_serve(etcd_discovery, size, kwargs):
    if "ADVERT_PORT" not in kwargs:
        kwargs["ADVERT_PORT"] = 2379
    if "PEER_PORT" not in kwargs:
        kwargs["PEER_PORT"] = kwargs["ADVERT_PORT"] + 1
    if "ADDITIONAL_LISTEN_PORT" not in kwargs:
        kwargs["ADDITIONAL_LISTEN_PORT"] = 4001

    command = "etcd"
    if not cmd_avail(command):
        raise EnvironmentError(
            "Expected {command} to be installed".format(command=command)
        )

    client = get_client()
    discovery_path = "/".join((kwargs["cluster_path"], "discovery"))

    return etcd_discovery or get_or_set_etcd_discovery_url(client, discovery_path, size)
