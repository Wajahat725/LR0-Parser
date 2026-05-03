"""
LR(0) Parser — Complete Python Implementation
DFA drawn on tkinter Canvas with rectangular states and proper labeled arrows.
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import re, math
from collections import defaultdict

# ─────────────────────────────────────────────────────────────────────────────
#  TOKENIZER
# ─────────────────────────────────────────────────────────────────────────────

def _tokenize_rhs(s):
    """Tokenize RHS properly handling multi-character tokens and quoted symbols"""
    tokens = []
    s = s.strip()
    i, n = 0, len(s)
    
    while i < n:
        c = s[i]
        if c in (' ', '\t'):
            i += 1
            continue
            
        # Handle quoted tokens (like 'id' or 'number')
        if c == "'":
            j = i + 1
            while j < n and s[j] != "'":
                j += 1
            if j < n:
                tokens.append(s[i+1:j])
                i = j + 1
                continue
        
        # Handle epsilon
        if s.startswith('ε', i) or s.startswith('epsilon', i) or s.startswith('eps', i):
            tokens.append('ε')
            i += len('ε') if s.startswith('ε', i) else (7 if s.startswith('epsilon', i) else 3)
            continue
        
        # Check for empty parentheses pattern: "()" as a special case
        if c == '(' and i + 1 < n and s[i+1] == ')':
            tokens.append('(')
            tokens.append('ε')
            tokens.append(')')
            i += 2
            continue
        
        # Handle non-terminals (uppercase starting, possibly with quotes)
        if re.match(r'[A-Z]', c):
            j = i + 1
            while j < n and (s[j] == "'" or s[j].isalnum()):
                j += 1
            tokens.append(s[i:j])
            i = j
        # Handle terminals (lowercase, digits, symbols)
        elif re.match(r'[a-z0-9_]', c):
            j = i
            while j < n and re.match(r'[a-z0-9_]', s[j]):
                j += 1
            tok = s[i:j]
            if tok not in ('eps', 'epsilon'):
                tokens.append(tok)
            i = j
        else:
            tokens.append(c)
            i += 1
    
    return tokens


# ─────────────────────────────────────────────────────────────────────────────
#  CORE ENGINE
# ─────────────────────────────────────────────────────────────────────────────

class Production:
    def __init__(self, lhs, rhs): 
        self.lhs = lhs
        self.rhs = tuple(rhs) if rhs else ('ε',)
    
    def __repr__(self): 
        return f"{self.lhs} -> {' '.join(self.rhs) if self.rhs else 'ε'}"

class Item:
    __slots__ = ('prod_idx','dot','lhs','rhs')
    def __init__(self, pi, dot, lhs, rhs):
        self.prod_idx=pi
        self.dot=dot
        self.lhs=lhs
        self.rhs=rhs
    
    @property
    def next_sym(self): 
        return self.rhs[self.dot] if self.dot < len(self.rhs) else None
    
    @property
    def is_complete(self): 
        return self.dot >= len(self.rhs)
    
    def advanced(self): 
        return Item(self.prod_idx, self.dot+1, self.lhs, self.rhs)
    
    def __eq__(self, o): 
        return self.prod_idx == o.prod_idx and self.dot == o.dot
    
    def __hash__(self): 
        return hash((self.prod_idx, self.dot))
    
    def __repr__(self):
        r = list(self.rhs)
        if not r or (len(r) == 1 and r[0] == 'ε'):
            r = []
        r.insert(self.dot, '•')
        return f"{self.lhs} → {' '.join(r) if r else '•'}"

class LR0Parser:
    def __init__(self, grammar_text):
        self.grammar_text = grammar_text
        self.productions=[]
        self.non_terminals=[]
        self.terminals=[]
        self.start_symbol=None
        self.aug_start=None
        self.states=[]
        self.transitions=[]
        self.action_table={}
        self.goto_table={}
        self.conflicts=[]
        self._parse_grammar()
        self._build_dfa()
        self._build_tables()

    def _parse_grammar(self):
        lines = [l.strip() for l in self.grammar_text.strip().splitlines()
                 if l.strip() and not l.strip().startswith('//')]
        if not lines: 
            raise ValueError("Grammar is empty.")
        
        raw = []
        non_terminals = set()
        start_symbol = None
        
        for line in lines:
            m = re.match(r'^(.+?)\s*(?:->|→)\s*(.+)$', line)
            if not m: 
                raise ValueError(f"Cannot parse: '{line}'")
            
            lhs = m.group(1).strip()
            if start_symbol is None:
                start_symbol = lhs
            
            non_terminals.add(lhs)
            rhs_part = m.group(2).strip()
            
            # Split alternatives
            alternatives = []
            current = []
            paren_count = 0
            j = 0
            while j < len(rhs_part):
                if rhs_part[j] == '(':
                    paren_count += 1
                    current.append(rhs_part[j])
                elif rhs_part[j] == ')':
                    paren_count -= 1
                    current.append(rhs_part[j])
                elif rhs_part[j] == '|' and paren_count == 0:
                    alternatives.append(''.join(current).strip())
                    current = []
                else:
                    current.append(rhs_part[j])
                j += 1
            if current:
                alternatives.append(''.join(current).strip())
            
            for alt in alternatives:
                if alt:
                    tokens = _tokenize_rhs(alt)
                    if tokens and len(tokens) == 3 and tokens[0] == '(' and tokens[1] == 'ε' and tokens[2] == ')':
                        tokens = ['(', ')']
                    raw.append((lhs, tokens))
                else:
                    raw.append((lhs, ['ε']))
        
        # Add augmented start symbol
        self.start_symbol = start_symbol
        self.aug_start = start_symbol + "'"
        while self.aug_start in non_terminals:
            self.aug_start += "'"
        
        # Build productions list
        self.productions = []
        self.productions.append(Production(self.aug_start, [self.start_symbol]))
        for lhs, rhs in raw:
            self.productions.append(Production(lhs, rhs))
        
        # Identify all symbols
        all_symbols = set()
        for p in self.productions:
            all_symbols.add(p.lhs)
            all_symbols.update(p.rhs)
        
        # Classify terminals and non-terminals
        nt_set = set()
        nt_set.add(self.aug_start)
        nt_set.add(self.start_symbol)
        for p in self.productions[1:]:
            nt_set.add(p.lhs)
        
        self.non_terminals = list(nt_set)
        self.terminals = sorted([s for s in all_symbols if s not in nt_set and s != 'ε'])
        if '$' not in self.terminals:
            self.terminals.append('$')
        if 'ε' in self.terminals:
            self.terminals.remove('ε')
        if '(' not in self.terminals:
            self.terminals.append('(')
        if ')' not in self.terminals:
            self.terminals.append(')')
        
        self.terminals = sorted(set(self.terminals))

    def _item(self, pi, dot):
        p = self.productions[pi]
        return Item(pi, dot, p.lhs, p.rhs)

    def _closure(self, items):
        s = set(items)
        changed = True
        
        while changed:
            changed = False
            items_list = list(s)
            
            for item in items_list:
                next_sym = item.next_sym
                if next_sym and next_sym in self.non_terminals:
                    for i, prod in enumerate(self.productions):
                        if prod.lhs == next_sym:
                            new_item = self._item(i, 0)
                            if new_item not in s:
                                s.add(new_item)
                                changed = True
        
        return frozenset(s)

    def _goto(self, state, sym):
        new_items = set()
        for item in state:
            if item.next_sym == sym:
                new_items.add(item.advanced())
        return self._closure(new_items) if new_items else frozenset()

    def _build_dfa(self):
        initial_items = self._closure({self._item(0, 0)})
        self.states = [initial_items]
        self.transitions = [{}]
        state_map = {initial_items: 0}
        queue = [0]
        
        while queue:
            state_idx = queue.pop(0)
            current_state = self.states[state_idx]
            
            next_symbols = set()
            for item in current_state:
                sym = item.next_sym
                if sym:
                    next_symbols.add(sym)
            
            for sym in next_symbols:
                goto_state = self._goto(current_state, sym)
                
                if not goto_state:
                    continue
                
                if goto_state not in state_map:
                    new_idx = len(self.states)
                    state_map[goto_state] = new_idx
                    self.states.append(goto_state)
                    self.transitions.append({})
                    queue.append(new_idx)
                else:
                    new_idx = state_map[goto_state]
                
                self.transitions[state_idx][sym] = new_idx

    def _set_action(self, state, symbol, action):
        key = (state, symbol)
        existing = self.action_table.get(key)
        
        if existing and existing != action:
            conflict_msg = f"State {state}, symbol '{symbol}': {existing} vs {action}"
            if conflict_msg not in self.conflicts:
                self.conflicts.append(conflict_msg)
        else:
            self.action_table[key] = action

    def _build_tables(self):
        for state, trans in enumerate(self.transitions):
            for symbol, target in trans.items():
                if symbol in self.non_terminals:
                    self.goto_table[(state, symbol)] = target
                else:
                    self._set_action(state, symbol, f"s{target}")
        
        for state, items in enumerate(self.states):
            for item in items:
                if item.is_complete:
                    if item.lhs == self.aug_start:
                        self._set_action(state, '$', 'acc')
                    else:
                        for terminal in self.terminals:
                            self._set_action(state, terminal, f"r{item.prod_idx}")


# ─────────────────────────────────────────────────────────────────────────────
#  GUI CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

EXAMPLES = {
    "Arithmetic": "E' -> E\nE -> E + T\nE -> T\nT -> T * F\nT -> F\nF -> ( E )\nF -> i",
    "Nested Parens": "S -> A\nA -> ( A B )\nA -> ( )\nB -> ( A )\nB -> ( )",
    "Balanced Parens": "S' -> S\nS -> ( S )\nS -> ε",
    "Simple (aAb)": "S' -> S\nS -> a A b\nA -> c\nA -> d",
}

MONO = ("Courier", 10)
LABEL = ("TkDefaultFont", 9)
HEAD = ("TkDefaultFont", 10, "bold")

# DFA colours
COL_HDR_BG   = '#1a3a6b'
COL_HDR_FG   = '#ffffff'
COL_BOX_BG   = '#dce8ff'
COL_BOX_BD   = '#1a3a6b'
COL_ACCEPT   = '#cc0000'
COL_DOT_FG   = '#002299'
COL_DONE_FG  = '#883300'
COL_ARROW    = '#222222'
COL_LBL_BG   = '#fffbe6'
COL_LBL_BD   = '#bbaa00'
COL_LBL_FG   = '#cc0000'


# ─────────────────────────────────────────────────────────────────────────────
#  DFA CANVAS RENDERER
# ─────────────────────────────────────────────────────────────────────────────

class DFACanvas(tk.Canvas):
    """Canvas that draws LR(0) states with clear, separate arrows for each transition."""

    BW     = 195
    HDR    = 22
    IH     = 17
    IPAD   = 6
    TXPAD  = 8

    def __init__(self, master, **kw):
        super().__init__(master, bg='#f4f6fa', **kw)
        self._scale   = 1.0
        self._parser  = None
        self._pos     = {}
        self.bind('<ButtonPress-1>',  self._drag_start)
        self.bind('<B1-Motion>',       self._drag_move)
        self.bind('<MouseWheel>',      lambda e: self._zoom(1.12 if e.delta>0 else 1/1.12))
        self.bind('<Button-4>',        lambda e: self._zoom(1.12))
        self.bind('<Button-5>',        lambda e: self._zoom(1/1.12))

    def draw(self, parser):
        self._parser = parser
        self._scale  = 1.0
        self._compute_layout()
        self.redraw()
        self.xview_moveto(0)
        self.yview_moveto(0)

    def zoom(self, factor):
        self._scale = max(0.25, min(3.0, self._scale * factor))
        self.redraw()

    def fit(self):
        self._scale = 1.0
        self.redraw()
        self.xview_moveto(0)
        self.yview_moveto(0)

    def _box_h(self, si):
        n = len(self._parser.states[si])
        return int((self.HDR + self.IPAD + n * self.IH + self.IPAD) * self._scale)

    def _box_w(self):
        return int(self.BW * self._scale)

    def _compute_layout(self):
        p = self._parser
        n = len(p.states)

        # BFS to assign column
        col = {0: 0}
        q = [0]
        while q:
            si = q.pop(0)
            for tgt in p.transitions[si].values():
                if tgt not in col:
                    col[tgt] = col[si] + 1
                    q.append(tgt)
        
        for i in range(n):
            if i not in col:
                col[i] = max(col.values()) + 1

        cols = defaultdict(list)
        for i in range(n):
            cols[col[i]].append(i)

        # Increased spacing
        COL_GAP = 350  # More horizontal space
        ROW_GAP = 80   # More vertical space

        def lh(si):
            return self.HDR + self.IPAD + len(p.states[si]) * self.IH + self.IPAD

        self._lpos = {}
        lx = self.BW // 2 + 50
        for ci in sorted(cols):
            nodes = cols[ci]
            ly = 50  # Start with more top margin
            for si in nodes:
                h = lh(si)
                self._lpos[si] = (lx, ly + h // 2)
                ly += h + ROW_GAP
            lx += COL_GAP

    def redraw(self):
        self.delete('all')
        p = self._parser
        sc = self._scale
        if not p:
            return

        pos = {si: (int(lx*sc), int(ly*sc)) for si, (lx,ly) in self._lpos.items()}
        accept_states = {s for s in range(len(p.states)) if p.action_table.get((s,'$')) == 'acc'}

        # Draw arrows first (behind boxes)
        transitions_by_pair = defaultdict(list)
        for si, trans in enumerate(p.transitions):
            for sym, tgt in trans.items():
                transitions_by_pair[(si, tgt)].append(sym)

        # Draw arrows with better routing
        for (si, ti), syms in transitions_by_pair.items():
            label = ', '.join(sorted(syms))
            self._draw_clear_arrow(pos, si, ti, label, p, sc)

        # Draw state boxes
        for si in range(len(p.states)):
            cx, cy = pos[si]
            bw = self._box_w()
            bh = self._box_h(si)
            x0, y0 = cx - bw//2, cy - bh//2
            x1, y1 = x0 + bw, y0 + bh

            hdr_h   = int(self.HDR * sc)
            item_h  = int(self.IH * sc)
            ipad    = int(self.IPAD * sc)
            txpad   = int(self.TXPAD * sc)

            is_acc = si in accept_states
            bd_col = COL_ACCEPT if is_acc else COL_BOX_BD
            bd_w   = max(2, int(2*sc)) if is_acc else max(1, int(1.5*sc))

            self.create_rectangle(x0, y0, x1, y1, fill=COL_BOX_BG, outline=bd_col, width=bd_w)
            self.create_rectangle(x0, y0, x1, y0+hdr_h, fill=COL_HDR_BG, outline=bd_col, width=bd_w)
            
            fsz = max(7, int(10*sc))
            self.create_text(cx, y0+hdr_h//2, text=f"I{si}",
                              font=('Courier', fsz, 'bold'),
                              fill=COL_HDR_FG, anchor='center')

            self.create_line(x0+bd_w, y0+hdr_h, x1-bd_w, y0+hdr_h,
                              fill=bd_col, width=max(1,int(sc)))

            fsz2 = max(6, int(9*sc))
            iy = y0 + hdr_h + ipad
            items = sorted(p.states[si], key=lambda it:(it.prod_idx, it.dot))
            for it in items:
                r = list(it.rhs)
                if r and r[0] == 'ε':
                    r = []
                r.insert(it.dot, '•')
                txt = f"{it.lhs} → {' '.join(r) if r else '•'}"
                col = COL_DONE_FG if it.is_complete else COL_DOT_FG
                self.create_text(x0+txpad, iy + item_h//2,
                                  text=txt, font=('Courier', fsz2),
                                  fill=col, anchor='w')
                iy += item_h

        self.update_idletasks()
        bb = self.bbox('all')
        if bb:
            self.configure(scrollregion=(bb[0]-50, bb[1]-50, bb[2]+50, bb[3]+50))

    def _draw_clear_arrow(self, pos, si, ti, label, p, sc):
        """Draw arrows with clear routing avoiding other states"""
        bw = self._box_w()
        bh_s = self._box_h(si)
        bh_t = self._box_h(ti)
        cx_s, cy_s = pos[si]
        cx_t, cy_t = pos[ti]
        
        # Get all state positions to avoid
        all_positions = list(pos.values())
        
        # For self-loop
        if si == ti:
            # Draw self-loop above the state
            r = int(45 * sc)
            loop_x = cx_s
            loop_y = cy_s - bh_s//2 - r//2 - 10
            
            # Draw full circle arc
            self.create_arc(loop_x - r, loop_y - r, loop_x + r, loop_y + r,
                           start=20, extent=320, style='arc',
                           outline=COL_ARROW, width=max(2, int(2.5*sc)))
            
            # Arrow head
            angle = 340
            arrow_x = loop_x + r * math.cos(math.radians(angle))
            arrow_y = loop_y + r * math.sin(math.radians(angle))
            arrow_size = int(8 * sc)
            self.create_polygon(
                arrow_x, arrow_y,
                arrow_x - arrow_size, arrow_y - arrow_size//2,
                arrow_x - arrow_size, arrow_y + arrow_size//2,
                fill=COL_ARROW, outline=COL_ARROW
            )
            
            # Label inside loop
            self._draw_label(loop_x, loop_y - r//3, label, sc)
            return
        
        # For transitions between different states
        dx = cx_t - cx_s
        dy = cy_t - cy_s
        
        # Determine the best edge points based on direction
        # Add more offset to avoid crossing other states
        if abs(dx) > abs(dy):
            # Horizontal movement
            if dx > 0:
                # Going right
                x1 = cx_s + bw//2
                y1 = cy_s
                x2 = cx_t - bw//2
                y2 = cy_t
                # Curve upward or downward based on vertical alignment
                if abs(y2 - y1) < 50:
                    offset = 60 * sc
                    cx1 = x1 + 40 * sc
                    cy1 = y1 - offset if (si % 2 == 0) else y1 + offset
                    cx2 = x2 - 40 * sc
                    cy2 = y1 - offset if (si % 2 == 0) else y1 + offset
                else:
                    cx1 = x1 + 40 * sc
                    cy1 = y1 + (y2 - y1) * 0.3
                    cx2 = x2 - 40 * sc
                    cy2 = y1 + (y2 - y1) * 0.7
            else:
                # Going left
                x1 = cx_s - bw//2
                y1 = cy_s
                x2 = cx_t + bw//2
                y2 = cy_t
                if abs(y2 - y1) < 50:
                    offset = 60 * sc
                    cx1 = x1 - 40 * sc
                    cy1 = y1 - offset if (si % 2 == 0) else y1 + offset
                    cx2 = x2 + 40 * sc
                    cy2 = y1 - offset if (si % 2 == 0) else y1 + offset
                else:
                    cx1 = x1 - 40 * sc
                    cy1 = y1 + (y2 - y1) * 0.3
                    cx2 = x2 + 40 * sc
                    cy2 = y1 + (y2 - y1) * 0.7
        else:
            # Vertical movement
            if dy > 0:
                # Going down
                x1 = cx_s
                y1 = cy_s + bh_s//2
                x2 = cx_t
                y2 = cy_t - bh_t//2
                if abs(x2 - x1) < 50:
                    offset = 60 * sc
                    cx1 = x1 - offset if (si % 2 == 0) else x1 + offset
                    cy1 = y1 + 40 * sc
                    cx2 = x1 - offset if (si % 2 == 0) else x1 + offset
                    cy2 = y2 - 40 * sc
                else:
                    cx1 = x1 + (x2 - x1) * 0.3
                    cy1 = y1 + 40 * sc
                    cx2 = x1 + (x2 - x1) * 0.7
                    cy2 = y2 - 40 * sc
            else:
                # Going up
                x1 = cx_s
                y1 = cy_s - bh_s//2
                x2 = cx_t
                y2 = cy_t + bh_t//2
                if abs(x2 - x1) < 50:
                    offset = 60 * sc
                    cx1 = x1 - offset if (si % 2 == 0) else x1 + offset
                    cy1 = y1 - 40 * sc
                    cx2 = x1 - offset if (si % 2 == 0) else x1 + offset
                    cy2 = y2 + 40 * sc
                else:
                    cx1 = x1 + (x2 - x1) * 0.3
                    cy1 = y1 - 40 * sc
                    cx2 = x1 + (x2 - x1) * 0.7
                    cy2 = y2 + 40 * sc

        # Draw bezier curve
        pts = _cubic_bezier(x1, y1, cx1, cy1, cx2, cy2, x2, y2, 25)
        flat = [c for pt in pts for c in pt]
        asz = (int(8*sc), int(10*sc), int(3*sc))
        
        self.create_line(*flat, smooth=True, fill=COL_ARROW,
                          width=max(2, int(2*sc)),
                          arrow=tk.LAST, arrowshape=asz)

        # Place label at mid-curve with offset
        mx, my = _bezier_point(0.5, x1,y1,cx1,cy1,cx2,cy2,x2,y2)
        
        # Smart label placement
        if dx > 0:
            off_x, off_y = 25 * sc, -20 * sc
        elif dx < 0:
            off_x, off_y = -25 * sc, -20 * sc
        elif dy > 0:
            off_x, off_y = 20 * sc, -25 * sc
        else:
            off_x, off_y = 20 * sc, 25 * sc
            
        self._draw_label(mx + off_x, my + off_y, label, sc)

    def _draw_label(self, lx, ly, text, sc):
        fsz = max(7, int(10*sc))
        pw, ph = int(18*sc), int(9*sc)
        
        # Add white background with border
        self.create_rectangle(lx-pw, ly-ph, lx+pw, ly+ph,
                               fill=COL_LBL_BG, outline=COL_LBL_BD,
                               width=max(1,int(sc)))
        self.create_text(lx, ly, text=text, font=('TkDefaultFont', fsz, 'bold'),
                          fill=COL_LBL_FG, anchor='center')

    def _drag_start(self, e):
        self.scan_mark(e.x, e.y)
    
    def _drag_move(self, e):
        self.scan_dragto(e.x, e.y, gain=1)
    
    def _zoom(self, f):
        self.zoom(f)


# ─────────────────────────────────────────────────────────────────────────────
#  BEZIER HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _cubic_bezier(x0,y0,cx1,cy1,cx2,cy2,x1,y1,n=25):
    pts=[]
    for i in range(n+1):
        t=i/n
        u=1-t
        x=u**3*x0+3*u**2*t*cx1+3*u*t**2*cx2+t**3*x1
        y=u**3*y0+3*u**2*t*cy1+3*u*t**2*cy2+t**3*y1
        pts.append((x,y))
    return pts

def _bezier_point(t,x0,y0,cx1,cy1,cx2,cy2,x1,y1):
    u=1-t
    x=u**3*x0+3*u**2*t*cx1+3*u*t**2*cx2+t**3*x1
    y=u**3*y0+3*u**2*t*cy1+3*u*t**2*cy2+t**3*y1
    return x,y


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN APP
# ─────────────────────────────────────────────────────────────────────────────

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("LR(0) Parser - DFA and Parsing Table")
        self.geometry("1200x800")
        self.resizable(True, True)
        self.parser = None
        self._build_ui()

    def _build_ui(self):
        left = tk.Frame(self, width=300)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)
        left.pack_propagate(False)

        tk.Label(left, text="Grammar Input", font=HEAD).pack(anchor='w')
        tk.Label(left,
                 text="One production per line. Use | for alternatives.\n"
                      "Use ε / eps for empty. Arrow: -> or →",
                 font=LABEL, justify='left', wraplength=280).pack(anchor='w', pady=(2,4))

        self.grammar_box = scrolledtext.ScrolledText(left, height=14, font=MONO, wrap=tk.WORD)
        self.grammar_box.pack(fill=tk.X)
        self.grammar_box.insert('1.0', EXAMPLES["Arithmetic"])

        tk.Label(left, text="Examples:", font=LABEL).pack(anchor='w', pady=(8,2))
        for name in EXAMPLES:
            tk.Button(left, text=name, font=LABEL,
                      command=lambda n=name: self._load(n)).pack(fill=tk.X, pady=2)

        tk.Button(left, text="▶  BUILD PARSER  ◀", font=HEAD,
                  bg="#1a3a6b", fg="white", activebackground="#2a4a8b",
                  cursor="hand2", height=2, command=self._build).pack(fill=tk.X, pady=(10,5))

        self.status_lbl = tk.Label(left, text="", font=LABEL, fg="red",
                                   wraplength=280, justify='left')
        self.status_lbl.pack(anchor='w')

        right = tk.Frame(self)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0,10), pady=10)
        
        self.nb = ttk.Notebook(right)
        self.nb.pack(fill=tk.BOTH, expand=True)
        self._tab_dfa()
        self._tab_table()

    def _load(self, name):
        self.grammar_box.delete('1.0', tk.END)
        self.grammar_box.insert('1.0', EXAMPLES[name])

    def _tab_dfa(self):
        f = tk.Frame(self.nb)
        self.nb.add(f, text="  DFA - LR(0) Item Sets  ")

        bar = tk.Frame(f, bg='#eeeeee', pady=5)
        bar.pack(fill=tk.X, side=tk.BOTTOM)
        tk.Label(bar, text="🖱️ Drag to pan  |  🔍 Zoom:", bg='#eeeeee', font=LABEL).pack(side=tk.LEFT, padx=10)
        tk.Button(bar, text="  +  ", font=HEAD, command=lambda: self.dfa_cv.zoom(1.2)).pack(side=tk.LEFT, padx=2)
        tk.Button(bar, text="  −  ", font=HEAD, command=lambda: self.dfa_cv.zoom(1/1.2)).pack(side=tk.LEFT, padx=2)
        tk.Button(bar, text="⟳ Fit", font=LABEL, command=lambda: self.dfa_cv.fit()).pack(side=tk.LEFT, padx=10)

        wrap = tk.Frame(f)
        wrap.pack(fill=tk.BOTH, expand=True)
        hbar = tk.Scrollbar(wrap, orient=tk.HORIZONTAL)
        vbar = tk.Scrollbar(wrap, orient=tk.VERTICAL)
        self.dfa_cv = DFACanvas(wrap, xscrollcommand=hbar.set, yscrollcommand=vbar.set)
        hbar.config(command=self.dfa_cv.xview)
        vbar.config(command=self.dfa_cv.yview)
        hbar.pack(side=tk.BOTTOM, fill=tk.X)
        vbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.dfa_cv.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def _tab_table(self):
        self.table_frame = tk.Frame(self.nb)
        self.nb.add(self.table_frame, text="  LR(0) Parsing Table  ")
        self.conflict_lbl = tk.Label(self.table_frame, text="", fg='red',
                                     font=LABEL, wraplength=800, justify='left')
        self.conflict_lbl.pack(anchor='w', padx=5, pady=5)
        wrap = tk.Frame(self.table_frame)
        wrap.pack(fill=tk.BOTH, expand=True)
        self.tbl_canvas = tk.Canvas(wrap, borderwidth=0)
        hbar = tk.Scrollbar(wrap, orient=tk.HORIZONTAL, command=self.tbl_canvas.xview)
        vbar = tk.Scrollbar(wrap, orient=tk.VERTICAL, command=self.tbl_canvas.yview)
        self.tbl_canvas.configure(xscrollcommand=hbar.set, yscrollcommand=vbar.set)
        hbar.pack(side=tk.BOTTOM, fill=tk.X)
        vbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tbl_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.tbl_inner = tk.Frame(self.tbl_canvas)
        self.tbl_canvas.create_window((0,0), window=self.tbl_inner, anchor='nw')
        self.tbl_inner.bind('<Configure>',
            lambda e: self.tbl_canvas.configure(scrollregion=self.tbl_canvas.bbox('all')))

    def _build(self):
        txt = self.grammar_box.get('1.0', tk.END).strip()
        if not txt:
            self.status_lbl.config(text="❌ Enter a grammar first.", fg='red')
            return
        
        try:
            self.parser = LR0Parser(txt)
        except Exception as e:
            self.status_lbl.config(text=f"❌ Error: {e}", fg='red')
            self.parser = None
            return
        
        self.status_lbl.config(
            text=f"✅ Built: {len(self.parser.states)} states, {len(self.parser.productions)} productions.",
            fg='green')
        self.dfa_cv.draw(self.parser)
        self._render_table()

    def _render_table(self):
        p = self.parser
        for w in self.tbl_inner.winfo_children():
            w.destroy()
        
        if p.conflicts:
            self.conflict_lbl.config(fg='darkred', bg='#ffcccc',
                text="⚠ WARNING - CONFLICTS DETECTED ⚠\n" + "\n".join(p.conflicts))
        else:
            self.conflict_lbl.config(fg='darkgreen', bg='#ccffcc',
                text="✓ No conflicts — grammar is LR(0).")

        terms = p.terminals
        nts   = [nt for nt in p.non_terminals if nt != p.aug_start]

        def cell(row, col, text, bg='white', fg='black', bold=False, w=8):
            font = (MONO[0], MONO[1], 'bold') if bold else MONO
            lbl = tk.Label(self.tbl_inner, text=text, font=font,
                          bg=bg, fg=fg, relief='solid', borderwidth=1,
                          padx=5, pady=3, width=w)
            lbl.grid(row=row, column=col, sticky='nsew')

        cell(0, 0, "State", bg='#222', fg='white', bold=True, w=6)
        for j,s in enumerate(terms):
            cell(0, j+1, s, bg='#1a3a6b', fg='white', bold=True, w=10)
        for j,nt in enumerate(nts):
            cell(0, len(terms)+j+1, nt, bg='#3a3a3a', fg='white', bold=True, w=10)
        cell(1, 0, "", bg='#eee')
        for j in range(len(terms)):
            cell(1, j+1, "ACTION", bg='#dde8ff', fg='#1a3a6b', bold=True, w=10)
        for j in range(len(nts)):
            cell(1, len(terms)+j+1, "GOTO", bg='#eee', fg='#333', bold=True, w=10)
        
        for i in range(len(p.states)):
            rbg = '#f8f8f8' if i%2==0 else '#ffffff'
            cell(i+2, 0, str(i), bg='#e5e5e5', bold=True, w=6)
            for j,sym in enumerate(terms):
                v = p.action_table.get((i,sym),'')
                if v.startswith('s'):
                    bg2,fg2='#dce8ff','#003399'
                elif v.startswith('r'):
                    bg2,fg2='#fff5dc','#884400'
                elif v=='acc':
                    bg2,fg2='#d4f5d4','#004400'
                else:
                    bg2,fg2=rbg,'#aaaaaa'
                cell(i+2, j+1, v, bg=bg2, fg=fg2, w=10)
            for j,nt in enumerate(nts):
                v = str(p.goto_table.get((i,nt),''))
                cell(i+2, len(terms)+j+1, v, bg=rbg, fg='#333333', w=10)


if __name__ == "__main__":
    App().mainloop()