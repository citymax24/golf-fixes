# Fast design rounds and merges

How a Claude session turns a visual idea from the owner into a live change quickly. The owner judges design from
moving pictures, decides fast and wants to see work early. Speed comes from short loops, not from skipping checks.

## The design loop
1. **Build, don't plan.** Make the change directly in the working tree and build it. For an open question of taste,
   build two or three variants side by side rather than one "best guess"; a variant is a few edited lines, not a branch.
2. **Show it within minutes, as video.** Record each variant with Playwright (desktop 1280 px and iPhone 14, light and
   dark), convert to mp4 and send it. Stills only for layout, never for motion, light or animation. Say in two or three
   plain sentences what changed and what is still weak.
3. **Ask once, then go on.** Put one clear decision to the owner (which variant, or yes/no) and keep working on what
   does not depend on it.
4. **Measure what can be measured.** For motion, a number beats an impression: e.g. the RMS change of speed per frame of
   an animated element while scrolling or moving the mouse. Report before and after.
5. **No multi-agent panels for taste.** Proposal/judge workflows with many agents are for research, audits and code review,
   not for colour, layout or motion questions. Use one at most when the owner asks for it.

## Rules of thumb for visual work on this site
- White, quiet, typographic; one accent green; gold only for awards; no decoration, no generic icons.
- Light and dark are designed separately (on white, light can only tint; on dark it can glow). Check both.
- Phones first: what the first screen shows decides. No hover on touch screens: drive effects by scroll or tap.
- Anything that moves must never bounce or pulse by accident: damp springs close to critical, no overshooting easing,
  and never move an element by script against content the browser scrolls on the compositor.
- Effects are rare and earned (the ambient light shows at the finder's answer and in "Or pick it by name" only).
- Text on any coloured background keeps 4.5:1 (small text) and 3:1 (large text); `build/site_check.js` checks it.

## From "Go" to live
1. Commit on a branch, merge the latest `main` in, push, open a PR.
2. **At the same time**, start the reviews and run `build/check.sh --live` (build, indexing gate and browser check,
   about 20 s). Do not run the reviews after the checks; they take longer.
3. Reviews, per CLAUDE.md:
   - **Small client-only change** (only `static/*.css` / `static/*.js`, no new host, script, embed or tracking, no data,
     workflow or `build.py` change): **one** review agent with both lenses, architecture and devops, under 10 minutes.
   - **Anything else**: two review agents, architecture and devops, in parallel.
   Fix blockers, push, re-run `build/check.sh`.
4. Save the current `main` as `rollback-<date><letter>` (read it with `git ls-remote` right before merging; bots push to
   `main`), merge the PR, wait for the new `app.js?v=` on the live site and re-check there:
   `node build/site_check.js --url https://golfvotes.com/`.
5. Report in a few lines: what is live, what was checked, the rollback branch.
