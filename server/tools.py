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

        tags_str = (
            ", ".join(f"{list(t.keys())[0]} ({list(t.values())[0]})" for t in context.top_tags)
            if context.top_tags
            else "none"
        )

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

    @mcp.tool()
    async def get_memory(
        memory_id: str,
        ctx: Context = None,
    ) -> str:
        """Get a single memory by its UUID.

        Args:
            memory_id: UUID of the memory to retrieve
        """
        memory_service, _ = _get_services(ctx)
        try:
            uid = UUID(memory_id)
        except ValueError:
            return f"Invalid memory ID format: {memory_id}"

        memory = await memory_service.get_memory(uid)
        if not memory:
            return f"Memory {memory_id} not found."

        tags_str = f"Tags: {', '.join(memory.tags)}\n" if memory.tags else ""
        author_str = f"Author: {memory.author}\n" if memory.author else ""
        file_str = f"File: {memory.file_path}\n" if memory.file_path else ""
        return (
            f"Memory [{memory.id}]\n"
            f"Type: {memory.memory_type}\n"
            f"{author_str}"
            f"{tags_str}"
            f"{file_str}"
            f"Created: {memory.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Updated: {memory.updated_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Content: {memory.content}"
        )

    @mcp.tool()
    async def list_tags(
        ctx: Context = None,
    ) -> str:
        """List all unique tags used in this project with their usage counts.

        Use this to understand how the team organises knowledge and to discover
        available tags for filtering with search_memories or list_memories.
        """
        memory_service, _ = _get_services(ctx)
        tags = await memory_service.list_tags()

        if not tags:
            return "No tags found. Save memories with tags to build a taxonomy."

        lines = [f"Tags used in this project ({len(tags)} total):\n"]
        for entry in tags:
            tag, count = list(entry.items())[0]
            lines.append(f"  {tag}: {count} {'memory' if count == 1 else 'memories'}")
        return "\n".join(lines)

    @mcp.tool()
    async def list_contributors(
        ctx: Context = None,
    ) -> str:
        """List all contributors who have saved memories in this project, with counts.

        Use this to see who is actively documenting knowledge and to filter
        memories by a specific author.
        """
        memory_service, _ = _get_services(ctx)
        contributors = await memory_service.list_contributors()

        if not contributors:
            return "No contributors found. Save a memory with an author to get started."

        lines = [f"Contributors to this project ({len(contributors)} total):\n"]
        for entry in contributors:
            author, count = list(entry.items())[0]
            lines.append(f"  {author}: {count} {'memory' if count == 1 else 'memories'}")
        return "\n".join(lines)

    @mcp.tool()
    async def search_by_file(
        file_path: str,
        limit: int = 20,
        ctx: Context = None,
    ) -> str:
        """Find all memories related to a specific file path (exact or substring match).

        Use this to discover all context documented about a particular file,
        directory, or module path.

        Args:
            file_path: File path to search for (substring match, case-insensitive)
            limit: Maximum number of results (default 20)
        """
        memory_service, _ = _get_services(ctx)
        memories = await memory_service.search_by_file(file_path=file_path, limit=limit)

        if not memories:
            return f"No memories found for file path matching '{file_path}'."

        lines = [f"Found {len(memories)} memories related to '{file_path}':\n"]
        for m in memories:
            tags_str = f" [{', '.join(m.tags)}]" if m.tags else ""
            author_str = f" by {m.author}" if m.author else ""
            lines.append(
                f"- [{m.id}] ({m.created_at.strftime('%Y-%m-%d')}) {m.memory_type}{author_str}{tags_str}\n"
                f"  File: {m.file_path}\n"
                f"  {m.content[:120]}{'...' if len(m.content) > 120 else ''}\n"
            )
        return "\n".join(lines)

    @mcp.tool()
    async def bulk_save_memories(
        memories: list[dict],
        ctx: Context = None,
    ) -> str:
        """Save multiple memories at once. Useful for importing or batch operations.

        Each item in the list must have a 'content' field and may optionally include
        'author', 'tags', 'file_path', and 'memory_type'.

        Args:
            memories: List of memory objects to save
        """
        memory_service, _ = _get_services(ctx)

        if not memories:
            return "No memories provided."

        creates = []
        for i, item in enumerate(memories):
            if not isinstance(item, dict) or "content" not in item:
                return f"Item at index {i} is missing required 'content' field."
            creates.append(
                MemoryCreate(
                    content=item["content"],
                    author=item.get("author"),
                    tags=item.get("tags") or [],
                    file_path=item.get("file_path"),
                    memory_type=item.get("memory_type", "general"),
                )
            )

        saved = await memory_service.bulk_save_memories(creates)

        lines = [f"Saved {len(saved)} memories:\n"]
        for m in saved:
            tags_str = f" [{', '.join(m.tags)}]" if m.tags else ""
            truncated = f"{m.content[:80]}{'...' if len(m.content) > 80 else ''}"
            lines.append(f"  - [{m.id}] {m.memory_type}{tags_str}: {truncated}")
        return "\n".join(lines)

    @mcp.tool()
    async def find_similar(
        memory_id: str,
        top_k: int = 5,
        ctx: Context = None,
    ) -> str:
        """Find memories semantically similar to an existing memory.

        Use this to discover related context, duplicate entries, or connected
        decisions when reviewing a specific memory.

        Args:
            memory_id: UUID of the source memory to compare against
            top_k: Maximum number of similar memories to return (default 5)
        """
        _, search_service = _get_services(ctx)
        try:
            uid = UUID(memory_id)
        except ValueError:
            return f"Invalid memory ID format: {memory_id}"

        results = await search_service.find_similar(memory_id=uid, top_k=top_k)

        if not results:
            return f"No similar memories found for memory {memory_id}."

        lines = [f"Found {len(results)} memories similar to [{memory_id}]:\n"]
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
