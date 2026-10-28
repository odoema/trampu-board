# Trampu Launch Board

Public board for [Trampu](https://trampu.online), student-to-student ride sharing for Makerere MBA 2026/27.

**Live board:** https://odoema.github.io/trampu-board/

It shows how many classmates have joined, rides on offer, trips so far and how the launch email landed. A GitHub Action refreshes the numbers every hour and republishes the page.

## How it works

- `scripts/update.py` reads the public totals from `https://trampu.online/api/health` and, if the `RESEND_API_KEY` secret is set, the launch email delivery counts from Resend.
- It writes `data.json` (latest numbers) and `history.json` (the trend).
- `.github/workflows/update.yml` runs it hourly, commits the data and deploys `index.html` to GitHub Pages.

Only totals are published. No names, emails or phone numbers ever reach this repository.

## Live email numbers (optional)

Add your Resend API key as a repository secret named `RESEND_API_KEY` (Settings → Secrets and variables → Actions). Without it, the board keeps the 27 Oct launch snapshot.
