"""Learning Net — a self-hostable mirror and MCP server for the Learning Commons
Knowledge Graph.

Open infrastructure for educational AI, stewarded by the InterRealm Foundation.
The upstream data is published by Learning Commons under CC BY-4.0; see
DATA-LICENSE.md for the attribution this project carries and preserves.
"""

__version__ = "0.1.0"

from .graph import Graph, GraphError

__all__ = ["Graph", "GraphError", "__version__"]
