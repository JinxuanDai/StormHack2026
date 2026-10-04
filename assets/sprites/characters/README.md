# Lab Panic doctor sprites

`doctor_female.png` and `doctor_male.png` are 120 × 256 transparent PNG sprite
sheets. Each sheet contains three 40 × 64 animation frames in each row:

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

The approved designs in `design/` replace the original characters' appearance:
both have brown hair, blue shirts and white laboratory coats, while their male
and female silhouettes remain distinct. The source pack supplies the directional
layout/pose reference. Run the reproducible conversion from the repository root:

```sh
.venv/bin/python tools/build_doctor_sprites.py
```

The converter detects the four opaque row bands separated by transparent
gutters; the design rows are not evenly spaced vertically. Every output cell
contains exactly one pose, aligned at its feet. Male source poses at row 2,
column 3 and row 3, column 1 (one-based) are mirrored during conversion to
correct their facing. Original design images remain unchanged. Runtime frames
are cached at 2× size; collision rectangles are independent of sprite size.
