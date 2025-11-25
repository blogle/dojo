"""
The budgeting domain package.

This package contains all modules related to budgeting functionalities,
including data schemas, business logic services, API routers, and SQL utilities.
"""

# Defines the public API of the 'budgeting' package, specifying which submodules
# are considered part of the package's public interface when 'import *' is used.
__all__ = ["routers", "schemas", "services", "sql"]
