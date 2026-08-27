# GitHub GPU runner assessment

## Current repository state

The repository currently contains `.github/workflows/fish-s2-dubbing.yml`. Its job uses `runs-on: [self-hosted, linux, x64, gpu]`, so GitHub has already queued the job for a self-hosted runner. A queued job is expected while no runner with all four labels is online; the workflow itself does not create a GPU machine.

## What GitHub provides

GitHub documents GPU-powered larger runners as an organization or enterprise feature rather than a standard free repository runner. GitHub's hosted-runners documentation says that GPU-powered runners are available when the account is on GitHub Team or GitHub Enterprise Cloud, and the July 2024 announcement describes T4 access through GPU larger runners. These runners are managed and billed by GitHub; they are not a free GPU attached to an individual repository.

References:

1. https://docs.github.com/actions/using-github-hosted-runners/about-github-hosted-runners — GitHub-hosted runners.
2. https://github.blog/changelog/2024-07-08-github-actions-gpu-hosted-runners-are-now-generally-available/ — GPU hosted runners announcement.
3. https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/use-in-a-workflow — self-hosted labels and routing.

## Practical options

| Approach | What it provides | Cost / limitation | Suitability for dub22 |
|---|---|---|---|
| GitHub-hosted GPU larger runner | Fully managed T4-class runner selected through an organization/enterprise runner group | Requires eligible GitHub plan and paid Actions usage; do not enable billing without user confirmation | Cleanest production path if paid GPU Actions are acceptable |
| Self-hosted GPU runner | GitHub dispatches jobs to a GPU machine labeled `self-hosted, linux, x64, gpu` | Requires an always-on GPU machine; the current workflow remains queued until one is registered | Best reusable path; can be a rented GPU VM or the user's own GPU |
| Colab-hosted self-hosted runner | A Colab T4 session temporarily registers as the GitHub runner | Session expires/disconnects; requires manual GPU runtime selection and a short-lived runner token; not persistent | Lowest-cost experiment, not a reliable production runner |
| Direct Colab/Kaggle notebook | Runs the model without GitHub Actions runner registration | Manual execution and platform availability limits | Current safest free validation route |

## Recommendation

Do not claim that GitHub itself has been converted into a GPU. The repository can be made GPU-ready by adding a SILMA workflow and a runner bootstrap script, but a real GPU runner must be registered separately. For a free experiment, use a temporary Colab T4 self-hosted runner. For reliable repeated jobs, use a dedicated GPU VM or GitHub's paid larger runner feature.

## Security constraint

Never commit a GitHub Personal Access Token or runner registration token. Registration tokens are short-lived and should be entered into a private runtime session or passed as a secret. Workflows triggered by untrusted pull requests must not be allowed to execute arbitrary repository code on a persistent self-hosted runner.
