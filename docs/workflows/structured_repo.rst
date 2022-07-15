Creating a Structured Repo
==========================

Below is the workflow to use to create a structured repo from scratch, and then publish and
distribute it.

**Setup**

.. literalinclude:: ../_scripts/setup.sh
   :language: bash

**Workflow**

.. literalinclude:: ../_scripts/structured_repo.sh
   :language: bash

This should return ``200 OK`` response:

.. code-block:: html

    <!DOCTYPE html>
    <html>
        <body>
            <ul>

                <li><a href="Packages">Packages</a></li>

                <li><a href="Packages.gz">Packages.gz</a></li>

            </ul>
        </body>
    </html>
