import os
import json
import re
from pathlib import Path

import requests
from openai import OpenAI

# Configuration
GITHUB_TOKEN = os.environ["GH_TOKEN"]
GITHUB_USERNAME = "SatishPolaka"
MODEL = "openai/gpt-oss-120b"

client = OpenAI(
    api_key=os.environ["GROQ_API_KEY"],
    base_url="https://api.groq.com/openai/v1",
)

github_headers = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

PROJECTS_DIR = Path("generated-projects")


def get_existing_repositories():
    """Read existing repository names to avoid duplicates."""
    repositories = []
    page = 1

    while True:
        response = requests.get(
            f"https://api.github.com/user/repos"
            f"?visibility=all&affiliation=owner&per_page=100&page={page}",
            headers=github_headers,
            timeout=30,
        )
        response.raise_for_status()

        batch = response.json()
        if not batch:
            break

        repositories.extend(batch)
        page += 1

    return repositories


def generate_project(existing_repositories):
    """Ask AI to generate a medium-sized DevOps project."""
    existing_names = [
        repo["name"] for repo in existing_repositories
    ]

    prompt = f"""
Create one practical, medium-sized AWS DevOps project
suitable for an engineer with 4+ years of experience.

Use a project name that is different from these existing
GitHub repositories:
{json.dumps(existing_names)}

Requirements:
- Generate 5 to 8 useful project files.
- Include README.md with architecture and setup instructions.
- Include real implementation files, not placeholders.
- Choose suitable technologies such as Terraform, Docker,
  Jenkins, Kubernetes, or GitHub Actions.
- Include validation and cleanup instructions.
- Do not include credentials or real secrets.
- Keep the scope manageable.
- Do not create AWS resources automatically.

Return ONLY valid JSON:
{{
  "name": "unique-kebab-case-name",
  "description": "short description",
  "files": {{
    "README.md": "complete README content",
    "Dockerfile": "complete file content"
  }}
}}

Return at least 5 files. Do not use Markdown fences
around the JSON.
"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
    )

    content = response.choices[0].message.content.strip()

    content = re.sub(r"^```(?:json)?\s*", "", content)
    content = re.sub(r"\s*```$", "", content)

    project = json.loads(content)

    name = project.get("name", "")
    description = project.get("description", "")
    files = project.get("files", {})

    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
        raise ValueError("AI returned an invalid repository name.")

    if not isinstance(files, dict) or len(files) < 5:
        raise ValueError("AI must generate at least 5 project files.")

    existing_names_lower = {
        repo["name"].lower() for repo in existing_repositories
    }

    if name.lower() in existing_names_lower:
        print(f"Repository already exists: {name}. Nothing published.")
        return

    # Validate all paths before writing any files.
    for filename, file_content in files.items():
        path = Path(filename)

        if (
            not isinstance(filename, str)
            or path.is_absolute()
            or ".." in path.parts
            or not isinstance(file_content, str)
        ):
            raise ValueError(f"Unsafe or invalid project file: {filename}")

    project_dir = PROJECTS_DIR / name
    project_dir.mkdir(parents=True, exist_ok=False)

    for filename, file_content in files.items():
        destination = project_dir / filename
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(file_content, encoding="utf-8")

    print(f"Generated project: {name}")
    print(f"Description: {description}")
    print(f"Files generated: {len(files)}")

    return name, description, project_dir


def publish_project(name, description, project_dir):
    """Create a public repository and upload project files."""
    # Create the repository only after generation succeeds.
    response = requests.post(
        "https://api.github.com/user/repos",
        headers=github_headers,
        json={
            "name": name,
            "description": description[:350],
            "private": False,
            "auto_init": True,
        },
        timeout=30,
    )
    response.raise_for_status()

    repository = response.json()
    branch = repository["default_branch"]

    # Wait until the initial branch exists before uploading.
    tree = []

    for path in sorted(project_dir.rglob("*")):
        if not path.is_file():
            continue

        relative_path = path.relative_to(project_dir).as_posix()

        content = path.read_text(encoding="utf-8")

        blob_response = requests.post(
            "https://api.github.com/repos/"
            f"{GITHUB_USERNAME}/{name}/git/blobs",
            headers=github_headers,
            json={
                "content": content,
                "encoding": "utf-8",
            },
            timeout=30,
        )
        blob_response.raise_for_status()

        tree.append({
            "path": relative_path,
            "mode": "100644",
            "type": "blob",
            "sha": blob_response.json()["sha"],
        })

    reference_response = requests.get(
        f"https://api.github.com/repos/"
        f"{GITHUB_USERNAME}/{name}/git/ref/heads/{branch}",
        headers=github_headers,
        timeout=30,
    )
    reference_response.raise_for_status()
    parent_sha = reference_response.json()["object"]["sha"]

    parent_commit_response = requests.get(
        f"https://api.github.com/repos/"
        f"{GITHUB_USERNAME}/{name}/git/commits/{parent_sha}",
        headers=github_headers,
        timeout=30,
    )
    parent_commit_response.raise_for_status()
    parent_tree_sha = parent_commit_response.json()["tree"]["sha"]

    tree_response = requests.post(
        f"https://api.github.com/repos/"
        f"{GITHUB_USERNAME}/{name}/git/trees",
        headers=github_headers,
        json={
            "base_tree": parent_tree_sha,
            "tree": tree,
        },
        timeout=30,
    )
    tree_response.raise_for_status()

    commit_response = requests.post(
        f"https://api.github.com/repos/"
        f"{GITHUB_USERNAME}/{name}/git/commits",
        headers=github_headers,
        json={
            "message": "Add generated DevOps project",
            "tree": tree_response.json()["sha"],
            "parents": [parent_sha],
        },
        timeout=30,
    )
    commit_response.raise_for_status()

    update_response = requests.patch(
        f"https://api.github.com/repos/"
        f"{GITHUB_USERNAME}/{name}/git/refs/heads/{branch}",
        headers=github_headers,
        json={
            "sha": commit_response.json()["sha"],
            "force": False,
        },
        timeout=30,
    )
    update_response.raise_for_status()

    print(f"Project published successfully: {repository['html_url']}")


def main():
    existing_repositories = get_existing_repositories()

    generated = generate_project(existing_repositories)

    if not generated:
        return

    name, description, project_dir = generated

    publish_project(name, description, project_dir)


if __name__ == "__main__":
    main()
