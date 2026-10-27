import os
import json
import re
from pathlib import Path

import requests
from openai import OpenAI


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

GITHUB_TOKEN = os.environ["GH_TOKEN"]
GITHUB_USERNAME = "SatishPolaka"

GROQ_API_KEY = os.environ["GROQ_API_KEY"]
MODEL = "openai/gpt-oss-120b"

PROJECTS_DIR = Path("generated-projects")

GITHUB_API = "https://api.github.com"

GITHUB_HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1",
)


# --------------------------------------------------
# GITHUB API
# --------------------------------------------------

def github_request(method, endpoint, **kwargs):
    """Make a GitHub API request and report useful errors."""

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
            f"{response.text[:1000]}"
        )

    if response.status_code == 204:
        return {}

    return response.json()


def get_existing_repositories():
    """Fetch repositories owned by the authenticated user."""

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
        page += 1

    return repositories


# --------------------------------------------------
# DUPLICATE CHECKING
# --------------------------------------------------

def find_duplicate_project(name, description, repositories):
    """Check names and descriptions for likely duplicates."""

    name_normalized = name.lower().replace("-", " ")

    for repo in repositories:
        existing_name = repo["name"].lower()
        existing_description = (
            repo.get("description") or ""
        ).lower()

        if existing_name == name.lower():
            return repo["name"]

        existing_normalized = existing_name.replace("-", " ")

        if existing_normalized == name_normalized:
            return repo["name"]

        if (
            description
            and existing_description
            and existing_description == description.lower()
        ):
            return repo["name"]

    return None


# --------------------------------------------------
# PROJECT GENERATION
# --------------------------------------------------

def generate_project(repositories):
    """Generate a medium-sized DevOps project using AI."""

    existing_names = [
        repo["name"] for repo in repositories
    ]

    prompt = f"""
Create ONE practical AWS DevOps project suitable for an
engineer with 4+ years of experience.

Existing repositories:
{json.dumps(existing_names)}

Project requirements:
- Generate 5 to 7 useful files.
- Include a complete README.md.
- Include a Dockerfile.
- Include docker-compose.yml when appropriate.
- Include a Jenkinsfile or GitHub Actions workflow.
- Include Terraform or Kubernetes files when appropriate.
- Include real implementation code, not placeholders.
- Include setup, testing, security, and cleanup instructions.
- Do not include real credentials.
- Do not automatically create cloud infrastructure.
- Keep the implementation medium-sized and maintainable.
- Avoid projects equivalent to the existing repositories.

Return ONLY a valid JSON object in this format:

{{
  "name": "unique-kebab-case-name",
  "description": "Short project description",
  "files": {{
    "README.md": "Complete README content",
    "Dockerfile": "Complete Dockerfile content"
  }}
}}

Return between 5 and 7 files.

JSON requirements:
- Escape quotation marks correctly.
- Represent newlines inside strings as \\n.
- Do not use Markdown code fences.
- Return the complete JSON object.
"""

    print("Requesting a DevOps project from Groq...")

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You generate practical DevOps project files. "
                    "Return only valid JSON. Keep responses concise. "
                    "Never include real credentials."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0.2,
        max_tokens=12000,
    )

    choice = response.choices[0]
    content = (choice.message.content or "").strip()

    if choice.finish_reason == "length":
        raise RuntimeError(
            "AI response was truncated. "
            "Run the workflow again to request another project."
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

    if not isinstance(name, str):
        raise RuntimeError("Invalid project name.")

    if not re.fullmatch(
        r"[a-z0-9]+(?:-[a-z0-9]+)*",
        name,
    ):
        raise RuntimeError(
            f"Invalid repository name returned by AI: {name}"
        )

    if not isinstance(description, str):
        raise RuntimeError("Invalid project description.")

    if not isinstance(files, dict) or not 5 <= len(files) <= 7:
        raise RuntimeError(
            "Expected between 5 and 7 project files."
        )

    if "README.md" not in files:
        raise RuntimeError("Project must include README.md.")

    duplicate = find_duplicate_project(
        name,
        description,
        repositories,
    )

    if duplicate:
        print(
            f"Duplicate detected: {duplicate}. "
            "No repository will be created."
        )
        return None

    # Validate every path and file before writing anything.
    for filename, file_content in files.items():

        if not isinstance(filename, str):
            raise RuntimeError("Invalid project filename.")

        path = Path(filename)

        if (
            path.is_absolute()
            or ".." in path.parts
            or not path.parts
            or not isinstance(file_content, str)
            or not file_content.strip()
        ):
            raise RuntimeError(
                f"Invalid or unsafe project file: {filename}"
            )

        if path.parts[0] == ".git":
            raise RuntimeError(
                "Generated projects cannot contain .git files."
            )

        # Basic checks for obvious hardcoded secrets.
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

    # Save the project locally in the runner.
    project_dir = PROJECTS_DIR / name

    if project_dir.exists():
        raise RuntimeError(
            f"Project directory already exists: {name}"
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

    print(f"Project generated: {name}")
    print(f"Files generated: {len(files)}")

    return name, description, project_dir


# --------------------------------------------------
# GITHUB REPOSITORY CREATION
# --------------------------------------------------

def create_repository(name, description):
    """Create a new public GitHub repository."""

    # Check again immediately before creating the repository.
    repositories = get_existing_repositories()

    duplicate = find_duplicate_project(
        name,
        description,
        repositories,
    )

    if duplicate:
        print(
            f"Repository already exists: {duplicate}. "
            "Publishing cancelled."
        )
        return None

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

    print(f"Created repository: {repository['html_url']}")

    return repository


# --------------------------------------------------
# PROJECT UPLOAD
# --------------------------------------------------

def upload_project(repository, project_dir):
    """Upload generated files in one Git commit."""

    owner = repository["owner"]["login"]
    name = repository["name"]

    branch = repository["default_branch"]

    reference = github_request(
        "GET",
        f"/repos/{owner}/{name}/git/ref/heads/{branch}",
    )

    parent_sha = reference["object"]["sha"]

    parent_commit = github_request(
        "GET",
        f"/repos/{owner}/{name}/git/commits/{parent_sha}",
    )

    parent_tree_sha = parent_commit["tree"]["sha"]

    tree = []

    for path in sorted(project_dir.rglob("*")):

        if not path.is_file():
            continue

        relative_path = path.relative_to(
            project_dir
        ).as_posix()

        content = path.read_text(
            encoding="utf-8",
        )

        blob = github_request(
            "POST",
            f"/repos/{owner}/{name}/git/blobs",
            json={
                "content": content,
                "encoding": "utf-8",
            },
        )

        tree.append({
            "path": relative_path,
            "mode": "100644",
            "type": "blob",
            "sha": blob["sha"],
        })

    if not tree:
        raise RuntimeError("No project files to upload.")

    new_tree = github_request(
        "POST",
        f"/repos/{owner}/{name}/git/trees",
        json={
            "base_tree": parent_tree_sha,
            "tree": tree,
        },
    )

    commit = github_request(
        "POST",
        f"/repos/{owner}/{name}/git/commits",
        json={
            "message": "Add generated DevOps project",
            "tree": new_tree["sha"],
            "parents": [parent_sha],
        },
    )

    github_request(
        "PATCH",
        f"/repos/{owner}/{name}/git/refs/heads/{branch}",
        json={
            "sha": commit["sha"],
            "force": False,
        },
    )

    print("Project files uploaded successfully.")
    print(f"Repository URL: {repository['html_url']}")


# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():
    print("AI DevOps Agent started.")
    print("Execution mode: Manual GitHub Actions trigger.")

    repositories = get_existing_repositories()

    print(f"Existing repositories found: {len(repositories)}")

    generated = generate_project(repositories)

    if generated is None:
        print("No project published.")
        return

    name, description, project_dir = generated

    repository = create_repository(
        name,
        description,
    )

    if repository is None:
        print("Duplicate detected. Nothing uploaded.")
        return

    upload_project(
        repository,
        project_dir,
    )

    print("AI DevOps Agent completed successfully.")


if __name__ == "__main__":
    main()
