def generate_project(repositories):
    """Generate a unique browser game using AI."""

    existing_names = [
        repo["name"] for repo in repositories
    ]

    existing_descriptions = [
        {
            "name": repo["name"],
            "description": repo.get("description") or ""
        }
        for repo in repositories
    ]

    prompt = f"""
Create ONE complete, playable browser game for GitHub.

Existing repositories:
{json.dumps(existing_descriptions)}

GAME CATEGORIES:
- Arcade: Snake, Breakout, retro games
- Racing: car racing, obstacle racing
- Action: space shooter, survival games
- Puzzle: Sudoku, 2048, memory games
- Strategy: chess, checkers, tower defense
- Adventure: platformers, treasure hunts
- Sports: cricket, football, basketball
- Brain games: quizzes, word puzzles
- Simulation: farming, city building
- RPG: quests, inventory, character progression
- 3D: simple 3D racing or exploration
- Casual: endless runner, clicker games

Choose a suitable category and create a different game
concept from existing projects.

TECHNICAL REQUIREMENTS:
- Use HTML, CSS and JavaScript for a browser game.
- Use Canvas when appropriate for 2D games.
- Use Three.js only when a 3D game genuinely needs it.
- Generate a complete, playable implementation.
- Include responsive design for desktop and mobile.
- Include start, restart and game-over functionality.
- Add score tracking when appropriate.
- Include keyboard or touch controls as appropriate.
- Include a README.md with gameplay and run instructions.
- Include all necessary source files.
- Include between 5 and 8 useful files.
- Do not include real credentials or API keys.
- Do not create cloud infrastructure automatically.
- Do not use placeholder implementations.
- Avoid duplicating existing repository names or game concepts.
- Keep dependencies minimal.

Return ONLY a valid JSON object using this structure:

{{
  "name": "unique-game-name",
  "description": "Short description of the game",
  "files": {{
    "README.md": "Complete README content",
    "index.html": "Complete HTML source",
    "style.css": "Complete CSS source",
    "game.js": "Complete JavaScript source",
    "package.json": "Only if required"
  }}
}}

Return between 5 and 8 files.

JSON RULES:
- Return valid JSON only.
- Escape quotation marks and newlines correctly.
- Do not use Markdown code fences.
- Do not omit required source code.
- Ensure the game can run using the instructions in README.md.
"""

    print("Requesting a new browser game from Groq...")

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an experienced browser game developer. "
                    "Generate complete, playable HTML, CSS and "
                    "JavaScript games. Return valid JSON only. "
                    "Never include real credentials."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0.8,
        max_tokens=12000,
    )

    choice = response.choices[0]
    content = (choice.message.content or "").strip()

    if choice.finish_reason == "length":
        raise RuntimeError(
            "AI response was truncated. "
            "No repository has been created."
        )

    if content.startswith("```"):
        content = re.sub(
            r"^```(?:json)?\s*",
            "",
            content,
        )
        content = re.sub(r"\s*```$", "", content)

    try:
        project = json.loads(content)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "The AI returned invalid JSON. "
            f"Line {exc.lineno}, column {exc.colno}. "
            "No repository has been created."
        ) from exc

    if not isinstance(project, dict):
        raise RuntimeError("AI response must be a JSON object.")

    name = project.get("name", "")
    description = project.get("description", "")
    files = project.get("files", {})

    if not isinstance(name, str) or not re.fullmatch(
        r"[a-z0-9]+(?:-[a-z0-9]+)*",
        name,
    ):
        raise RuntimeError("Invalid game repository name.")

    if not isinstance(description, str) or not description.strip():
        raise RuntimeError("Invalid game description.")

    if not isinstance(files, dict) or not 5 <= len(files) <= 8:
        raise RuntimeError(
            "Expected between 5 and 8 game files."
        )

    required_files = {"README.md", "index.html", "game.js", "style.css"}

    if not required_files.issubset(files):
        raise RuntimeError(
            "The game must include README.md, index.html, "
            "style.css and game.js."
        )

    duplicate = find_duplicate_project(
        name,
        description,
        repositories,
    )

    if duplicate:
        print(
            f"Duplicate repository detected: {duplicate}. "
            "No repository will be created."
        )
        return None

    for filename, file_content in files.items():
        if not isinstance(filename, str):
            raise RuntimeError("Invalid game filename.")

        path = Path(filename)

        if (
            path.is_absolute()
            or ".." in path.parts
            or not path.parts
            or not isinstance(file_content, str)
            or not file_content.strip()
        ):
            raise RuntimeError(
                f"Invalid or unsafe game file: {filename}"
            )

        if path.parts[0] == ".git":
            raise RuntimeError(
                "Generated games cannot contain .git files."
            )

        secret_patterns = [
            r"AKIA[0-9A-Z]{16}",
            r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
            r"gh[pousr]_[A-Za-z0-9_]{20,}",
            r"sk-[A-Za-z0-9]{20,}",
        ]

        for pattern in secret_patterns:
            if re.search(pattern, file_content):
                raise RuntimeError(
                    f"Potential secret detected in {filename}. "
                    "Nothing will be published."
                )

    project_dir = PROJECTS_DIR / name

    if project_dir.exists():
        raise RuntimeError(
            f"Game directory already exists: {name}"
        )

    project_dir.mkdir(
        parents=True,
        exist_ok=False,
    )

    for filename, file_content in files.items():
        destination = project_dir / filename
        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        destination.write_text(
            file_content,
            encoding="utf-8",
        )

    print(f"Game generated: {name}")
    print(f"Files generated: {len(files)}")

    return name, description, project_dir
