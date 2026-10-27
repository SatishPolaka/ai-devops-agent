import os
import json
import re
from pathlib import Path
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["GROQ_API_KEY"],
    base_url="https://api.groq.com/openai/v1"
)

PROJECTS_DIR = Path("generated-projects")
MODEL = "openai/gpt-oss-120b"


def generate_project():
    prompt = """
Create one medium-sized, practical AWS DevOps project suitable
for an engineer with 4+ years of experience.

Project requirements:
- Include a README.md.
- Include a Dockerfile and docker-compose.yml where appropriate.
- Include a Jenkinsfile or GitHub Actions workflow.
- Include Terraform or Kubernetes manifests where appropriate.
- Include configuration and validation files when useful.
- Include deployment instructions and cleanup steps.
- Use secure practices.
- Never include real credentials.
- Keep the project practical and reasonably sized.

Return ONLY valid JSON in this format:
{
  "name": "short-kebab-case-project-name",
  "description": "short project description",
  "files": {
    "README.md": "file content",
    "Dockerfile": "file content"
  }
}

Generate at least 5 useful files.
Do not include Markdown code fences around the JSON.
"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4
    )

    content = response.choices[0].message.content.strip()

    content = re.sub(r"^```(?:json)?\s*", "", content)
    content = re.sub(r"\s*```$", "", content)

    project = json.loads(content)

    name = project["name"]

    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
        raise ValueError("Invalid project name returned by AI")

    files = project.get("files", {})

    if len(files) < 5:
        raise ValueError("Generated project has fewer than 5 files")

    project_dir = PROJECTS_DIR / name

    # Avoid overwriting a previously generated project.
    if project_dir.exists():
        print(f"Project already exists locally: {name}")
        return

    for filename, file_content in files.items():
        relative_path = Path(filename)

        if (
            relative_path.is_absolute()
            or ".." in relative_path.parts
            or not isinstance(file_content, str)
        ):
            raise ValueError(f"Unsafe project file: {filename}")

    project_dir.mkdir(parents=True, exist_ok=False)

    for filename, file_content in files.items():
        destination = project_dir / filename
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(file_content, encoding="utf-8")

    print(f"Project generated: {name}")
    print(f"Files created: {len(files)}")
    print(f"Location: {project_dir}")


if __name__ == "__main__":
    generate_project()
