# Publishing mexicoendatos.net without it pointing back at you

The site is plain files (`web/`), so it needs no server of its own. The plan
below uses GitHub for hosting and for the daily data refresh, and a registrar
that keeps your name out of the domain record. Nothing in this repository
carries a personal name or email; keep it that way.

What can still identify you, and what covers it:

| Trail | Covered by |
|---|---|
| Domain ownership record (WHOIS) | A registrar that lists itself as the registrant (Njalla does this; it also takes anonymous payment). Avoid `.mx`: its record shows the owner's name and city. |
| Hosting account | A GitHub account made only for this, with a new email address, created and always used through Tor Browser or a VPN. |
| Payment | GitHub Pages and Actions are free for a public repository. The domain is the only payment; pay it anonymously. |
| Code history | Commits are made as `mexicoendatos <mexico-en-datos@users.noreply.github.com>` (see below). Never commit from a git identity with your name. |
| Your computer's address in the sources' logs | The daily refresh runs on GitHub's machines, not yours. Run the tools at home only through a VPN, or not at all once the schedule works. |
| Visitors | The page sets no cookies, loads nothing from other sites, and sends no referrer. GitHub still sees visitors' addresses, as any host would. |

This hides you from the public and from casual investigation. The registrar
and GitHub will know what they know (an email, login addresses); a legal order
could reach them. If that is part of your threat, the Tor-only route is the
next step, and worth a separate conversation.

## Steps, in order

1. **Email.** Make a new address with a provider that needs no phone number
   (Proton Mail works over Tor). Use it for nothing else.
2. **GitHub account** under a pseudonym, with that email, through Tor Browser
   or a VPN. Turn on two-factor authentication (an authenticator app, not SMS).
3. **Git identity for this folder only**, before the first commit:
   ```bash
   cd <carpeta del proyecto>
   git init -b main
   git config user.name "mexico-en-datos"
   git config user.email "mexico-en-datos@users.noreply.github.com"
   git add -A && git commit -m "Primera versión"
   ```
   Check with `git log --format='%an <%ae>'` that no real name appears.
4. **Repository.** Create a public repository (Pages is free only for public
   ones) and push `main`. Then in *Settings → Pages* set *Source: GitHub Actions*.
   The workflow in `.github/workflows/pages.yml` publishes `web/` on every push.
5. **Daily data.** `.github/workflows/refresh.yml` runs every morning, re-reads
   the sources and commits the new `web/data/politicians.json` and
   `web/data/fuel.json` (gasoline prices). In *Settings →
   Actions → General*, allow workflows to write to the repository. Run it once
   by hand (*Actions → Actualizar datos → Run workflow*) and check it succeeds;
   if SIL or INEGI refuse GitHub's addresses, that run will say so.
6. **Domain.** Register `mexicoendatos.net` (free as of 2026-11-06). At the
   registrar, add DNS records pointing at GitHub Pages: a `CNAME` for `www` to
   `<account>.github.io`, and the four `A` records GitHub documents for the
   bare domain. In *Settings → Pages* add the custom domain and tick *Enforce HTTPS*.
7. **Before announcing it:** open the site from a browser you never use for
   personal accounts and read it as a stranger would. Nothing on the page, in
   the repository, or in the domain record should name you.

## Day to day

- Edit and push only through the pseudonymous account and a VPN or Tor.
- Do not link the site from personal profiles, and do not reply to press or
  readers from a personal address; use the project email.
- The map (`web/data/municipios.topojson`) changes only when INEGI publishes a
  new edition; rebuild it with `tools/build_map.py` and commit the result.
- Homicides (`web/data/crime.json`) change once a month, when the SESNSP
  publishes the next cut (around the 20th): copy the new share ids from its page
  into `FILES` in `informate/crime.py`, set `MONTHS`, run `tools/fetch_crime.py
  --refresh` and commit the result.
- Employment (`web/data/economy.json`) changes every quarter, when INEGI
  publishes the next ENOE bulletin (next: 2026-11-25): update `ENOE` in
  `informate/economy.py` to the new PDF and period, run `tools/fetch_economy.py
  --refresh` and commit. The minimum wage (January) and poverty (every two
  years, August) live in the same file and module.
- GDP (`web/data/gdp.json`) changes once a year, when INEGI publishes the next
  PIBE release in December: update `RELEASE` in `informate/gdp.py` to the new
  PDF, run `tools/fetch_gdp.py` and commit the result.
