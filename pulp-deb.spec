%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}
%{!?python_sitearch: %global python_sitearch %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib(1))")}

# define required pulp platform version.
%define pulp_version 2.10.3

%define inst_prefix pulp_deb

Name: pulp-deb
Version: 1.5.0
Release: 1%{?dist}
Summary: Support for Debian packages in the Pulp platform
Group: Development/Languages
License: GPLv2
URL: https://github.com/pulp/pulp_deb
Source0: https://fedorahosted.org/releases/p/u/%{name}/%{name}-%{version}.tar.gz
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildArch:      noarch
BuildRequires:  python2-devel
BuildRequires:  python-setuptools
# Not required, but Jenkins needs lzma.h for python-debpkgr
Requires: xz-devel

%description
Provides a collection of platform plugins and client extensions that provide
support for Debian packages.

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

# Remove tests
rm -rf %{buildroot}/%{python_sitelib}/test

%clean
rm -rf %{buildroot}

# ---- Common ---------------------------
%package -n python-%{name}-common
Summary: Pulp Debian support common library
Group: Development/Languages
Requires: python-pulp-common >= %{pulp_version}

%description -n python-%{name}-common
A collection of modules shared among all pulp-deb components.

%files -n python-%{name}-common
%defattr(-,root,root,-)
%dir %{python_sitelib}/%{inst_prefix}
%{python_sitelib}/%{inst_prefix}_common*.egg-info
%{python_sitelib}/%{inst_prefix}/__init__.py*
%{python_sitelib}/%{inst_prefix}/extensions/__init__.py*
%{python_sitelib}/%{inst_prefix}/common/
%doc COPYRIGHT LICENSE AUTHORS

# ---- Plugins -----------------------------------------------------------------
%package plugins
Summary: Pulp Debian plugins
Group: Development/Languages
Requires: python-%{name}-common = %{version}-%{release}
Requires: pulp-server >= %{pulp_version}
Requires: python-debian
Requires: python-debpkgr >= 1.0.0
Requires: gnupg

%description plugins
Provides a collection of platform plugins that extend the Pulp platform
to provide Debian package support.

%files plugins
%defattr(-,root,root,-)
%{python_sitelib}/%{inst_prefix}/plugins/
%{python_sitelib}/%{inst_prefix}_plugins*.egg-info
%config(noreplace) %{_sysconfdir}/httpd/conf.d/%{inst_prefix}.conf
%{_usr}/lib/pulp/plugins/types/deb.json
%doc COPYRIGHT LICENSE AUTHORS

# ---- Admin Extensions --------------------------------------------------------
%package admin-extensions
Summary: The Debian admin client extensions
Group: Development/Languages
Requires: python-%{name}-common = %{version}-%{release}
Requires: pulp-admin-client >= %{pulp_version}

%description admin-extensions
A collection of extensions that supplement and override generic admin
client capabilites with Debian specific features.

%files admin-extensions
%defattr(-,root,root,-)
%{python_sitelib}/%{inst_prefix}_extensions_admin*.egg-info
%{python_sitelib}/%{inst_prefix}/extensions/__init__.py*
%{python_sitelib}/%{inst_prefix}/extensions/admin/
%doc COPYRIGHT LICENSE AUTHORS

%changelog
* Tue Jan 10 2017 Mihai Ibanescu <mihai.ibanescu@gmail.com> 1.2-1
- Updated for pulp 2.10
* Wed May 6 2015 Barnaby Court<bcourt@redhat.com> 1.0.0-0.1.alpha
- Initial Release
