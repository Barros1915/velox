Installation
=============

Requirements
-------------

- Python 3.9 or higher

Basic Installation
------------------

Install Velox from PyPI:

.. code-block:: bash

    pip install velox-web

This installs Velox without any dependencies.

With ASGI Support
-----------------

To use async features, install with uvicorn:

.. code-block:: bash

    pip install velox-web[asgi]

This installs:

- ``velox-web`` — The framework
- ``uvicorn`` — ASGI server

With Full Features
-----------------

To install all features:

.. code-block:: bash

    pip install velox-web[full]

This installs:

- ``velox-web`` — The framework
- ``uvicorn`` — ASGI server
- ``psycopg2-binary`` — PostgreSQL support
- ``redis`` — Redis cache support
- ``aiosqlite`` — Async SQLite support
- ``asyncpg`` — Async PostgreSQL support

Development Dependencies
----------------------

For local development:

.. code-block:: bash

    pip install velox-web[dev]

This installs:

- ``pytest`` — Test framework
- ``pytest-asyncio`` — Async test support
- ``httpx`` — HTTP client for testing

Verify Installation
------------------

After installing, verify it works:

.. code-block:: python

   import velox

   print(velox.__version__)  # Should print 1.0.0

Or run the built-in server:

.. code-block:: python

   from velox import Velox

   app = Velox(__name__)

   @app.get('/')
   def home(req, res):
       res.text('Hello from Velox!')

   app.run()

Then open http://localhost:8000 in your browser.

From Source
----------

Install from the latest source:

.. code-block:: bash

   git clone https://github.com/Barros1915/velox.git
   cd velox
   pip install -e .

Upgrading
--------

To upgrade to the latest version:

.. code-block:: bash

   pip install --upgrade velox-web

Or for a specific version:

.. code-block:: bash

   pip install velox-web==1.0.0
