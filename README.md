# Trampu Launch Board

Public board for [Trampu](https://trampu.online), student-to-student ride sharing for Makerere MBA 2026/27.

**Live board:** https://odoema.github.io/trampu-board/

It shows how many classmates have joined, rides on offer, trips so far, email delivery/click engagement and board traffic. A GitHub Action refreshes the numbers every hour and republishes the page.

## How it works

- `scripts/update.py` reads the public totals from `https://trampu.online/api/health`.
- When `RESEND_API_KEY` is available, it reads aggregate email delivery/open/click events from Resend.
- The updater also reads aggregate GitHub repository traffic, which is shown as **Board visits** for the last 14 days.
- It writes `data.json` (latest numbers) and `history.json` (the trend).
- `.github/workflows/update.yml` runs hourly and on changes, commits the data and deploys `index.html` to GitHub Pages.

Only totals are published. No names, emails or phone numbers ever reach this repository.

## Live email numbers (optional)

Add your Resend API key as a repository secret named `RESEND_API_KEY` (Settings → Secrets and variables → Actions). Without it, the board keeps the last available email snapshot.

## About visits

**Board visits** are GitHub traffic views of this repository over the last 14 days. They are not the same as visits to `trampu.online`.

For true `trampu.online` visits, the next clean upgrade is GA4/Data API reporting for sessions, users and page views. The board should publish only aggregate figures from that source.
