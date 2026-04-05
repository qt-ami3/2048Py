0.8.23 -- Fixed audio skipping.

0.8.22 -- Fixed cracking and performence issues with track when low-pass filter kicks in.

0.8.21 -- Added music system!

    Not nearly as nice a patch number, but a huge leap in improving the game's atmosphere:
        Added first game theme track & accompanying cross-fading, low-pass, and tempo effect's.
    
    Fixed:
        Bug where, with nowhere else to go, a contrarian tile would prevent combination with like tile;
            After intense delibaeration, I came to the decision to make the combination of a sandwhiched contrarian combine into the opposing tile, meaning; you will unfortunately not be able to stick one in a corner to anchor your largest tile.

    Huge thanks to my pal, merionette for composing such a great piece.


0.7.20 -- Updated ability pricing and started version no.

    Bomb:
        Price lowered from 750 --> 500

    Freeze:
        Price increased from 500 --> 750

    Switch:
        Price increased from 600 --> 1550

    In main.py:
        {'name': 'Bomb', 'cost': 500, 'charges': 0, 'description': 'Destroy a tile'},
        {'name': 'Freeze', 'cost': 750, 'charges': 0, 'description': 'Hold tile 1 turn'},
        {'name': 'Switch', 'cost': 1550, 'charges': 0, 'description': 'Move any tile'},
