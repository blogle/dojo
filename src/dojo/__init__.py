"""
The root package for the Dojo application.

This package organizes the main domains and functionalities of the financial
management system, including core utilities, budgeting, frontend components,
investment tracking, forecasting, optimization, backtesting, and SQL-related modules.
"""

# Defines the public API of the 'dojo' package, specifying which submodules
# are considered part of the package's public interface when 'import *' is used.
__all__ = [
    "core",
    "budgeting",
    "frontend",
    "investments",
    "forecasting",
    "optimization",
    "backtesting",
    "sql",
]
