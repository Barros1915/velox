API Reference
============

This section documents the core Velox API.

Velox Core
---------

.. automodule:: velox.core
   :members:
   :undoc-members:
   :show-inheritance:

Request
-------

.. automodule:: velox.request
   :members:
   :undoc-members:
   :show-inheritance:

Response
---------

.. automodule:: velox.response
   :members:
   :undoc-members:
   :show-inheritance:

Router / Blueprint
------------------

.. autodata:: velox.core.Router
   :doc:
   :members:

WebSocket
--------

.. autoclass:: velox.core.WebSocket
   :members:
   :undoc-members:
   :show-inheritance:

Route Pattern
-----------

.. autoclass:: velox.core.RoutePattern
   :members:
   :undoc-members:
   :show-inheritance:

Module Functions
---------------

.. py:function:: velox.core.load_env(path='.env')

   Loads environment variables from a `.env` file.

   :param path: Path to the .env file
   :type path: str
   :raises FileNotFoundError: If the file doesn't exist

   Example::

      velox.core.load_env('.env.prod')

Constants
----------

.. py:data:: velox.core.CONVERTERS

   Dictionary of URL parameter converters.

   ==============  ====================  ==============================================
   Converter       Regex Pattern          Description
   ==============  ====================  ==============================================
   ``int``         ``\d+``              Integer number
   ``float``       ``\d+\.?\d*``        Float number
   ``str``         ``[^/]+``            String (default)
   ``slug``        ``[a-z0-9\-]+``       URL slug
   ``uuid``        ``[0-9a-f\-]{36}``   UUID
   ``path``        ``.+``               File path
   ==============  ====================  ==============================================

Type Aliases
-----------

.. data:: velox.core.MeuFramework

   Alias for :class:`velox.core.Velox` (for backwards compatibility).

   .. code-block:: python

      from velox import MeuFramework

   is equivalent to:

   .. code-block:: python

      from velox import Velox

.. data:: velox.core.Blueprint

   Alias for :class:`velox.core.Router`.

   .. code-block:: python

      from velox import Blueprint

   is equivalent to:

   .. code-block:: python

      from velox import Router