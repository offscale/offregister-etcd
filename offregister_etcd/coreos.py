from os import path
from pkg_resources import resource_filename

from fabric.api import run, sudo
from fabric.contrib.files import upload_template

from offregister_etcd import shared_serve


def install(*args, **kwargs):
    pass  # etcd is installed by default


def serve(etcd_discovery=None, size=3, *args, **kwargs):
    if kwargs["cluster_name"]:
        raise NotImplementedError(
            "Running multiple etcd clusters not yet implemented for CoreOS"
        )

    cluster_name = "etcd2"  # '-'.join(ifilter(None, ('etcd2', kwargs['cluster_name'])))
    if run(
        "systemctl status {cluster_name}.service".format(cluster_name=cluster_name),
        warn_only=True,
        quiet=True,
    ).succeeded:
        sudo("systemctl stop {cluster_name}.service".format(cluster_name=cluster_name))

    etcd_discovery = shared_serve(etcd_discovery, size, cluster_name, kwargs)

    data_dir = "/var/{cluster_name}_data_dir".format(cluster_name=cluster_name)
    sudo('mkdir -p "{data_dir}"'.format(data_dir=data_dir))

    upload_template(
        path.join(
            path.dirname(resource_filename("offregister.aux_recipes", "__init__.py")),
            "templates",
            "etcd2.systemd.conf",
        ),
        "/run/systemd/system/{cluster_name}.service.d/10-oem.conf".format(
            cluster_name=cluster_name
        ),
        context=locals(),
        use_sudo=True,
    )

    sudo("systemctl daemon-reload")
    sudo("systemctl start {cluster_name}.service".format(cluster_name=cluster_name))
    run("systemctl status {cluster_name}.service".format(cluster_name=cluster_name))
