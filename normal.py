from Xlib import X, XK

from clipboard import copy
from constants import TARGET
from vim import open_vim
import text
import styles

# Set of pressed keys
pressed = set()


# This is a list of received events that haven't been handled yet.
# Only when the user releases a key, the script knows what it should do.
# Then it either discards the preceding events, or replays them
events = []

def event_to_string(self, event):
    mods = []
    if event.state & X.ShiftMask:
        mods.append('Shift')

    if event.state & X.ControlMask:
        mods.append('Control')

    keycode = event.detail
    keysym = self.disp.keycode_to_keysym(keycode, 0)
    char = XK.keysym_to_string(keysym)

    return ''.join(mod + '+' for mod in mods) + (char if char else '?')


def replay(self):
    for e in events:
        self.inkscape.send_event(e, propagate=True)

    self.disp.flush()
    self.disp.sync()

def normal_mode(self, event, char):
    events.append(event)

    if event.type == X.KeyPress and char:
        pressed.add(event_to_string(self, event))
        return 

    if event.type != X.KeyRelease:
        return 

    handled = False
    if len(pressed) > 1:
        paste_style(self, pressed)
        handled = True
    elif len(pressed) == 1:
        # Get the only element in pressed
        ev = next(iter(pressed))
        handled = handle_single_key(self, ev)
        
    # replay events to Inkscape if we couldn't handle them
    if not handled:
        replay(self)

    events.clear()
    pressed.clear()

def handle_single_key(self, ev):
    if ev == 't':
        # Vim mode
        open_vim(self, compile_latex=False)
    elif ev == 'Shift+t':
        # Vim mode prerendered
        open_vim(self, compile_latex=True)
    elif ev == 'a':
        # Add objects mode
        self.mode = styles.object_mode
    elif ev == 'Shift+a':
        # Save objects mode
        styles.save_object_mode(self)
    elif ev == 's':
        # Apply style mode
        self.mode = styles.style_mode
    elif ev == 'Shift+s':
        # Save style mode
        styles.save_style_mode(self)
    elif ev == 'w':
        # Pencil
        self.press('p')
    elif ev == 'x':
        # Snap
        self.press('percent', X.ShiftMask)
    elif ev == 'f':
        # Bezier
        self.press('b')
    elif ev == 'z':
        # Undo
        self.press('z', X.ControlMask)
    elif ev == 'Shift+z':
        # Delete
        self.press('Delete')
    elif ev == '`':
        # Disabled mode
        self.press('t')
        self.mode = text.text_mode
    else:
        # Not handled
        return False
    return True

def paste_style(self, combination):
    """

    This creates the style depending on the combination of keys.

    """

    # Stolen from TikZ
    pt = 1.327 # pixels
    w = 0.4 * pt
    thick_width = 0.75 * pt
    very_thick_width = 1.4 * pt

    style = {
        'stroke-opacity': 1
    }

    if {'s', 'a', 'd', 'g', 'h', 'x', 'e'} & combination:
        style['stroke'] = 'black'
        style['stroke-width'] = w
        style['marker-end'] = 'none'
        style['marker-start'] = 'none'
        style['stroke-dasharray'] = 'none'
    else:
        style['stroke'] = 'none'

    if 'g' in combination:
        w = thick_width
        style['stroke-width'] = w

    if 'h' in combination:
        w = very_thick_width
        style['stroke-width'] = w

    if 'a' in combination:
        style['marker-end'] = f'url(#marker-arrow-{w})'

    if 'x' in combination:
        style['marker-start'] = f'url(#marker-arrow-{w})'
        style['marker-end'] = f'url(#marker-arrow-{w})'

    if 'd' in combination:
        style['stroke-dasharray'] = f'{w},{2*pt}'

    if 'e' in combination:
        style['stroke-dasharray'] = f'{3*pt},{3*pt}'

    if 'f' in combination:
        style['fill'] = 'black'
        style['fill-opacity'] = 0.12

    if 'b' in combination:
        style['fill'] = 'black'
        style['fill-opacity'] = 1

    if 'w' in combination:
        style['fill'] = 'white'
        style['fill-opacity'] = 1

    if {'f', 'b', 'w'} & combination:
        style['marker-end'] = 'none'
        style['marker-start'] = 'none'

    if not {'f', 'b', 'w'} & combination:
        style['fill'] = 'none'
        style['fill-opacity'] = 1

    if style['fill'] == 'none' and style['stroke'] == 'none':
        return

    # Start creation of the svg.
    # Later on, we'll write this svg to the clipboard, and send Ctrl+Shift+V to
    # Inkscape, to paste this style.

    svg = '''
          <?xml version="1.0" encoding="UTF-8" standalone="no"?>
          <svg>
          '''
    # If a marker is applied, add its definition to the clipboard
    # Arrow styles stolen from tikz
    if ('marker-end' in style and style['marker-end'] != 'none') or \
            ('marker-start' in style and style['marker-start'] != 'none'):
        svg += f'''
                <defs id="marker-defs">
                    <marker
       style="overflow:visible"
       id="marker-arrow-{w}"
       refX="0"
       refY="0"
       orient="auto-start-reverse"
       inkscape:stockid="Arrow1Mend"
       inkscape:isstock="true">
      <path
         transform="matrix(-0.4,0,0,-0.4,-4,0)"
         style="fill:#000000;fill-opacity:1;fill-rule:evenodd;stroke:#000000;stroke-width:1pt;stroke-opacity:1"
         d="M 0,0 5,-5 -12.5,0 5,5 Z"
         id="path1025-6" />
    </marker>
</defs>
                '''

    style_string = ';'.join('{}: {}'.format(key, value)
                            for key, value in sorted(style.items(), key=lambda x: x[0])
                           )
    svg += f'<inkscape:clipboard style="{style_string}" /></svg>'

    copy(svg, target=TARGET)
    self.press('v', X.ControlMask | X.ShiftMask)
