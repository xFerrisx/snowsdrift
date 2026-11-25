# Project instructions

## Always push

After making changes, commit them **and push to `origin`** (`main`) without being
asked again. Do not leave work sitting locally as an unpushed commit.

- Remote: `https://github.com/xFerrisx/snowsdrift.git` (`origin`), branch `main`.
- Commit in the repository's existing style (short imperative subject, body
  explaining the why), then `git push`.
- Verify the push with `git ls-remote origin` or `git status -sb` showing no
  ahead/behind marker, and say in the reply that it was pushed.
- Only skip the push if the remote is unreachable or credentials fail; report
  that plainly instead of quietly leaving the commit local.

## What this is

Snowdrift: a Python/pygame endless 3D snowmobile drift game. Pure-pygame
software 3D rasteriser (no OpenGL/numpy), track generated from station index
and streamed in both directions, points = metres ridden. Tuning lives in
`snowdrift/config.py`; track shape in `TrackStream._curvature` / `_height`.
