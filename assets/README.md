# Assets

Place 2D art in sprites/, sounds in audio/, and fonts in fonts/.
Record source, author, license, and modifications here for every imported asset.
Only publish redistributable assets. One teammate owns asset importing.

## Fonts

- `fonts/PressStart2P-Regular.ttf`
  - Name: Press Start 2P
  - Authors: The Press Start 2P Project Authors; Cody "CodeMan38" Boisclair
  - Source: Google Fonts, `google/fonts/ofl/pressstart2p`
  - License: SIL Open Font License 1.1
  - Modification: none
  - License copy: `fonts/OFL-PressStart2P.txt`
  - Upstream changelog: `fonts/FONTLOG-PressStart2P.txt`

## Player characters

- `sprites/characters/doctor_female.png`
- `sprites/characters/doctor_male.png`
  - Source pack: 2D Top-Down Pixel Art Characters
  - Author: Jephed, Game Between The Lines
  - Source: https://gamebetweenthelines.itch.io/top-down-pixel-art-characters
  - License/usage: free for commercial and non-commercial use; credit appreciated
  - Source sheets retained in `sprites/characters/source/`
  - Modification: selected characters 010 and 003 were recolored into a white
    laboratory coat and blue shirt while preserving the original 12-frame walk
    cycles. `tools/build_doctor_sprites.py` reproduces the derived PNG files.
