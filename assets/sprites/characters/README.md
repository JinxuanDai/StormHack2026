# Lab Panic doctor sprites

`doctor_female.png` and `doctor_male.png` are 64 × 128 transparent PNG sprite
sheets. Each sheet contains three 20 × 32 animation frames in each row:

1. down/front
2. left
3. right
4. up/back

The source sheets are characters `010.png` and `003.png` from **2D Top-Down
Pixel Art Characters** by Jephed / Game Between The Lines:

https://gamebetweenthelines.itch.io/top-down-pixel-art-characters

The author states that the pack is free for commercial and non-commercial use.
Credit is appreciated:

> Jephed, Game Between The Lines, https://gamebetweenthelines.com/

Lab Panic recolors the clothing into white laboratory coats with blue shirts.
No frames or poses were generated or removed. Run the reproducible build from
the repository root:

```sh
.venv/bin/python tools/build_doctor_sprites.py
```
