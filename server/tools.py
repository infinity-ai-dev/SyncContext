from uuid import UUID

from mcp.server.fastmcp import Context, FastMCP

from core.auth import TokenAuth
from core.memory import MemoryService
from core.models import MemoryCreate, MemoryUpdate
from core.search import SearchService
from server.context import current_project


def register_tools(mcp: FastMCP) -> None:
    """Register all SyncContext MCP tools."""

    def _get_services(ctx: Context) -> tuple[MemoryService, SearchService]:
        """Create services scoped to the current request's project."""
        lc = ctx.request_context.lifespan_context
        pool = lc["db_pool"]
        vector_store = lc["vector_store"]
        embeddings = lc["embeddings"]

        # Resolve project: from contextvar (HTTP) or fallback to env token (stdio)
        project = current_project.get()
        if project:
            project_id = project.id
        else:
            # stdio mode: ensure_project was called in lifespan
            # Fallback: use a zero UUID (shouldn't happen in practice)
            from uuid import UUID as _UUID

            project_id = _UUID("00000000-0000-0000-0000-000000000000")

        memory_service = MemoryService(pool, vector_store, embeddings, project_id)
        search_service = SearchService(memory_service, vector_store, embeddings, project_id)
        return memory_service, search_service

    def _get_auth(ctx: Context) -> TokenAuth:
        return ctx.request_context.lifespan_context["token_auth"]

    def _get_admin_token(ctx: Context) -> str | None:
        return ctx.request_context.lifespan_context.get("admin_token")

    def _get_project_info() -> str:
        """Get current project info for tool responses."""
        project = current_project.get()
        if project:
            return f"[Project: {project.name}]"
        return ""

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
            f"Memory saved successfully. {_get_project_info()}\n"
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
        results = await search_service.search(query=query, top_k=top_k, tag=tag, author=author)

        if not results:
            return f"No relevant memories found. {_get_project_info()}"

        lines = [f"Found {len(results)} relevant memories: {_get_project_info()}\n"]
        for i, r in enumerate(results, 1):
            m = r.memory
            tags_str = f"  Tags: {', '.join(m.tags)}\n" if m.tags else ""
            author_str = f" by {m.author}" if m.author else ""
            file_str = f"  File: {m.file_path}\n" if m.file_path else ""
            lines.append(
                f"{i}. [score: {r.score:.2f}]{author_str} ({m.created_at.strftime('%Y-%m-%d')})\n"
                f"  Type: {m.memory_type}\n"
                f"{tags_str}{file_str}"
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
        memories = await memory_service.list_memories(limit=limit, tag=tag, author=author, memory_type=memory_type)

        if not memories:
            return f"No memories found. {_get_project_info()}"

        lines = [f"Listing {len(memories)} memories: {_get_project_info()}\n"]
        for m in memories:
            tags_str = f" [{', '.join(m.tags)}]" if m.tags else ""
            author_str = f" by {m.author}" if m.author else ""
            lines.append(
                f"- [{m.id}] ({m.created_at.strftime('%Y-%m-%d')}) "
                f"{m.memory_type}{author_str}{tags_str}\n"
                f"  {m.content[:120]}{'...' if len(m.content) > 120 else ''}\n"
            )
        return "\n".join(lines)

    @mcp.tool()
    async def delete_memory(memory_id: str, ctx: Context = None) -> str:
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
            MemoryUpdate(content=content, tags=tags, file_path=file_path, memory_type=memory_type),
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
    async def get_project_context(ctx: Context = None) -> str:
        """Get a summary of the project's shared knowledge base.

        Use this when onboarding to a project or when you need an overview
        of what the team has documented so far.
        """
        memory_service, _ = _get_services(ctx)
        project = current_project.get()
        context = await memory_service.get_project_context()

        project_name = project.name if project else "Unknown"

        if context.total_memories == 0:
            return f"Project: {project_name}\nNo memories yet. Use save_memory to start building the knowledge base."

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
            f"Project: {project_name}\n"
            f"{'=' * 35}\n"
            f"Total memories: {context.total_memories}\n"
            f"Contributors: {contributors_str}\n"
            f"Top tags: {tags_str}\n\n"
            f"Recent memories:\n{recent_str}"
        )

    @mcp.tool()
    async def get_memory(memory_id: str, ctx: Context = None) -> str:
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
            f"{author_str}{tags_str}{file_str}"
            f"Created: {memory.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Updated: {memory.updated_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Content: {memory.content}"
        )

    @mcp.tool()
    async def list_tags(ctx: Context = None) -> str:
        """List all unique tags used in this project with their usage counts."""
        memory_service, _ = _get_services(ctx)
        tags = await memory_service.list_tags()

        if not tags:
            return "No tags found. Save memories with tags to build a taxonomy."

        lines = [f"Tags in this project ({len(tags)} total): {_get_project_info()}\n"]
        for entry in tags:
            tag, count = list(entry.items())[0]
            lines.append(f"  {tag}: {count} {'memory' if count == 1 else 'memories'}")
        return "\n".join(lines)

    @mcp.tool()
    async def list_contributors(ctx: Context = None) -> str:
        """List all contributors who have saved memories in this project."""
        memory_service, _ = _get_services(ctx)
        contributors = await memory_service.list_contributors()

        if not contributors:
            return "No contributors found."

        lines = [f"Contributors ({len(contributors)} total): {_get_project_info()}\n"]
        for entry in contributors:
            author, count = list(entry.items())[0]
            lines.append(f"  {author}: {count} {'memory' if count == 1 else 'memories'}")
        return "\n".join(lines)

    @mcp.tool()
    async def search_by_file(file_path: str, limit: int = 20, ctx: Context = None) -> str:
        """Find all memories related to a specific file path.

        Args:
            file_path: File path to search for (substring match, case-insensitive)
            limit: Maximum number of results (default 20)
        """
        memory_service, _ = _get_services(ctx)
        memories = await memory_service.search_by_file(file_path=file_path, limit=limit)

        if not memories:
            return f"No memories found for '{file_path}'."

        lines = [f"Found {len(memories)} memories for '{file_path}': {_get_project_info()}\n"]
        for m in memories:
            tags_str = f" [{', '.join(m.tags)}]" if m.tags else ""
            author_str = f" by {m.author}" if m.author else ""
            lines.append(
                f"- [{m.id}] ({m.created_at.strftime('%Y-%m-%d')}) "
                f"{m.memory_type}{author_str}{tags_str}\n"
                f"  File: {m.file_path}\n"
                f"  {m.content[:120]}{'...' if len(m.content) > 120 else ''}\n"
            )
        return "\n".join(lines)

    @mcp.tool()
    async def bulk_save_memories(memories: list[dict], ctx: Context = None) -> str:
        """Save multiple memories at once.

        Args:
            memories: List of memory objects with 'content' (required) and optional
                      'author', 'tags', 'file_path', 'memory_type'
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

        lines = [f"Saved {len(saved)} memories: {_get_project_info()}\n"]
        for m in saved:
            tags_str = f" [{', '.join(m.tags)}]" if m.tags else ""
            lines.append(f"  - [{m.id}] {m.memory_type}{tags_str}: {m.content[:80]}")
        return "\n".join(lines)

    @mcp.tool()
    async def find_similar(memory_id: str, top_k: int = 5, ctx: Context = None) -> str:
        """Find memories semantically similar to an existing memory.

        Args:
            memory_id: UUID of the source memory
            top_k: Maximum number of similar memories (default 5)
        """
        _, search_service = _get_services(ctx)
        try:
            uid = UUID(memory_id)
        except ValueError:
            return f"Invalid memory ID format: {memory_id}"

        results = await search_service.find_similar(memory_id=uid, top_k=top_k)

        if not results:
            return f"No similar memories found for {memory_id}."

        lines = [f"Found {len(results)} similar memories:\n"]
        for i, r in enumerate(results, 1):
            m = r.memory
            tags_str = f"  Tags: {', '.join(m.tags)}\n" if m.tags else ""
            author_str = f" by {m.author}" if m.author else ""
            lines.append(
                f"{i}. [score: {r.score:.2f}]{author_str} ({m.created_at.strftime('%Y-%m-%d')})\n"
                f"  Type: {m.memory_type}\n"
                f"{tags_str}  {m.content}\n"
            )
        return "\n".join(lines)

    # ── Admin tools ──────────────────────────────────────────────────────

    @mcp.tool()
    async def create_project(
        name: str,
        description: str | None = None,
        admin_token: str | None = None,
        ctx: Context = None,
    ) -> str:
        """Create a new project. Returns the generated token.

        Args:
            name: Display name for the project
            description: Optional project description
            admin_token: Admin authentication token
        """
        expected = _get_admin_token(ctx)
        if not expected:
            return "Admin operations disabled (no admin token configured)."
        if admin_token != expected:
            return "Invalid admin token."

        auth = _get_auth(ctx)
        project = await auth.create_project(name=name, description=description)
        return (
            f"Project created.\n"
            f"ID: {project.id}\n"
            f"Name: {project.name}\n"
            f"Token: {project.token}\n"
            f"Share this token with team members for their MCP client config."
        )

    @mcp.tool()
    async def list_projects(admin_token: str | None = None, ctx: Context = None) -> str:
        """List all registered projects. Requires admin token.

        Args:
            admin_token: Admin authentication token
        """
        expected = _get_admin_token(ctx)
        if not expected:
            return "Admin operations disabled (no admin token configured)."
        if admin_token != expected:
            return "Invalid admin token."

        auth = _get_auth(ctx)
        projects = await auth.list_projects()

        if not projects:
            return "No projects registered."

        lines = [f"Projects ({len(projects)} total):\n"]
        for p in projects:
            status = "active" if p.is_active else "inactive"
            lines.append(
                f"- [{p.id}] {p.name} ({status})\n"
                f"  Token: {p.token[:16]}...\n"
                f"  Created: {p.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
            )
        return "\n".join(lines)
