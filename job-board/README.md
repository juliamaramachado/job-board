# Fieldnotes — Animal Behavior Jobs

A small website that collects job, postdoc, and graduate-position listings in
animal behavior, cognition, comparative cognition, and animal welfare from a
handful of legitimate public sources, and shows them in one feed.

It costs nothing to run: GitHub hosts the website (GitHub Pages) and runs the
daily update job (GitHub Actions) for free.

## How it works

- `scraper/scrape.py` fetches listings from USAJOBS (official API), the
  Animal Behavior Society's positions page, and the ISAE Applied Ethology
  jobs page, and writes them to `docs/data.json`.
- `docs/` is the actual website (`index.html`, `styles.css`, `app.js`) — it
  just reads `data.json` and displays it. No build step.
- `.github/workflows/update-jobs.yml` runs the scraper once a day automatically
  and commits the refreshed `data.json`, which updates the live site.

## One-time setup (about 15 minutes)

1. **Create a GitHub account** at github.com if you don't have one.

2. **Create a new repository** and upload these files.
   - Go to github.com → the "+" in the top right → "New repository".
   - Give it a name (e.g. `animal-behavior-jobs`), keep it Public, create it.
   - On the new repo's page, use "uploading an existing file" (or, if you're
     comfortable with git, `git init`, `git add .`, `git commit`, `git push`)
     to upload every file and folder from this project, keeping the same
     folder structure (`scraper/`, `docs/`, `.github/workflows/`).

3. **(Optional but recommended) Get a free USAJOBS API key**, so federal
   wildlife/animal-care jobs are included too:
   - Sign up at https://developer.usajobs.gov/
   - You'll get an email address (the one you signed up with) and an API key.
   - In your GitHub repo: Settings → Secrets and variables → Actions →
     "New repository secret". Add two secrets:
     - `USAJOBS_EMAIL` = the email you signed up with
     - `USAJOBS_API_KEY` = the key USAJOBS gave you
   - If you skip this, the site still works — it just won't include the
     USAJOBS source.

4. **Turn on GitHub Pages**:
   - In your repo: Settings → Pages.
   - Under "Build and deployment" → Source, choose "Deploy from a branch".
   - Branch: `main`, folder: `/docs`. Save.
   - GitHub will give you a URL like `https://yourusername.github.io/animal-behavior-jobs/`
     — that's your live site (it can take a minute or two to go live the
     first time).

5. **Run the scraper for the first time**:
   - In your repo: Actions tab → "Update job listings" workflow → "Run workflow" → Run workflow.
   - Wait ~30–60 seconds, then click into the run to see the log. It prints
     how many jobs each source found.
   - Refresh your live site — you should see listings.

After this, it updates itself daily — you don't need to do anything else.

## If a source shows "0 postings" or fails

Job-board websites occasionally redesign their pages, which can break the
part of the scraper that reads them. If you see this in the Action log:

1. Open the run's log and note which source failed and any error shown.
2. Come back and tell me — paste the log lines — and I can update
   `scraper/scrape.py` to match the site's new layout.

This is normal maintenance for any site that aggregates other websites, and
happens rarely (maybe a few times a year per source, if ever).

## Adding more sources later

Many employers (zoos, aquariums, universities, conservation nonprofits) post
jobs through applicant-tracking systems like Greenhouse or Lever, which often
expose a public JSON feed, e.g.:

- `https://boards-api.greenhouse.io/v1/boards/<company>/jobs`
- `https://api.lever.co/v0/postings/<company>`

To add one, write a new `fetch_*` function in `scraper/scrape.py` that
returns a list of job dicts in the same shape as the existing ones, and add
it to the `SOURCES` list at the bottom of the file. Happy to help write any
of these with you — just tell me which organization's board you want to add.

## Customizing

- Keyword list (used to filter USAJOBS results): `KEYWORDS` near the top of
  `scraper/scrape.py`.
- Colors/fonts: `docs/styles.css`.
- How often it updates: the `cron:` line in
  `.github/workflows/update-jobs.yml` (currently once a day).
