import os
from openai import OpenAI

# Connect to OpenAI using the API key stored in GitHub Secrets
client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY")
)


def generate_devops_project():
    prompt = """
    Create a practical DevOps project for an AWS DevOps Engineer.

    Requirements:
    - Choose a useful real-world DevOps project.
    - Include a project title and overview.
    - Explain the architecture.
    - List the technologies used.
    - Provide implementation steps.
    - Include example commands where appropriate.
    - Include security best practices.
    - Write a complete README.md.
    - Do not include real passwords, API keys, or credentials.
    """

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt
    )

    project_readme = response.output_text

    with open("README.md", "w", encoding="utf-8") as file:
        file.write(project_readme)

    print("DevOps project README generated successfully!")


if __name__ == "__main__":
    generate_devops_project()
