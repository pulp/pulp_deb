Contributing
================================================================================

.. _towncrier tool: https://github.com/hawkowl/towncrier
.. _pulp_deb issue tracker: https://pulp.plan.io/projects/pulp_deb/issues/

To contribute to the ``pulp_deb`` plugin follow this process:

1. Clone the GitHub repo
2. Make a change
3. Make sure all tests passed
4. Add a file into CHANGES folder (Changelog update).
5. Commit changes to own ``pulp_deb`` clone
6. Make pull request from github page for your clone against master branch


Changelog Update
--------------------------------------------------------------------------------

The ``CHANGES.rst`` file is managed using the `towncrier tool`_ and all non trivial changes must be accompanied by a news entry.

To add an entry to the news file, you first need an issue on the `pulp_deb issue tracker`_ describing the change you want to make.
Once you have an issue, take its number and create a file inside of the ``CHANGES/`` directory named as the issue number with an extension of ``.feature``, ``.bugfix``, ``.doc``, ``.removal``, or ``.misc``.
So if your issue is 3543 and it fixes a bug, you would create the file ``CHANGES/3543.bugfix``.
The content of your new file should be a short sentence describing your change in a single line of reStructuredText formatted text.
You do not need to reference any issue numbers since they are already referenced via the filename.
The sentence should be in past tense.
An example might be:

.. code-block:: none

   Fixed synchronization of Release files without a Suite field.

PRs can span multiple categories by creating multiple files (for instance, if you added a feature and deprecated an old feature at the same time, you would create ``CHANGES/NNNN.feature`` and ``CHANGES/NNNN.removal``).
Likewise if a PR touches multiple issues you may create a file for each of them with the exact same contents and Towncrier will deduplicate them.
