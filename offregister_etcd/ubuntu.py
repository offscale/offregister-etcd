from os import path

from offregister_fab_utils.apt import apt_depends
from patchwork.files import append

from offregister_fab_utils.fs import cmd_avail, get_tempdir_fab
from offregister_fab_utils.misc import upload_template_fmt
from offutils import update_d
from offutils.util import iteritems
from pkg_resources import resource_filename

from offregister_etcd import shared_serve


def install(c, version="v2.3.7", *args, **kwargs):
    """
    :param c: Connection
    :type c: ```fabric.connection.Connection```
    """
    command = "etcd"
    if cmd_avail(c, command):
        installed_version = (lambda s: s[s.rfind(" ") + 1 :])(
            c.run("etcd --version | head -n 1", hide=True)
        )
        if version[1:] == installed_version:
            c.local(
                "echo {command} {version} is already installed".format(
                    command=command, version=version
                )
            )
            return

    tempdir = get_tempdir_fab(c, run_command=c.run)

    install_dir = "{tempdir}/{version}/{epoch}".format(
        tempdir=tempdir, version=version, epoch=c.run("date +%s").stdout
    )
    c.run("mkdir -p {install_dir}".format(install_dir=install_dir))

    apt_depends(c, "curl")
    with c.cd(install_dir):
        c.run(
            "curl -OL "
            "https://github.com/coreos/etcd/releases/download/{version}/etcd-{version}-linux-amd64.tar.gz".format(
                version=version
            )
        )
        c.run("tar xf etcd-{version}-linux-amd64.tar.gz".format(version=version))
        c.run(
            "sudo mv etcd-{version}-linux-amd64/etcd /usr/local/bin".format(
                version=version
            )
        )
        c.run(
            "sudo mv etcd-{version}-linux-amd64/etcdctl /usr/local/bin".format(
                version=version
            )
        )
    c.run("logout")  # Need to get stuff from /etc/environment on next run


def serve(c, etcd_discovery=None, size=3, *args, **kwargs):
    """
    :param c: Connection
    :type c: ```fabric.connection.Connection```
    """
    cluster_name = "-".join(_f for _f in ("etcd2", kwargs["cluster_name"]) if _f)

    status = c.run(
        "status {cluster_name}".format(cluster_name=cluster_name),
        warn=True,
        hide=True,
    )
    if status.exited == 0 and status.endswith("start/running"):
        c.sudo("stop {cluster_name}".format(cluster_name=cluster_name))
        if "start/running" in c.run(
            "status {cluster_name}".format(cluster_name=cluster_name),
            warn=True,
            hide=True,
        ):
            raise RuntimeError("Cluster hasn't stopped")
    etcd_discovery = shared_serve(etcd_discovery, size, kwargs)
    append(
        "/etc/environment",
        "ETCD_DISCOVERY={etcd_discovery}".format(etcd_discovery=etcd_discovery),
        use_sudo=True,
    )

    data_dir = "/var/{cluster_name}_data_dir".format(cluster_name=cluster_name)
    c.sudo('mkdir -p "{data_dir}"'.format(data_dir=data_dir))

    upload_template_fmt(
        c,
        path.join(
            path.dirname(resource_filename("offregister_etcd", "__init__.py")),
            "data",
            "etcd2.upstart.conf",
        ),
        "/etc/init/{cluster_name}.conf".format(cluster_name=cluster_name),
        context={k: str(v) for k, v in iteritems(update_d(kwargs, locals()))},
        use_sudo=True,
    )

    c.sudo("initctl reload-configuration")
    c.sudo("start {cluster_name}".format(cluster_name=cluster_name), warn=True)
    return etcd_discovery


def tail(c, method_args, n=10, *args, **kwargs):
    """
    :param c: Connection
    :type c: ```fabric.connection.Connection```
    """
    c.sudo("initctl list | grep etcd")  # Chuck error if it's not installed
    c.sudo(
        "tail -n {n} {method_args} /var/log/upstart/etcd2-{cluster_name}.log".format(
            cluster_name=kwargs.get("cluster_name"), method_args=method_args, n=n
        )
    )
