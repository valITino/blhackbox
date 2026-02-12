"""Reset the Neo4j knowledge graph – delete all nodes and relationships."""

from __future__ import annotations

import asyncio
import sys

from blhackbox.core.knowledge_graph import KnowledgeGraphClient
from blhackbox.utils.logger import console, setup_logging


async def main() -> None:
    setup_logging("INFO")
    console.print("[warning]This will DELETE all data in the knowledge graph.[/warning]")
    confirm = input("Type 'yes' to confirm: ").strip().lower()
    if confirm != "yes":
        console.print("Aborted.")
        sys.exit(0)

    async with KnowledgeGraphClient() as kg:
        await kg.clear_all()

    console.print("[success]Knowledge graph has been reset.[/success]")


if __name__ == "__main__":
    asyncio.run(main())
