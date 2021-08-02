Installation
================================================================================

.. include:: external_references.rst


As with all Pulp plugins, the installation method for ``pulp_deb`` depends on your chosen ``pulpcore`` installation method.
There are multiple `pulpcore installation options`_.
The default recommendation is to use the `Pulp Ansible installer`_, which is documented via the `Pulp Ansible installer documentation`_.

Using the Pulp Ansible installer as our example, adding the ``pulp_deb`` plugin to your installation is as easy as uncommenting ``# pulp-deb: {}`` in the example playbook, and then re-running that playbook.
This will both work for entirely new Pulp installations, as well as to add the ``pulp_deb`` plugin to a already completed Pulp installation.

If you need more help with advanced installation scenarios you can either consult the documentation referenced above, or else join the ``pulp`` Matrix/IRC channel for interactive help.
See the `Pulp project help page`_ for more information and additional ways on how to get in contact with the Pulp community.
