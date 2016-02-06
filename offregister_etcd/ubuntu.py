from os import path
from pkg_resources import resource_filename

from fabric.api import run, sudo, cd, local, settings
from fabric.contrib.files import append, upload_template

from offregister_fab_utils.fs import get_tempdir_fab, cmd_avail
from offregister_fab_utils.misc import ubuntu_install_curl

from offutils_strategy_register import _get_client as get_client
from offregister_etcd import get_etcd_discovery_url


def install(version='v2.2.5', *args, **kwargs):
    command = 'etcd'
    if cmd_avail(command):
        installed_version = (lambda s: s[s.rfind(' ') + 1:])(run('etcd --version | head -n 1', quiet=True))
        if version[1:] == installed_version:
            local('echo {command} {version} is already installed'.format(command=command, version=version))
            return

    tempdir = get_tempdir_fab(run_command=run)

    install_dir = '{tempdir}/{version}/{epoch}'.format(
        tempdir=tempdir, version=version, epoch=run('date +%s', quiet=True)
    )
    run('mkdir -p {install_dir}'.format(install_dir=install_dir))

    ubuntu_install_curl()
    with cd(install_dir):
        run(
            'curl -OL '
            'https://github.com/coreos/etcd/releases/download/{version}/etcd-{version}-linux-amd64.tar.gz'.format(
                version=version
            )
        )
        run('tar xf etcd-{version}-linux-amd64.tar.gz'.format(version=version))
        run('sudo mv etcd-{version}-linux-amd64/etcd /usr/local/bin'.format(version=version))
        run('sudo mv etcd-{version}-linux-amd64/etcdctl /usr/local/bin'.format(version=version))
    run('logout')  # Need to get stuff from /etc/environment on next run


def serve(domain, node_name, public_ipv4, private_ipv4, etcd_discovery=None, size=3,
          discovery_path='/coreos/discovery', *args, **kwargs):
    command = 'etcd'
    if not cmd_avail(command):
        raise EnvironmentError('Expected {command} to be installed'.format(command=command))

    if run('status etcd2', warn_only=True, quiet=True).succeeded:
        if sudo('status etcd2').endswith('stop/waiting'):
            sudo('start etcd2')
        return etcd_discovery or run('echo "$ETCD_DISCOVERY"', quiet=True)

    client = get_client()
    etcd_discovery = get_etcd_discovery_url(client, etcd_discovery, size, discovery_path)
    append('/etc/environment', 'ETCD_DISCOVERY={etcd_discovery}'.format(etcd_discovery=etcd_discovery),
           use_sudo=True)
    data_dir = '/var/etcd2_data_dir'
    sudo('mkdir {data_dir}'.format(data_dir=data_dir))
    upload_template(
        path.join(path.dirname(resource_filename('offregister_etcd', '__init__.py')), 'data',
                  'etcd2.upstart.conf'),
        '/etc/init/etcd2.conf', context=locals(), use_sudo=True
    )
    sudo('initctl reload-configuration')
    sudo('start etcd2')
    return etcd_discovery


def tail(method_args, n=10):
    sudo('initctl list | grep etcd')  # Chuck error if it's not installed
    sudo('tail -n {n} {method_args} /var/log/upstart/etcd2.log'.format(method_args=method_args, n=n))
