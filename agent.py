import os
import re
import json
import base64
from pathlib import Path

import requests
from openai import OpenAI


# ==========================================================
# CONFIGURATION
# ==========================================================

GITHUB_TOKEN = os.environ["GH_TOKEN"]
GROQ_API_KEY = os.environ["GROQ_API_KEY"]

GITHUB_API = "https://api.github.com"
MODEL = "openai/gpt-oss-120b"

PROJECTS_DIR = Path("generated-projects")

GITHUB_HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1",
)


# ==========================================================
# GITHUB API HELPER
# ==========================================================

def github_request(method, endpoint, **kwargs):
    """Call GitHub API and report errors clearly."""

    response = requests.request(
        method,
        f"{GITHUB_API}{endpoint}",
        headers=GITHUB_HEADERS,
        timeout=60,
        **kwargs,
    )

    if not response.ok:
        raise RuntimeError(
            f"GitHub API error {response.status_code}: "
            f"{response.text[:1500]}"
        )

    if response.status_code == 204:
        return {}

    return response.json()


# ==========================================================
# VERIFY GITHUB AUTHENTICATION
# ==========================================================

def verify_github_account():
    """Identify the account associated with GH_TOKEN."""

    print("Checking GitHub authentication...", flush=True)

    user = github_request("GET", "/user")

    print(
        f"Authenticated GitHub account: {user['login']}",
        flush=True,
    )

    return user["login"]


# ==========================================================
# EXISTING REPOSITORIES
# ==========================================================

def get_existing_repositories():
    """Retrieve repositories owned by the authenticated user."""

    repositories = []
    page = 1

    while True:
        batch = github_request(
            "GET",
            "/user/repos",
            params={
                "visibility": "all",
                "affiliation": "owner",
                "per_page": 100,
                "page": page,
                "sort": "created",
                "direction": "desc",
            },
        )

        if not batch:
            break

        repositories.extend(batch)

        if len(batch) < 100:
            break

        page += 1

    return repositories


# ==========================================================
# DUPLICATE CHECK
# ==========================================================

def find_duplicate_project(name, description, repositories):
    """Detect duplicate repository names and exact descriptions."""

    normalized_name = name.lower().replace("-", " ").strip()
    normalized_description = description.lower().strip()

    for repo in repositories:
        existing_name = repo.get("name", "")
        existing_description = (
            repo.get("description") or ""
        ).lower().strip()

        if existing_name.lower() == name.lower():
            return existing_name

        existing_normalized = (
            existing_name.lower().replace("-", " ").strip()
        )

        if existing_normalized == normalized_name:
            return existing_name

        if (
            normalized_description
            and existing_description
            and normalized_description == existing_description
        ):
            return existing_name

    return None


# ==========================================================
# AI GAME GENERATION
# ==========================================================

def generate_project(repositories):
    """Generate a browser game using Groq."""

    existing_projects = [
        {
            "name": repo.get("name", ""),
            "description": repo.get("description") or "",
        }
        for repo in repositories
    ]

    prompt = f"""
Create ONE complete and playable browser game.

EXISTING GITHUB PROJECTS:
{json.dumps(existing_projects)}

Choose a game category and create a new concept.

SUPPORTED CATEGORIES:

1. Arcade: Snake, Breakout, retro arcade
2. Racing: car racing, bike racing, obstacle racing
3. Action: space shooter, survival
4. Puzzle: 2048, Sudoku, memory puzzles
5. Strategy: checkers, tower defense
6. Adventure: platformers, treasure hunts
7. Sports: cricket, football, basketball
8. Brain games: quizzes, word puzzles
9. Simulation: farming, city building
10. RPG: quests, inventory, character progression
11. Casual: endless runners, clicker games
12. 3D: simple 3D racing or exploration
13. Two-player local games
14. Retro pixel games

TECHNICAL REQUIREMENTS:

- Use HTML, CSS and JavaScript.
- Generate a complete playable browser game.
- Use Canvas for 2D graphics when appropriate.
- Use Three.js only when necessary for 3D.
- Include responsive desktop and mobile layouts.
- Include start and restart functionality.
- Include score tracking when appropriate.
- Include keyboard or touch controls as appropriate.
- Include game-over and win states when appropriate.
- Use original game logic and a consistent visual design.
- Include README.md with installation and gameplay instructions.
- Include index.html, style.css and game.js.
- Include additional useful files to reach 5 to 8 files.
- Keep external dependencies minimal.
- Do not include real credentials or API keys.
- Do not create cloud infrastructure automatically.
- Do not use placeholder code.
- Do not copy an existing repository's game concept.
- Do not reuse an existing repository name.

RETURN ONLY VALID JSON in this structure:

{{
  "name": "unique-game-name",
  "description": "Short game description",
  "files": {{
    "README.md": "Complete documentation",
    "index.html": "Complete HTML",
    "style.css": "Complete CSS",
    "game.js": "Complete JavaScript",
    "assets/game.svg": "SVG source if appropriate"
  }}
}}

Return between 5 and 8 files.

The files dictionary must contain:
README.md
index.html
style.css
game.js

JSON rules:
- Return one valid JSON object.
- Escape quotation marks and newlines correctly.
- Do not use Markdown fences.
- Do not omit source code.
- Ensure local file paths work together.
- Do not include binary data.
"""

    print("Requesting a game from Groq AI...", flush=True)

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an experienced browser game developer. "
                    "Create original, playable browser games. "
                    "Return valid JSON only. Never include credentials."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0.7,
        max_tokens=12000,
    )

    choice = response.choices[0]
    content = (choice.message.content or "").strip()

    print(
        f"AI response received. Finish reason: "
        f"{choice.finish_reason}",
        flush=True,
    )

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
            "Groq returned invalid JSON. "
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
        raise RuntimeError(
            f"Invalid repository name returned by AI: {name}"
        )

    if not isinstance(description, str) or not description.strip():
        raise RuntimeError("AI returned an empty description.")

    if not isinstance(files, dict) or not 5 <= len(files) <= 8:
        raise RuntimeError(
            f"Expected 5 to 8 files; received "
            f"{len(files) if isinstance(files, dict) else 'invalid data'}."
        )

    required_files = {
        "README.md",
        "index.html",
        "style.css",
        "game.js",
    }

    if not required_files.issubset(files):
        raise RuntimeError(
            "The game must contain README.md, index.html, "
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
            "Generation cancelled.",
            flush=True,
        )
        return None

    secret_patterns = [
        r"AKIA[0-9A-Z]{16}",
        r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
        r"gh[pousr]_[A-Za-z0-9_]{20,}",
        r"sk-[A-Za-z0-9]{20,}",
    ]

    for filename, file_content in files.items():
        if not isinstance(filename, str):
            raise RuntimeError("Invalid filename returned by AI.")

        path = Path(filename)

        if (
            path.is_absolute()
            or ".." in path.parts
            or not path.parts
            or not isinstance(file_content, str)
            or not file_content.strip()
            or "\\" in filename
        ):
            raise RuntimeError(
                f"Invalid or unsafe generated file: {filename}"
            )

        if path.parts[0] in {".git", ".github"}:
            raise RuntimeError(
                f"Generated file path is not allowed: {filename}"
            )

        if path.suffix.lower() in {
            ".exe", ".dll", ".so", ".bin", ".pyc"
        }:
            raise RuntimeError(
                f"Unexpected binary file type: {filename}"
            )

        for pattern in secret_patterns:
            if re.search(pattern, file_content):
                raise RuntimeError(
                    f"Potential hardcoded secret in {filename}. "
                    "Publishing cancelled."
                )

    # Save generated files locally on the runner.
    project_dir = PROJECTS_DIR / name

    if project_dir.exists():
        raise RuntimeError(
            f"Generated project directory already exists: {name}"
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

    print(f"Game generated: {name}", flush=True)
    print(f"Files generated: {len(files)}", flush=True)

    return name, description, project_dir


# ==========================================================
# CREATE GITHUB REPOSITORY
# ==========================================================

def create_repository(owner, name, description):
    """Create a public repository under the authenticated account."""

    print(
        f"Creating GitHub repository: {name}",
        flush=True,
    )

    repository = github_request(
        "POST",
        "/user/repos",
        json={
            "name": name,
            "description": description[:350],
            "private": False,
            "auto_init": True,
        },
    )

    print(
        f"Repository created: {repository['html_url']}",
        flush=True,
    )

    return repository


# ==========================================================
# UPLOAD FILES USING GITHUB CONTENTS API
# ==========================================================

def upload_project(repository, project_dir):
    """Upload project files through the GitHub Contents API."""

    owner = repository["owner"]["login"]
    name = repository["name"]
    branch = repository["default_branch"]

    print(
        f"Uploading game files to {owner}/{name}...",
        flush=True,
    )

    for path in sorted(project_dir.rglob("*")):
        if not path.is_file():
            continue

        relative_path = path.relative_to(
            project_dir
        ).as_posix()

        encoded_path = requests.utils.quote(
            relative_path,
            safe="/",
        )

        endpoint = (
            f"/repos/{owner}/{name}/contents/{encoded_path}"
        )

        content = path.read_text(encoding="utf-8")

        payload = {
            "message": f"Add game file: {relative_path}",
            "content": base64.b64encode(
                content.encode("utf-8")
            ).decode("utf-8"),
            "branch": branch,
        }

        # The repository was initialized with a README.
        # Retrieve its SHA before replacing that file.
        existing = requests.get(
            f"{GITHUB_API}{endpoint}",
            headers=GITHUB_HEADERS,
            params={"ref": branch},
            timeout=60,
        )

        if existing.status_code == 200:
            existing_data = existing.json()

            if isinstance(existing_data, dict):
                existing_sha = existing_data.get("sha")

                if existing_sha:
                    payload["sha"] = existing_sha

        elif existing.status_code != 404:
            raise RuntimeError(
                f"Could not inspect {relative_path}: "
                f"HTTP {existing.status_code}: "
                f"{existing.text[:1000]}"
            )

        result = requests.put(
            f"{GITHUB_API}{endpoint}",
            headers=GITHUB_HEADERS,
            json=payload,
            timeout=60,
        )

        if not result.ok:
            raise RuntimeError(
                f"Upload failed for {relative_path}: "
                f"HTTP {result.status_code}: "
                f"{result.text[:1200]}"
            )

        print(
            f"Uploaded: {relative_path}",
            flush=True,
        )

    print("All game files uploaded successfully.", flush=True)
    print(
        f"Game repository URL: {repository['html_url']}",
        flush=True,
    )


# ==========================================================
# MAIN
# ==========================================================

def main():
    print("=" * 55, flush=True)
    print("AI GAME CREATOR STARTED", flush=True)
    print("Trigger: Manual GitHub Actions workflow", flush=True)
    print("=" * 55, flush=True)

    owner = verify_github_account()

    repositories = get_existing_repositories()

    print(
        f"Repositories found: {len(repositories)}",
        flush=True,
    )

    generated = generate_project(repositories)

    if generated is None:
        print(
            "No repository created because a duplicate was detected.",
            flush=True,
        )
        return

    name, description, project_dir = generated

    # Check again immediately before creating the repository.
    current_repositories = get_existing_repositories()

    duplicate = find_duplicate_project(
        name,
        description,
        current_repositories,
    )

    if duplicate:
        print(
            f"Repository already exists: {duplicate}. "
            "Publishing cancelled.",
            flush=True,
        )
        return

    repository = create_repository(
        owner,
        name,
        description,
    )

    upload_project(
        repository,
        project_dir,
    )

    print("=" * 55, flush=True)
    print("AI GAME CREATOR COMPLETED SUCCESSFULLY", flush=True)
    print(f"Game: {repository['html_url']}", flush=True)
    print("=" * 55, flush=True)


if __name__ == "__main__":
    main()
