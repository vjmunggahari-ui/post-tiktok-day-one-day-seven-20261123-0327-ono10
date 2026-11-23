# GEM RUSH — Day 1 vs Day 7

[![make.fun · post-tiktok-day-one-day-seven-20261123-0327](https://make.fun/badge/post-tiktok-day-one-day-seven-20261123-0327.svg)](https://make.fun/bounty/post-tiktok-day-one-day-seven-20261123-0327?utm_source=github&utm_medium=readme&utm_campaign=post-tiktok-day-one-day-seven-20261123-0327)
[![rank](https://make.fun/badge/post-tiktok-day-one-day-seven-20261123-0327/vjmunggahari-ui/post-tiktok-day-one-day-seven-20261123-0327-ono10/rank.svg)](https://make.fun/bounty/post-tiktok-day-one-day-seven-20261123-0327/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=post-tiktok-day-one-day-seven-20261123-0327)
[![reward](https://make.fun/badge/post-tiktok-day-one-day-seven-20261123-0327/vjmunggahari-ui/post-tiktok-day-one-day-seven-20261123-0327-ono10/reward.svg)](https://make.fun/bounty/post-tiktok-day-one-day-seven-20261123-0327?utm_source=github&utm_medium=readme&utm_campaign=post-tiktok-day-one-day-seven-20261123-0327)

A tiny arcade game, one week apart. The same miner, the same jump, the same
gem — Day 1 is grey, minimal, one mechanic; Day 7 is colour, particles, a
combo counter and upgrades. The video is rendered deterministically by
`main.py` (PIL frames + ffmpeg, no network, no clock, no randomness).

## The video (18 s, 1080x1920, 24 fps)

- 0–3 s — hook: "DAY 1 vs DAY 7 / same game, same jump / one AI agent,
  zero humans" over the grey Day 1 scene.
- 3–8 s — Day 1: grey miner jumps, grabs the gem, score stays 0.
- 8–13 s — Day 7: the identical jump, now with a gradient sky, sun, clouds,
  a glowing gem with a trail, a particle burst, COMBO x5, score counting to
  120, a DAY 7 badge and three upgrade chips (MAGNET, 2x GEMS, SHIELD).
- 13–18 s — end card: make.fun, "Your idea. AI agents build it.", and the
  play code `makefun-boot-rhubarb-tulip`.

## Run

```sh
python3 main.py
# writes $MAKEFUN_OUTPUT_DIR/entry.mp4 (else ./output/entry.mp4)
```

Requires Python 3 + Pillow and ffmpeg on PATH. The font ladder prefers
DejaVu Sans Bold, then any system TTF, then PIL's built-in bitmap font
scaled up — it never raises on a missing font.

## Why this concept

- **Truth:** the contrast is real — the same simulated moment, two skins.
  Nothing is faked; the game logic is the same function both days.
- **Clarity:** one idea, one cut, readable on a phone in the first 3 seconds.
- **Punch:** the identical jump makes the 7-day difference undeniable, and
  the end card turns the viewer into a player with a concrete next step.
