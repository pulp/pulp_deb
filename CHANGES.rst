=========
Changelog
=========

..
    You should *NOT* be adding new change log entries to this file, this
    file is managed by towncrier. You *may* edit previous change logs to
    fix problems like typo corrections or such.
    To add a new change log entry, please see
    https://docs.pulpproject.org/en/3.0/nightly/contributing/git.html#changelog-update

    WARNING: Don't drop the next directive!

.. towncrier release notes start

2.0.0b1 (2019-09-06)
====================

Features
--------


- Add oneshot upload functionality for deb type packages.
  `#5391 <https://pulp.plan.io/issues/5391>`_



Bugfixes
--------


- Add relative_path to package units natural key to fix uniqueness constraints.
  `#5377 <https://pulp.plan.io/issues/5377>`_
- Fix publishing of lazy content and add download_policy tests.
  `#5405 <https://pulp.plan.io/issues/5405>`_



Improved Documentation
----------------------


- Reference the fact you must have both _relative_path and relative_path.
  `#5376 <https://pulp.plan.io/issues/5376>`_
- Fix various documentation issues from API changes, plus other misc fixes.
  `#5380 <https://pulp.plan.io/issues/5380>`_



Misc
----


- Adopting related names on models.
  `#4681 <https://pulp.plan.io/issues/4681>`_
- Generate and commit initial migrations.
  `#5401 <https://pulp.plan.io/issues/5401>`_





