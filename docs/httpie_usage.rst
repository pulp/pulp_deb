.. _httpie: https://httpie.org/doc

All REST API examples below use `httpie`_ to perform the requests.
The ``httpie`` commands below assume that the user executing the commands has a ``.netrc`` file in the home directory.
The ``.netrc`` should have the following configuration:

.. code-block:: none

   machine localhost
   login admin
   password admin

If you configured the ``admin`` user with a different password, adjust the configuration accordingly.
If you prefer to specify the username and password with each request, please see ``httpie`` documentation on how to do that.
