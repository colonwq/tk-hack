#!/usr/bin/env python3
"""Two-column hex-style display with address column and hover inversion."""

import random
import string
import tkinter as tk

# ASCII printable excluding letters and digits
SYMBOLS = [
    c for c in (string.punctuation + " ")
    if c.isprintable()
]
# Ensure we have a good set
if not SYMBOLS:
    SYMBOLS = list(" !\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~")

# 4-letter English words for random placement
FOUR_LETTER_WORDS = [
    "word", "good", "have", "that", "this", "with", "from", "they", "been", "were",
    "what", "when", "your", "said", "each", "make", "like", "time", "will", "know",
    "long", "down", "more", "some", "come", "over", "only", "into", "than", "them",
    "back", "after", "many", "same", "well", "here", "just", "where", "most", "such",
    "take", "work", "hand", "high", "find", "year", "part", "turn", "last", "head",
]

# Colors
BG = "#000000"
ADDRESS_COLOR = "#00CC00"   # medium neon green
CHAR_COLOR = "#00FF00"      # bright neon green
HOVER_BG = CHAR_COLOR       # inverted: green background
HOVER_FG = BG              # inverted: black text
HIGHLIGHT_BG = "#003300"    # dark green for matched range
HIGHLIGHT_FG = "#00FF00"    # bright green on highlight
STATUS_BOX_GREEN = "#00CC00"  # green for status squares
STATUS_BOX_RED = "#FF0000"   # red when wrong word clicked
STATUS_BOX_SIZE = 18         # square side in pixels (~text row height)
SECRET_REVEAL_RED = "#FF0000"  # red for secret word letters on Give up

# Lazy bracket pairs (opening -> closing)
OPEN_CLOSE = {"{": "}", "[": "]", "<": ">", "(": ")"}
CLOSE_OPEN = {v: k for k, v in OPEN_CLOSE.items()}

BASE_ADDRESS = 0xF00
CHARS_PER_ROW = 16
ROW_COUNT = 24
# Second column starts immediately after first column's last row
BASE_ADDRESS_COL1 = BASE_ADDRESS + ROW_COUNT * CHARS_PER_ROW
SPACER_PX = 32  # pixels between the two column sets
MESSAGE_COLUMN_LINES = 24  # max lines before scrolling off top


def find_lazy_match(col_chars, pos):
    """Return (start, end) inclusive for lazy bracket match within one column, or None."""
    c = col_chars[pos]
    if c in OPEN_CLOSE:
        # Opening bracket: find first matching closing to the right
        close = OPEN_CLOSE[c]
        for j in range(pos + 1, len(col_chars)):
            if col_chars[j] == close:
                return (pos, j)
        return None
    if c in CLOSE_OPEN:
        # Closing bracket: find first matching opening to the left (lazy = rightmost open)
        open_ch = CLOSE_OPEN[c]
        for j in range(pos - 1, -1, -1):
            if col_chars[j] == open_ch:
                return (j, pos)
        return None
    return None


def main():
    root = tk.Tk()
    root.title("Hex view")
    root.configure(bg=BG)

    rng = random.Random()
    column0 = []
    column1 = []
    word_placements = []
    secret_placement = None

    def do_generate_data():
        nonlocal column0, column1, word_placements, secret_placement
        column0 = [
            [rng.choice(SYMBOLS) for _ in range(CHARS_PER_ROW)]
            for _ in range(ROW_COUNT)
        ]
        column1 = [
            [rng.choice(SYMBOLS) for _ in range(CHARS_PER_ROW)]
            for _ in range(ROW_COUNT)
        ]
        word_placements.clear()
        words_to_place = rng.sample(FOUR_LETTER_WORDS, 8)
        for word in words_to_place:
            def valid_starts_for(col_idx, row):
                valid = set(range(0, CHARS_PER_ROW - 3))
                for (c, r, s) in word_placements:
                    if c != col_idx or r != row:
                        continue
                    invalid = set(range(max(0, s - 4), min(CHARS_PER_ROW - 3, s + 5)))
                    valid -= invalid
                return valid
            candidates = []
            for col_idx in (0, 1):
                for row in range(ROW_COUNT):
                    for start in valid_starts_for(col_idx, row):
                        candidates.append((col_idx, row, start))
            if not candidates:
                candidates = [
                    (col_idx, row, start)
                    for col_idx in (0, 1)
                    for row in range(ROW_COUNT)
                    for start in range(0, CHARS_PER_ROW - 3)
                ]
            col_idx, row, start = rng.choice(candidates)
            col = column0 if col_idx == 0 else column1
            for i, letter in enumerate(word):
                col[row][start + i] = letter
            word_placements.append((col_idx, row, start))
        secret_placement = rng.choice(word_placements)

    do_generate_data()

    removed_words = set()  # (col_idx, row, start) of words replaced with spaces, no longer clickable

    # Menu bar at top
    menubar = tk.Frame(root, bg=BG)
    menubar.pack(side=tk.TOP, fill=tk.X, padx=8, pady=(8, 0))
    game_container = tk.Frame(root, bg=BG)
    game_container.pack(padx=8, pady=8)

    def is_part_of_word(row, pos):
        col_idx = pos // CHARS_PER_ROW
        pos_in_col = pos % CHARS_PER_ROW
        for cidx, r, start in word_placements:
            if (cidx, r, start) in removed_words:
                continue
            if cidx == col_idx and r == row and start <= pos_in_col < start + 4:
                return True
        return False

    def get_clicked_word_placement(row, pos):
        """Return (col_idx, row, start) if (row, pos) is inside a word, else None."""
        col_idx = pos // CHARS_PER_ROW
        pos_in_col = pos % CHARS_PER_ROW
        for cidx, r, start in word_placements:
            if (cidx, r, start) in removed_words:
                continue
            if cidx == col_idx and r == row and start <= pos_in_col < start + 4:
                return (cidx, r, start)
        return None

    def get_word_at_placement(col_idx, row, start):
        """Return the 4-letter word at (col_idx, row, start) from the grid."""
        col = column0 if col_idx == 0 else column1
        return "".join(col[row][start + i] for i in range(4))

    def count_same_position_letters(word_a, word_b):
        """Return how many letters match in the same position (0..4 for 4-letter words)."""
        return sum(1 for i in range(min(len(word_a), len(word_b))) if word_a[i] == word_b[i])

    # labels_grid[row][pos] = label for that character (pos 0..15 col0, 16..31 col1)
    labels_grid = [[None] * (CHARS_PER_ROW * 2) for _ in range(ROW_COUNT)]
    click_highlighted = set()   # labels with persistent highlight (from click)
    hover_inverted = []         # labels currently showing hover inversion

    def restore_label(lbl):
        if lbl in click_highlighted:
            lbl.configure(fg=HIGHLIGHT_FG, bg=HIGHLIGHT_BG)
        else:
            lbl.configure(fg=CHAR_COLOR, bg=BG)

    def clear_hover_invert():
        nonlocal hover_inverted
        for lbl in hover_inverted:
            restore_label(lbl)
        hover_inverted = []

    def apply_highlight(row, start_glob, end_glob):
        for pos in range(start_glob, end_glob + 1):
            lbl = labels_grid[row][pos]
            click_highlighted.add(lbl)
            lbl.configure(fg=HIGHLIGHT_FG, bg=HIGHLIGHT_BG)

    def remove_one_non_secret_word():
        """Remove one non-secret word: replace letters with spaces and make it non-clickable.
        Never removes the secret word. Returns True if a word was removed, False otherwise.
        """
        nonlocal removed_words
        # Only consider non-secret words that have not already been removed
        candidates = [
            (cidx, r, s)
            for (cidx, r, s) in word_placements
            if (cidx, r, s) != secret_placement and (cidx, r, s) not in removed_words
        ]
        if not candidates:
            return False
        col_idx, r, start = rng.choice(candidates)
        removed_words.add((col_idx, r, start))
        col = column0 if col_idx == 0 else column1
        start_glob = col_idx * CHARS_PER_ROW + start
        for i in range(4):
            col[r][start + i] = " "
            lbl = labels_grid[r][start_glob + i]
            lbl.configure(text=" ")
            if lbl in click_highlighted:
                click_highlighted.discard(lbl)
            lbl.configure(fg=CHAR_COLOR, bg=BG)
        return True

    # Message column: append at top (new messages below); when full, scroll old off top
    message_text = None
    clicked_match_ranges = set()   # (row, start_glob, end_glob) for each match already clicked
    clicked_words = set()          # (col_idx, row, start) for each word already clicked
    secret_found = False          # when True, no more highlights or clicks
    wrong_word_count = 0          # 0..3, drives which status box turns red
    status_boxes = None           # list of 3 labels for status squares, set when status line built
    memory_value_label = None     # label for "Memory Value 0xXX"

    def append_message(msg):
        nonlocal message_text
        if message_text is None:
            return
        message_text.configure(state=tk.NORMAL)
        message_text.insert(tk.END, msg + "\n", "msg")
        message_text.see(tk.END)
        lines = int(message_text.index("end-1c").split(".")[0])
        if lines > MESSAGE_COLUMN_LINES:
            message_text.delete("1.0", "2.0")
        message_text.configure(state=tk.DISABLED)

    def on_cell_click(row, pos):
        nonlocal secret_found
        if secret_found:
            return
        col_idx = pos // CHARS_PER_ROW
        pos_in_col = pos % CHARS_PER_ROW
        col_chars = column0[row] if col_idx == 0 else column1[row]
        word_placement = get_clicked_word_placement(row, pos)
        if word_placement is not None:
            if word_placement == secret_placement:
                append_message("Secret found")
                secret_found = True
                return
            col_idx, r, start = word_placement
            start_glob = col_idx * CHARS_PER_ROW + start
            end_glob = start_glob + 3
            apply_highlight(row, start_glob, end_glob)
            if word_placement not in clicked_words:
                nonlocal wrong_word_count
                wrong_word_count += 1
                if wrong_word_count <= 3 and status_boxes is not None:
                    status_boxes[3 - wrong_word_count].configure(bg=STATUS_BOX_RED)
                clicked_word = get_word_at_placement(col_idx, r, start)
                secret_word = get_word_at_placement(
                    secret_placement[0], secret_placement[1], secret_placement[2]
                )
                n = count_same_position_letters(clicked_word, secret_word)
                append_message(f"Found word: {n}")
                clicked_words.add(word_placement)
        match = find_lazy_match(col_chars, pos_in_col)
        if match:
            start, end = match
            start_glob = col_idx * CHARS_PER_ROW + start
            end_glob = col_idx * CHARS_PER_ROW + end
            range_key = (row, start_glob, end_glob)
            if range_key not in clicked_match_ranges:
                append_message("Match found")
                clicked_match_ranges.add(range_key)
            apply_highlight(row, start_glob, end_glob)
            if not remove_one_non_secret_word():
                append_message("Error")

    def on_regen():
        nonlocal removed_words, clicked_match_ranges, clicked_words, secret_found, wrong_word_count
        do_generate_data()
        removed_words.clear()
        clicked_match_ranges.clear()
        clicked_words.clear()
        secret_found = False
        wrong_word_count = 0
        build_game()

    def on_give_up():
        nonlocal secret_found
        if secret_found:
            return
        secret_found = True
        append_message("Secret found")
        col_idx, r, start = secret_placement
        start_glob = col_idx * CHARS_PER_ROW + start
        for i in range(4):
            labels_grid[r][start_glob + i].configure(fg=SECRET_REVEAL_RED)

    def on_exit():
        root.destroy()

    def build_game():
        nonlocal labels_grid, message_text, status_boxes, memory_value_label, click_highlighted, hover_inverted
        for w in game_container.winfo_children():
            w.destroy()
        click_highlighted.clear()
        hover_inverted = []
        labels_grid = [[None] * (CHARS_PER_ROW * 2) for _ in range(ROW_COUNT)]

        # Container: [addr0][col0] spacer [addr1][col1] | message column
        main_frame = tk.Frame(game_container, bg=BG)
        main_frame.pack(padx=8, pady=8)

        content = tk.Frame(main_frame, bg=BG)
        content.pack(side=tk.LEFT)

        font_spec = ("Consolas", 14)
        addr_font = ("Consolas", 14)

        def make_enter(lbl, row, pos):
            def on_enter(_):
                if secret_found:
                    return
                nonlocal hover_inverted
                col_idx = pos // CHARS_PER_ROW
                pos_in_col = pos % CHARS_PER_ROW
                col_chars = column0[row] if col_idx == 0 else column1[row]
                ch = col_chars[pos_in_col]
                if ch in OPEN_CLOSE:
                    match = find_lazy_match(col_chars, pos_in_col)
                    if match:
                        start, end = match
                        start_glob = col_idx * CHARS_PER_ROW + start
                        end_glob = col_idx * CHARS_PER_ROW + end
                        range_labels = [labels_grid[row][p] for p in range(start_glob, end_glob + 1)]
                        if all(l in click_highlighted for l in range_labels):
                            return
                        clear_hover_invert()
                        hover_inverted = range_labels
                        for l in hover_inverted:
                            l.configure(fg=HOVER_FG, bg=HOVER_BG)
                        return
                if lbl not in click_highlighted:
                    lbl.configure(fg=HOVER_FG, bg=HOVER_BG)
            return on_enter

        def make_leave(lbl, row, pos):
            def on_leave(evt):
                if secret_found:
                    return
                nonlocal hover_inverted
                if hover_inverted:
                    w = root.winfo_containing(evt.x_root, evt.y_root)
                    if w in hover_inverted:
                        return
                    clear_hover_invert()
                    return
                if lbl in click_highlighted:
                    lbl.configure(fg=HIGHLIGHT_FG, bg=HIGHLIGHT_BG)
                    return
                lbl.configure(fg=CHAR_COLOR, bg=BG)
            return on_leave

        for row in range(ROW_COUNT):
            addr0 = BASE_ADDRESS + row * CHARS_PER_ROW
            addr1 = BASE_ADDRESS_COL1 + row * CHARS_PER_ROW

            addr0_lbl = tk.Label(
                content,
                text=f"0x{addr0:04X} ",
                font=addr_font,
                fg=ADDRESS_COLOR,
                bg=BG,
                width=7,
                anchor="w",
            )
            addr0_lbl.grid(row=row, column=0, sticky="w")

            frame0 = tk.Frame(content, bg=BG)
            frame0.grid(row=row, column=1, sticky="w")

            for idx, ch in enumerate(column0[row]):
                pos = idx
                lbl = tk.Label(
                    frame0,
                    text=ch,
                    font=font_spec,
                    fg=CHAR_COLOR,
                    bg=BG,
                    width=1,
                    cursor="hand2",
                )
                lbl.pack(side="left")
                lbl._hex_row, lbl._hex_pos = row, pos
                labels_grid[row][pos] = lbl
                lbl.bind("<Enter>", make_enter(lbl, row, pos))
                lbl.bind("<Leave>", make_leave(lbl, row, pos))
                lbl.bind("<Button-1>", lambda e, r=row, p=pos: on_cell_click(r, p))

            spacer = tk.Frame(content, bg=BG, width=SPACER_PX)
            spacer.grid(row=row, column=2, sticky="w")
            spacer.grid_propagate(False)

            addr1_lbl = tk.Label(
                content,
                text=f"0x{addr1:04X} ",
                font=addr_font,
                fg=ADDRESS_COLOR,
                bg=BG,
                width=7,
                anchor="w",
            )
            addr1_lbl.grid(row=row, column=3, sticky="w")

            frame1 = tk.Frame(content, bg=BG)
            frame1.grid(row=row, column=4, sticky="w")

            for idx, ch in enumerate(column1[row]):
                pos = CHARS_PER_ROW + idx
                lbl = tk.Label(
                    frame1,
                    text=ch,
                    font=font_spec,
                    fg=CHAR_COLOR,
                    bg=BG,
                    width=1,
                    cursor="hand2",
                )
                lbl.pack(side="left")
                lbl._hex_row, lbl._hex_pos = row, pos
                labels_grid[row][pos] = lbl
                lbl.bind("<Enter>", make_enter(lbl, row, pos))
                lbl.bind("<Leave>", make_leave(lbl, row, pos))
                lbl.bind("<Button-1>", lambda e, r=row, p=pos: on_cell_click(r, p))

        def on_motion(evt):
            w = root.winfo_containing(evt.x_root, evt.y_root)
            if memory_value_label is None:
                return
            if hasattr(w, "_hex_row") and hasattr(w, "_hex_pos"):
                r, p = w._hex_row, w._hex_pos
                col = column0 if p < CHARS_PER_ROW else column1
                pos_in_col = p % CHARS_PER_ROW
                ch = col[r][pos_in_col]
                memory_value_label.configure(text=f"Memory Value 0x{ord(ch):02X}")
            else:
                memory_value_label.configure(text="Memory Value 0x--")

        # Message column (third column)
        msg_frame = tk.Frame(main_frame, bg=BG)
        msg_frame.pack(side=tk.LEFT, padx=(SPACER_PX, 0))
        message_text = tk.Text(
            msg_frame,
            height=ROW_COUNT,
            width=20,
            font=("Consolas", 12),
            fg=CHAR_COLOR,
            bg=BG,
            insertbackground=CHAR_COLOR,
            state=tk.DISABLED,
            wrap=tk.WORD,
        )
        message_text.pack(side=tk.LEFT)
        message_text.tag_configure("msg", foreground=CHAR_COLOR)

        # Status line at bottom
        status_frame = tk.Frame(game_container, bg=BG)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=8, pady=(0, 8))
        status_boxes = []
        box_frame = tk.Frame(status_frame, bg=BG)
        box_frame.pack(side=tk.LEFT)
        for _ in range(3):
            f = tk.Frame(box_frame, bg=STATUS_BOX_GREEN, width=STATUS_BOX_SIZE, height=STATUS_BOX_SIZE)
            f.pack(side=tk.LEFT, padx=1)
            f.pack_propagate(False)
            status_boxes.append(f)
        memory_value_label = tk.Label(
            status_frame,
            text="Memory Value 0x--",
            font=("Consolas", 12),
            fg=CHAR_COLOR,
            bg=BG,
        )
        memory_value_label.pack(side=tk.RIGHT)
        root.bind("<Motion>", on_motion)

    # Menu buttons
    btn_font = ("Consolas", 12)
    tk.Button(menubar, text="Regen", command=on_regen, font=btn_font, fg=CHAR_COLOR, bg=BG, relief=tk.RAISED, bd=2).pack(side=tk.LEFT, padx=4)
    tk.Button(menubar, text="Exit", command=on_exit, font=btn_font, fg=CHAR_COLOR, bg=BG, relief=tk.RAISED, bd=2).pack(side=tk.LEFT, padx=4)
    tk.Button(menubar, text="Give up", command=on_give_up, font=btn_font, fg=CHAR_COLOR, bg=BG, relief=tk.RAISED, bd=2).pack(side=tk.LEFT, padx=4)

    build_game()
    root.mainloop()


if __name__ == "__main__":
    main()
