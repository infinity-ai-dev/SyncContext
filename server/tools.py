from uuid import UUID

from mcp.server.fastmcp import Context, FastMCP

from core.memory import MemoryService
from core.models import MemoryCreate, MemoryUpdate
from core.search import SearchService


def register_tools(mcp: FastMCP) -> None:
    """Register all SyncContext MCP tools."""

    def _get_services(ctx: Context) -> tuple[MemoryService, SearchService]:
        lc = ctx.request_context.lifespan_context
        return lc["memory_service"], lc["search_service"]

    @mcp.tool()
    async def save_memory(
        content: str,
        author: str | None = None,
        tags: list[str] | None = None,
        file_path: str | None = None,
        memory_type: str = "general",
        ctx: Context = None,
    ) -> str:
        """Save a memory to the shared team knowledge base.

        Use this to store architecture decisions, patterns, bugs, conventions,
        or any context useful for team members and AI agents.

        Args:
            content: The memory content to save
            author: Who is saving this (developer name/email)
            tags: Categorization tags (e.g. ["auth", "frontend", "decision"])
            file_path: Related file path if applicable
            memory_type: Type: general, decision, bug, pattern, onboarding
        """
        memory_service, _ = _get_services(ctx)
        memory = await memory_service.save_memory(
            MemoryCreate(
                content=content,
                author=author,
                tags=tags or [],
                file_path=file_path,
                memory_type=memory_type,
            )
        )
        return (
            f"Memory saved successfully.\n"
            f"ID: {memory.id}\n"
            f"Type: {memory.memory_type}\n"
            f"Tags: {', '.join(memory.tags) if memory.tags else 'none'}"
        )

    @mcp.tool()
    async def search_memories(
        query: str,
        top_k: int = 5,
        tag: str | None = None,
        author: str | None = None,
        ctx: Context = None,
    ) -> str:
        """Search team memories by semantic similarity.

        Use this to find relevant context, decisions, patterns, or conventions
        that team members have previously documented.

        Args:
            query: Natural language search query
            top_k: Maximum number of results (default 5)
            tag: Filter by specific tag
            author: Filter by specific author
        """
        _, search_service = _get_services(ctx)
        results = await search_service.search(
            query=query,
            top_k=top_k,
            tag=tag,
            author=author,
        )

        if not results:
            return "No relevant memories found for this query."

        lines = [f"Found {len(results)} relevant memories:\n"]
        for i, r in enumerate(results, 1):
            m = r.memory
            tags_str = f"  Tags: {', '.join(m.tags)}\n" if m.tags else ""
            author_str = f" by {m.author}" if m.author else ""
            file_str = f"  File: {m.file_path}\n" if m.file_path else ""
            lines.append(
                f"{i}. [score: {r.score:.2f}]{author_str} ({m.created_at.strftime('%Y-%m-%d')})\n"
                f"  Type: {m.memory_type}\n"
                f"{tags_str}"
                f"{file_str}"
                f"  {m.content}\n"
            )
        return "\n".join(lines)

    @mcp.tool()
    async def list_memories(
        limit: int = 20,
        tag: str | None = None,
        author: str | None = None,
        memory_type: str | None = None,
        ctx: Context = None,
    ) -> str:
        """List recent memories from the project.

        Args:
            limit: Maximum number of memories to return (default 20)
            tag: Filter by tag
            author: Filter by author
            memory_type: Filter by type (general, decision, bug, pattern, onboarding)
        """
        memory_service, _ = _get_services(ctx)
        memories = await memory_service.list_memories(
            limit=limit,
            tag=tag,
            author=author,
            memory_type=memory_type,
        )

        if not memories:
            return "No memories found."

        lines = [f"Listing {len(memories)} memories:\n"]
        for m in memories:
            tags_str = f" [{', '.join(m.tags)}]" if m.tags else ""
            author_str = f" by {m.author}" if m.author else ""
            lines.append(
                f"- [{m.id}] ({m.created_at.strftime('%Y-%m-%d')}) {m.memory_type}{author_str}{tags_str}\n"
                f"  {m.content[:120]}{'...' if len(m.content) > 120 else ''}\n"
            )
        return "\n".join(lines)

    @mcp.tool()
    async def delete_memory(
        memory_id: str,
        ctx: Context = None,
    ) -> str:
        """Delete a specific memory by its ID.

        Args:
            memory_id: UUID of the memory to delete
        """
        memory_service, _ = _get_services(ctx)
        try:
            uid = UUID(memory_id)
        except ValueError:
            return f"Invalid memory ID format: {memory_id}"

        deleted = await memory_service.delete_memory(uid)
        if deleted:
            return f"Memory {memory_id} deleted successfully."
        return f"Memory {memory_id} not found."

    @mcp.tool()
    async def update_memory(
        memory_id: str,
        content: str | None = None,
        tags: list[str] | None = None,
        file_path: str | None = None,
        memory_type: str | None = None,
        ctx: Context = None,
    ) -> str:
        """Update an existing memory. Re-embeds automatically if content changes.

        Args:
            memory_id: UUID of the memory to update
            content: New content (triggers re-embedding if changed)
            tags: New tags (replaces existing)
            file_path: New file path
            memory_type: New memory type
        """
        memory_service, _ = _get_services(ctx)
        try:
            uid = UUID(memory_id)
        except ValueError:
            return f"Invalid memory ID format: {memory_id}"

        updated = await memory_service.update_memory(
            uid,
            MemoryUpdate(
                content=content,
                tags=tags,
                file_path=file_path,
                memory_type=memory_type,
            ),
        )

        if not updated:
            return f"Memory {memory_id} not found."
        return (
            f"Memory updated successfully.\n"
            f"ID: {updated.id}\n"
            f"Content: {updated.content[:100]}{'...' if len(updated.content) > 100 else ''}\n"
            f"Tags: {', '.join(updated.tags) if updated.tags else 'none'}"
        )

    @mcp.tool()
    async def get_project_context(
        ctx: Context = None,
    ) -> str:
        """Get a summary of the project's shared knowledge base.

        Use this when onboarding to a project or when you need an overview
        of what the team has documented so far.
        """
        memory_service, _ = _get_services(ctx)
        context = await memory_service.get_project_context()

        if context.total_memories == 0:
            return "This project has no memories yet. Use save_memory to start building the knowledge base."

        tags_str = ", ".join(
            f"{list(t.keys())[0]} ({list(t.values())[0]})" for t in context.top_tags
        ) if context.top_tags else "none"

        contributors_str = ", ".join(context.contributors) if context.contributors else "none"

        recent_str = "\n".join(
            f"  - [{m.memory_type}] {m.content[:80]}{'...' if len(m.content) > 80 else ''}"
            for m in context.recent_memories[:5]
        )

        return (
            f"Project Knowledge Base Summary\n"
            f"{'=' * 35}\n"
            f"Total memories: {context.total_memories}\n"
            f"Contributors: {contributors_str}\n"
            f"Top tags: {tags_str}\n\n"
            f"Recent memories:\n{recent_str}"
        )
