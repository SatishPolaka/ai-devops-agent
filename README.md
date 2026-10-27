# AI DevOps Agent 🚀

An AI-powered agent designed to generate practical DevOps projects and publish them to GitHub through a manually triggered GitHub Actions workflow.

## Project Objective

The goal is to build an AI agent that helps maintain a professional GitHub profile by creating medium-sized, practical DevOps projects suitable for an engineer with 4+ years of experience.

The agent will focus on AWS, Azure, Docker, Kubernetes, Jenkins, Terraform, Ansible, and CI/CD automation.

## Current Features

* Python-based AI agent.
* Groq API integration for AI-generated content.
* GitHub Actions workflow triggered manually.
* Automated generation of DevOps project documentation.
* API credentials stored using GitHub Secrets.

## Current Workflow

```text
Manual Workflow Trigger
        |
        v
GitHub Actions
        |
        v
Install Python Dependencies
        |
        v
Run agent.py
        |
        v
Call Groq AI API
        |
        v
Generate README.md
```

**Current limitation:** The agent generates a README file in the temporary GitHub Actions environment. It does not yet generate complete project files or publish projects to separate GitHub repositories.

## Repository Structure

```text
ai-devops-agent/
├── agent.py
├── requirements.txt
├── README.md
└── .github/
    └── workflows/
        └── agent.yml
```

## Technologies

* Python
* Groq API
* GitHub
* GitHub Actions
* OpenAI-compatible Python SDK

## How to Run

1. Open the repository on GitHub.
2. Select the Actions tab.
3. Choose AI DevOps Agent.
4. Click Run workflow.
5. Select the branch and confirm.
6. Review the workflow logs.

The workflow runs only when manually triggered. No scheduled execution is configured.

## GitHub Secrets

Configure the following secrets under **Settings → Secrets and variables → Actions**.

| Secret         | Purpose                                                        |
| -------------- | -------------------------------------------------------------- |
| `GROQ_API_KEY` | Authenticates requests to the Groq API.                        |
| `GH_TOKEN`     | Intended for future GitHub repository creation and publishing. |

Never hardcode credentials in source files or commit them to GitHub.

## Planned Improvements

### 1. Complete Project Generation

Generate actual project files, including:

* Terraform configurations.
* Dockerfiles and Docker Compose files.
* Jenkins pipelines.
* Kubernetes manifests.
* Ansible playbooks.
* GitHub Actions workflows.
* AWS and Azure deployment examples.

Projects should include implementation instructions, validation steps, security practices, and cleanup instructions where applicable.

### 2. Automatic GitHub Publishing

Create a dedicated repository for each new project and upload the generated files.

### 3. Duplicate Prevention

Before creating a repository:

* Inspect existing repositories.
* Compare project names and scope.
* Avoid creating duplicate projects.
* Update an existing project when appropriate.
* Report the result if a duplicate is detected.

### 4. GitHub Profile Maintenance

Maintain the profile README with accurate technical skills, featured projects, and links to completed repositories.

### 5. Validation and Security

Before publishing:

* Check for exposed secrets.
* Validate YAML and configuration files.
* Run applicable Terraform checks.
* Review Dockerfiles and deployment configurations.
* Report failures instead of publishing broken projects.

## Expected Final Workflow

```text
Manually Trigger Workflow
        |
        v
Inspect GitHub Repositories
        |
        v
Check for Duplicates
        |
        v
Generate Complete DevOps Project
        |
        v
Validate Files and Security
        |
        v
Create GitHub Repository
        |
        v
Upload Project Files
        |
        v
Update Profile When Needed
        |
        v
Report Results
```

## Implementation Status

| Feature                            | Status    |
| ---------------------------------- | --------- |
| Python agent                       | Completed |
| Groq integration                   | Completed |
| Manual GitHub Actions execution    | Completed |
| README generation                  | Completed |
| Complete DevOps project generation | Pending   |
| GitHub repository creation         | Pending   |
| Automatic project publishing       | Pending   |
| Duplicate detection                | Pending   |
| Automated validation               | Pending   |
| Profile README maintenance         | Pending   |

## Goal

Build a reliable AI agent that generates useful, medium-sized DevOps projects, prevents duplicates, validates project files, and publishes them to GitHub only when manually triggered.

The focus is on genuine technical contributions that demonstrate practical engineering skills and help recruiters evaluate the projects.
