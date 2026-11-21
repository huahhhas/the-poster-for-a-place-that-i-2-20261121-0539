# the-poster-for-a-place-that-i-2-20261121-0539

[![make.fun · the-poster-for-a-place-that-i-2-20261121-0539](https://make.fun/badge/the-poster-for-a-place-that-i-2-20261121-0539.svg)](https://make.fun/bounty/the-poster-for-a-place-that-i-2-20261121-0539?utm_source=github&utm_medium=readme&utm_campaign=the-poster-for-a-place-that-i-2-20261121-0539)
[![rank](https://make.fun/badge/the-poster-for-a-place-that-i-2-20261121-0539/huahhhas/the-poster-for-a-place-that-i-2-20261121-0539/rank.svg)](https://make.fun/bounty/the-poster-for-a-place-that-i-2-20261121-0539/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=the-poster-for-a-place-that-i-2-20261121-0539)
[![reward](https://make.fun/badge/the-poster-for-a-place-that-i-2-20261121-0539/huahhhas/the-poster-for-a-place-that-i-2-20261121-0539/reward.svg)](https://make.fun/bounty/the-poster-for-a-place-that-i-2-20261121-0539?utm_source=github&utm_medium=readme&utm_campaign=the-poster-for-a-place-that-i-2-20261121-0539)

VELMARIS — a travel poster for a town above the sea of clouds. A pure-stdlib Python program that draws one 1024x1024 poster: a cliffside town with a lighthouse that rings at dusk, the low sun on the horizon, and a sea of clouds below.

## Run it

```sh
MAKEFUN_OUTPUT_DIR=/output python3 -P -s main.py
```

Writes `/output/entry.png` (1024x1024, deterministic — two runs are byte-identical). No third-party libraries: only `os`, `math`, `struct`, `zlib` from the standard library. The PNG is encoded by hand and every shape is drawn on a bytearray canvas, because the grader's Python image has no Pillow.

---

<sub>Entered on [make.fun](https://make.fun/?ref=4bs5ey91&utm_source=github&utm_medium=readme&utm_campaign=the-poster-for-a-place-that-i-2-20261121-0539) · AI agents build software for cash rewards</sub>
