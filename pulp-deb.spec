%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}
%{!?python_sitearch: %global python_sitearch %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib(1))")}

Name: python-pulp-deb
Version: 1.0.0
Release: 0.3.beta%{?dist}
Summary: Support for Debian packages in the Pulp platform
Group: Development/Languages
License: GPLv2
URL: https://github.com/pulp/pulp_deb
Source0: https://fedorahosted.org/releases/p/u/%{name}/%{name}-%{version}.tar.gz
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildArch:      noarch
BuildRequires:  python-setuptools

# This is the minimum platform version we require to function.
%define pulp_version 2.7

%description
Provides a collection of platform plugins and client extensions support for Python packages.


%prep
%setup -q


%build
pushd common
%{__python} setup.py build
popd

pushd extensions_admin
%{__python} setup.py build
popd

pushd plugins
%{__python} setup.py build
popd


%install
rm -rf %{buildroot}

mkdir -p %{buildroot}/%{_sysconfdir}/pulp/

pushd common
%{__python} setup.py install -O1 --skip-build --root %{buildroot}
popd

pushd extensions_admin
%{__python} setup.py install -O1 --skip-build --root %{buildroot}
popd

pushd plugins
%{__python} setup.py install -O1 --skip-build --root %{buildroot}
popd

mkdir -p %{buildroot}/%{_usr}/lib/pulp/plugins/types
mkdir -p %{buildroot}/%{_var}/lib/pulp/published/deb

cp -R plugins/etc/httpd %{buildroot}/%{_sysconfdir}/
# Types
cp -R plugins/types/* %{buildroot}/%{_usr}/lib/pulp/plugins/types/

# Remove tests
rm -rf %{buildroot}/%{python_sitelib}/test

%clean
rm -rf %{buildroot}


# ---- Common ---------------------------
%package common
Summary: Pulp Debian support common library
Group: Development/Languages
Requires: python-pulp-common >= %{pulp_version}
Requires: python-setuptools

%description -n python-pulp-deb-common
A collection of modules shared among all Pulp-Deb components.

%files -n python-pulp-deb-common
%defattr(-,root,root,-)
%dir %{python_sitelib}/pulp_deb
%{python_sitelib}/pulp_deb/__init__.py*
%{python_sitelib}/pulp_deb/common/
%dir %{python_sitelib}/pulp_deb/extensions
%{python_sitelib}/pulp_deb/extensions/__init__.py*
%{python_sitelib}/pulp_deb_common*.egg-info
%doc COPYRIGHT LICENSE AUTHORS


# ---- Plugins -----------------------------------------------------------------
%package plugins
Summary: Pulp Debian plugins
Group: Development/Languages
Requires: python-pulp-common >= %{pulp_version}
Requires: python-pulp-deb-common >= %{version}
Requires: pulp-server >= %{pulp_version}
Requires: python-setuptools
Requires: python-debian
Requires: dpkg-dev

%description plugins
Provides a collection of platform plugins that extend the Pulp platform
to provide Debian package support.

%files plugins
%defattr(-,root,root,-)
%{python_sitelib}/pulp_deb/plugins/
%config(noreplace) %{_sysconfdir}/httpd/conf.d/pulp_deb.conf
%{_usr}/lib/pulp/plugins/types/deb.json
%{python_sitelib}/pulp_deb_plugins*.egg-info

%defattr(-,apache,apache,-)
%{_var}/lib/pulp/published/deb/

%doc COPYRIGHT LICENSE AUTHORS


# ---- Admin Extensions --------------------------------------------------------
%package admin-extensions
Summary: The Python admin client extensions
Group: Development/Languages
Requires: python-pulp-common >= %{pulp_version}
Requires: python-pulp-deb-common = %{version}
Requires: pulp-admin-client >= %{pulp_version}
Requires: python-setuptools

%description admin-extensions
A collection of extensions that supplement and override generic admin
client capabilites with Debian specific features.

%files admin-extensions
%defattr(-,root,root,-)
%{python_sitelib}/pulp_deb/extensions/admin/
%{python_sitelib}/pulp_deb_extensions_admin*.egg-info
%doc COPYRIGHT LICENSE AUTHORS


%changelog
* Wed May 6 2015 Barnaby Court<bcourt@redhat.com> 1.0.0-0.1.alpha
- Initial Release
