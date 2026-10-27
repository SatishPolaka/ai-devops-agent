import os
from openai import OpenAI

# Connect to Groq using its API key
client = OpenAI(
    api_key=os.environ["GROQ_API_KEY"],
    base_url="https://api.groq.com/openai/v1"
)


def generate_devops_project():
    prompt = """
    Create a practical AWS DevOps project README.

    Include:
    1. Project title and overview
    2. Architecture
    3. Technologies used
    4. Implementation steps
    5. Example commands
    6. Security best practices
    7. Cleanup instructions

    Do not include passwords, API keys, or credentials.
    Return only the README content.
    """

    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.7
    )

    project_readme = response.choices[0].message.content

    with open("README.md", "w", encoding="utf-8") as file:
        file.write(project_readme)

    print("DevOps project README generated successfully!")


if __name__ == "__main__":
    generate_devops_project()
