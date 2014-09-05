"""
The content model:

TODO: Define the content model

"""

from hashlib import sha256


def generate_remote_id(url):
    """
    Generate a remote_id based on the url.

    :param url: The remote URL.
    :type url: basestring
    :return: The generated ID.
    :rtype:str
    """
    h = sha256()
    h.update(url)
    return h.hexdigest()
