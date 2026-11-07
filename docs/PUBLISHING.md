# Publish and verify the repository

## Current state
A complete local repository is prepared. **No authorized GitHub publishing access was available, and no public repository URL is claimed.** The workspace preview is not a public GitHub submission. No credentials are included.

## Owner commands — GitHub CLI option
Install Git and GitHub CLI on the owner's computer, download/unzip the project, enter its root, and inspect its contents. Authentication is interactive and must be done by the owner; do not paste a token into source files or chat.

```bash
cd PranaGuard-COPD-Digital-Twin
gh auth login
# The delivered folder may already include local Git history. Initialize only if absent:
if [ ! -d .git ]; then git init -b main; fi
# Configure your own identity if Git asks (do not invent an author).
git add .
git diff --cached --check
git status --short
# Commit only when there are staged changes:
git diff --cached --quiet || git commit -m "Prepare verified PranaGuard research prototype"
gh repo create PranaGuard-COPD-Digital-Twin --public --source=. --remote=origin --push
# Read the real created URL and visibility; do not substitute a guessed username:
gh repo view --json url,visibility
```

If that repository already exists, inspect it rather than overwriting:
```bash
gh repo view PranaGuard-COPD-Digital-Twin --json url,visibility
# If this is the intended repository, use its actual URL:
git remote add origin "ACTUAL_URL_RETURNED_BY_GITHUB"
git push -u origin main
```
`ACTUAL_URL_RETURNED_BY_GITHUB` is a command placeholder, not a real project URL. Do not execute it unchanged. If an origin is already configured, inspect it with `git remote -v` before changing anything.

## Browser-only creation option
Create a **public** repository named `PranaGuard-COPD-Digital-Twin` on the owner's GitHub account without generating an extra initial README/license. Copy the actual URL shown by GitHub, then run the remote/push commands using that real URL. Private must not be selected. No organization/repository ID has been guessed.

## Insert the final, actual URLs
1. Fill team, member and institution fields in `submission_metadata.json`.
2. Set `public_repository_url` to the real URL returned by GitHub.
3. Record/upload the real demo; set `unlisted_youtube_url` and `video_duration_minutes` after verifying them.
4. Run `python -m scripts.write_documentation`; verify README video/publishing sections. Update VIDEO_STATUS.md and editable slide1 (or regenerate the deck after metadata is filled).
5. Run tests, build and artifact checks; commit/push the final documents and metadata.
6. Run `python -m scripts.verify_submission --check-public` without an authentication token in requests. Inspect `docs/verification/PUBLIC_ACCESS.md`.
7. Open the public repository, README images, architecture PDF/PPTX and presentation PDF/PPTX in an incognito/signed-out browser. Download and open the Office/PDF files as well as checking HTTP status.
8. Play the actual YouTube video signed out, verify visibility/duration/audio, and document that manual check. HTTP200 alone does not prove playable public access.
9. Commit/push final audit evidence and re-evaluate every mandatory checklist item before submitting on Unstop.

## Do not commit
The supplied `.gitignore` excludes virtual environments, node_modules, runtime SQLite files, `.env`, caches and generated frontend bundles. Keep source data attribution and the small licensed caches/models. Never commit tokens, credential stores, private patient data, restricted datasets or uploaded account cookies. Review `git diff --cached` and the secret-scan output before pushing.
