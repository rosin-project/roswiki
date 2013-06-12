from __future__ import with_statement

import os
import sys
import yaml
import urllib2
try:
    from MoinMoin.Page import Page
except ImportError:
    print >> sys.stderr, "WARNING: Cannot load MoinMoin plugins, continuing load for testing only"

distro_names = ['boxturtle', 'cturtle', 'diamondback', 'electric', 'fuerte', 'groovy', 'hydro', 'unstable']
distro_names_indexed = ['diamondback', 'electric', 'fuerte', 'groovy', 'hydro', 'unstable'] #boxturtle and cturtle not indexed

#doc_url = "http://ros.org/doc/api/"
doc_url = "http://ros.org/doc/"

doc_path = '/var/www/www.ros.org/html/doc/'
metrics_path = '/var/www/www.ros.org/html/metrics/'

CONTRIBUTE_TMPL = """Cannot load information on <strong>%(name)s</strong>, which means that it is not yet in our index.
Please see <a href="http://www.ros.org/wiki/Get%%20Involved#Indexing_Your_.2A-ros-pkg_Repository_for_Documentation_Generation">this page</a> for information on how to submit your repository to our index."""

class UtilException(Exception): pass

def ahref(url, text):
    """create HTML link to specified URL with link text"""
    return '<a href="%(url)s">%(text)s</a>'%locals()

def repo_manifest_file(repo):
    """
    Generate filesystem path to stack.yaml for package
    """
    return os.path.join(doc_path, 'api', repo, "repo.yaml")

def package_manifest_file(package, distro=None):
    """
    Generate filesystem path to manifest.yaml for package
    """
    if distro:
        return os.path.join(doc_path, distro, 'api', package, "manifest.yaml")
    else:
        return os.path.join(doc_path, 'api', package, "manifest.yaml")

def get_package_versions(package):
    distros = []
    for d in distro_names_indexed:
        if os.path.exists(package_manifest_file(package, d)):
            distros.append(d)
    return distros
    
def package_html_link(package, distro=None):
    """
    Generate link to auto-generated package HTML documentation
    """
    if distro:
        return doc_url + distro + "/api/" + package + '/html/'
    else:
        return doc_url + "api/" + package  + '/html/'
    
def package_changelog_html_link(package, distro):
    """
    Generate link to auto-generated package changelog HTML
    """
    return doc_url + distro + "/changelogs/" + package + '/changelog.html'

def msg_doc_link(package, link_title, distro=None):
    package_url = package_html_link(package, distro)  
    return ahref('%(package_url)sindex-msg.html'%locals(), link_title)

def msg_link(package, msg):
    package_url = package_html_link(package)
    return ahref('%(package_url)smsg/%(msg)s.html'%locals(), msg)
  
def srv_link(package, srv):
    package_url = package_html_link(package)
    return ahref('%(package_url)ssrv/%(srv)s.html'%locals(), srv)

def sub_link(macro, page, sub, title=None):
    """
    Generate link to wiki subpage
    @param macro: macro instance
    @param page: current page name
    @param sub: sub page name
    @param title: (optional) link text
    """
    if title is None:
        title = sub
    return Page(macro.request, '%s/%s'%(page, sub)).link_to(macro.request, text=title)

def wiki_url(macro, page,shorten=None,querystr=None):
    """
    Create link to ROS wiki page
    """
    if not shorten or len(page) < shorten:
        page_text = page
    else:
        page_text = page[:shorten]+'...'
    return Page(macro.request, page).link_to(macro.request, text=page_text, querystr=querystr)

def get_repo_li(macro, props):
    """
    Get list item HTML for repository URL
    @param macro: Moin macro object
    @param props: package/stack manifest dictionary
    """
    if 'repository' in props and props['repository'] is not None:
        f = macro.formatter
        li = f.listitem
        return li(1)+f.text("Repository: ")+wiki_url(macro, props['repository'])+li(0)
    else:
        return ''

def get_vcs_li(macro, stack_data):
    if 'vcs' in stack_data and 'vcs_uri' in stack_data:
        type_ = stack_data['vcs']
        uri_display = uri = stack_data['vcs_uri']
        # link goes to browsable version of repo if github
        if not uri:
            return ''
        if '//github.com/' in uri and uri.endswith('.git'):
            uri = uri[:-4]
        f = macro.formatter
        li = f.listitem
        return li(1)+f.text("Source: "+type_)+f.rawHTML(' <a href="%s">%s</a>'%(uri, uri_display))+li(0)
    else:
        return ''

def get_url_li(macro, data):
    if 'url' in data and data['url'] and 'ros.org/wiki' not in data['url']:
        f = macro.formatter
        li = f.listitem
        return li(1)+f.text("External website: ")+f.rawHTML(' <a href="%s">%s</a>'%(data['url'], data['url']))+li(0)
    else:
        return ''

def get_bugtracker_li(macro, data):
    if 'bugtracker' in data and data['bugtracker']:
        f = macro.formatter
        li = f.listitem
        return li(1)+f.text("Bug / feature tracker: ")+f.rawHTML(' <a href="%s">%s</a>'%(data['bugtracker'], data['bugtracker']))+li(0)
    else:
        return ''

def get_maintainer_status_li(macro, data):
    if 'maintainer_status' in data and data['maintainer_status']:
        f = macro.formatter
        li = f.listitem
        status_description = ' (%s)' % data['maintainer_status_description'] if 'maintainer_status_description' in data and data['maintainer_status_description'] else ''
        return li(1)+f.text("Maintainer status: ")+data['maintainer_status']+status_description+li(0)
    else:
        return ''

def process_distro(stack_name, yaml_str):
    """
    @return: distro properties, stack properties. Stack properties
    is just for convenience as it is part of distro properties
    """
    distro = yaml.load(yaml_str)
    return distro, distro['stacks'][stack_name]

def load_stack_release(release_name, stack_name):
    """load in distro release info for stack"""
    if stack_name == 'ROS':
        stack_name = 'ros'
    try:
        #TODO: figure out how to cache these better, e.g. have a hudson job that rsyncs to wgs32
        if release_name in ['boxturtle', 'cturtle', 'diamondback']:
            usock = open('/var/www/www.ros.org/html/distros/%s.rosdistro'%release_name)
        else:
            usock = urllib2.urlopen('https://code.ros.org/svn/release/trunk/distros/%s.rosdistro'%release_name)
        rosdistro_str = usock.read()
        usock.close()
        release, stack_props = process_distro(stack_name, rosdistro_str)
    except:
        release = stack_props = {}
    return release, stack_props

def _load_manifest_file(filename, name, type_='package'):
    """
    Load manifest.yaml properties into dictionary for package
    @param filename: file to load manifest data from
    @param name: printable name (for debugging)
    @return: manifest properties dictionary
    @raise UtilException: if unable to load. Text of error message is human-readable
    """
    if not os.path.exists(filename):
        raise UtilException('Newly proposed, mistyped, or obsolete %s. Could not find %s "'%(type_, type_) + name + '" in rosdoc')

    try:
        with open(filename) as f:
            data = yaml.load(f)
    except:
        raise UtilException("Error loading manifest data")        

    if not data:
        raise UtilException("Unable to retrieve manifest data. Auto-generated documentation may need to regenerate")
    return data

def load_package_manifest(package_name, distro=None):
    """
    Load manifest.yaml properties into dictionary for package
    @param lang: optional language argument for localization, e.g. 'ja'
    @return: manifest properties dictionary
    @raise UtilException: if unable to load. Text of error message is human-readable
    """
    return _load_manifest_file(package_manifest_file(package_name, distro), package_name, "package")

def load_repo_manifest(repo_name):
    """
    Load repo.yaml properties into dictionary for package
    @param lang: optional language argument for localization, e.g. 'ja'
    @return: manifest properties dictionary
    @raise UtilException: if unable to load. Text of error message is human-readable
    """
    data = _load_manifest_file(repo_manifest_file(repo_name), repo_name, 'repository')
    if not data:
        raise UtilException("Unable to retrieve manifest data. Auto-generated documentation may need to regenerate")
    return data


def load_stack_manifest(stack_name, distro=None):
    """
    Load stack.yaml properties into dictionary for package
    @param lang: optional language argument for localization, e.g. 'ja'
    @return: stack manifest properties dictionary
    @raise UtilException: if unable to load. Text of error message is human-readable
    """
    return _load_manifest_file(package_manifest_file(stack_name, distro), stack_name, 'stack')
