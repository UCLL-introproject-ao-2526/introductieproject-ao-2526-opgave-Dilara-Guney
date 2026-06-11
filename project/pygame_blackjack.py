import math
import random
import pygame

pygame.init()
try:
    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
    SOUND_ON = True
except Exception:
    SOUND_ON = False

# ── Window ────────────────────────────────────────────────────────────────────
WIDTH, HEIGHT = 680, 720
screen = pygame.display.set_mode([WIDTH, HEIGHT])
pygame.display.set_caption("Pygame Blackjack!")
fps = 60
clock = pygame.time.Clock()

# ── Fonts ─────────────────────────────────────────────────────────────────────
font        = pygame.font.Font("freesansbold.ttf", 44)
mid_font    = pygame.font.Font("freesansbold.ttf", 36)
small_font  = pygame.font.Font("freesansbold.ttf", 24)
tiny_font   = pygame.font.Font("freesansbold.ttf", 18)
card_font   = pygame.font.Font("freesansbold.ttf", 22)

# ── Colours ───────────────────────────────────────────────────────────────────
FELT        = (34, 100, 34)
DARK_FELT   = (15,  60, 15)
GOLD        = (212, 175, 55)
CREAM       = (255, 250, 220)
SHADOW_COL  = (10,  10, 10)
RED_CARD    = (180,  20, 20)
BLUE_BACK   = (25,  25,120)
YELLOW      = (255, 215,  0)
DARK_BOX    = (30,  30, 30)
LIGHT_GREEN = (120, 220, 120)

# ── Card constants ────────────────────────────────────────────────────────────
CARD_W, CARD_H = 68, 96
SUITS  = ["♠", "♥", "♦", "♣"]
RANKS  = ["2","3","4","5","6","7","8","9","10","J","Q","K","A"]
RED_SUITS = {"♥", "♦"}

# ── Sound helpers ─────────────────────────────────────────────────────────────
def _make_beep(freq, dur_ms, vol=0.35):
    """Generate a simple sine-wave beep without numpy."""
    if not SOUND_ON:
        return None
    try:
        import array as _arr
        rate = 44100
        n    = int(rate * dur_ms / 1000)
        buf  = _arr.array("h")
        for i in range(n):
            t    = i / rate
            fade = 1.0 - i / n
            v    = int(math.sin(2 * math.pi * freq * t) * fade * 32767 * vol)
            buf.append(max(-32768, min(32767, v)))
            buf.append(max(-32768, min(32767, v)))   # stereo
        return pygame.sndarray.make_sound(
            pygame.surfarray.make_surface([[0]])      # placeholder — overwrite below
        )
    except Exception:
        return None

# Build sounds via pygame.mixer directly
def _beep(freq, dur_ms, vol=0.35):
    if not SOUND_ON:
        return None
    try:
        import array as _arr
        rate = 44100
        n    = int(rate * dur_ms / 1000)
        buf  = _arr.array("h")
        for i in range(n):
            t    = i / rate
            fade = max(0.0, 1.0 - i / n)
            v    = int(math.sin(2 * math.pi * freq * t) * fade * 32767 * vol)
            buf.append(max(-32768, min(32767, v)))
            buf.append(max(-32768, min(32767, v)))
        sound = pygame.mixer.Sound(buffer=buf)
        return sound
    except Exception:
        return None

SND_CARD  = _beep(700,  70, 0.25)
SND_WIN   = _beep(523, 220, 0.35)
SND_BJ    = _beep(660, 350, 0.40)
SND_LOSE  = _beep(180, 300, 0.35)
SND_CHIP  = _beep(1100, 55, 0.20)
SND_BUST  = _beep(150, 400, 0.35)

def play(snd):
    if snd:
        try: snd.play()
        except Exception: pass

# ── Deck ──────────────────────────────────────────────────────────────────────
def make_shoe(num_decks=4):
    deck = [(r, s) for s in SUITS for r in RANKS] * num_decks
    random.shuffle(deck)
    return deck

# ── Card drawing ──────────────────────────────────────────────────────────────
def draw_card(surf, x, y, rank, suit, face_down=False):
    # Shadow
    pygame.draw.rect(surf, SHADOW_COL, [x+5, y+5, CARD_W, CARD_H], 0, 8)
    if face_down:
        pygame.draw.rect(surf, BLUE_BACK, [x, y, CARD_W, CARD_H], 0, 8)
        for row in range(3):
            for col in range(3):
                pygame.draw.rect(surf, (45, 45, 150),
                                 [x+8+col*25, y+8+row*35, 19, 28], 0, 4)
        pygame.draw.rect(surf, GOLD, [x, y, CARD_W, CARD_H], 3, 8)
        return

    color = RED_CARD if suit in RED_SUITS else (10, 10, 10)
    pygame.draw.rect(surf, CREAM,  [x, y, CARD_W, CARD_H], 0, 8)
    pygame.draw.rect(surf, (180, 180, 180), [x, y, CARD_W, CARD_H], 2, 8)

    # Top-left rank + suit
    r_surf = card_font.render(rank, True, color)
    s_surf = card_font.render(suit, True, color)
    surf.blit(r_surf, (x + 5, y + 4))
    surf.blit(s_surf, (x + 5, y + 4 + r_surf.get_height()))

    # Bottom-right (flipped)
    r_flip = pygame.transform.rotate(card_font.render(rank, True, color), 180)
    s_flip = pygame.transform.rotate(card_font.render(suit, True, color), 180)
    surf.blit(r_flip, (x + CARD_W - r_flip.get_width() - 5,
                       y + CARD_H - r_flip.get_height() - s_flip.get_height() - 4))
    surf.blit(s_flip, (x + CARD_W - s_flip.get_width() - 5,
                       y + CARD_H - s_flip.get_height() - 4))

    # Centre suit
    big = pygame.font.Font("freesansbold.ttf", 32).render(suit, True, color)
    surf.blit(big, (x + CARD_W//2 - big.get_width()//2,
                    y + CARD_H//2 - big.get_height()//2))

# ── Score calculation ─────────────────────────────────────────────────────────
def calc_score(hand):
    score, aces = 0, 0
    for rank, _ in hand:
        if rank in ("J", "Q", "K"):
            score += 10
        elif rank == "A":
            score += 11; aces += 1
        else:
            score += int(rank)
    while score > 21 and aces:
        score -= 10; aces -= 1
    return score

def is_blackjack(hand):
    return len(hand) == 2 and calc_score(hand) == 21

# ── Button helper ─────────────────────────────────────────────────────────────
def btn(surf, rect, text, fnt, mouse, fg=(0,0,0), bg=(255,255,255),
        border=None, hover_bg=(220, 255, 220)):
    bdr = border or (0, 160, 0)
    hov = pygame.Rect(rect).collidepoint(mouse)
    col = hover_bg if hov else bg
    pygame.draw.rect(surf, col,  rect, 0, 8)
    pygame.draw.rect(surf, bdr,  rect, 3, 8)
    t = fnt.render(text, True, fg)
    surf.blit(t, (rect[0] + rect[2]//2 - t.get_width()//2,
                  rect[1] + rect[3]//2 - t.get_height()//2))
    return pygame.Rect(rect)

def label(surf, text, fnt, color, cx, y):
    t = fnt.render(text, True, color)
    surf.blit(t, (cx - t.get_width()//2, y))

# ── Animation system ──────────────────────────────────────────────────────────
class AnimCard:
    SPEED = 20
    def __init__(self, rank, suit, tx, ty, face_down=False):
        self.rank, self.suit = rank, suit
        self.x, self.y = float(WIDTH + 60), float(-60)
        self.tx, self.ty = float(tx), float(ty)
        self.face_down = face_down
        self.done = False

    def update(self):
        dx, dy = self.tx - self.x, self.ty - self.y
        d = math.hypot(dx, dy)
        if d < self.SPEED:
            self.x, self.y = self.tx, self.ty
            self.done = True
        else:
            self.x += dx / d * self.SPEED
            self.y += dy / d * self.SPEED

    def draw(self, surf):
        draw_card(surf, int(self.x), int(self.y), self.rank, self.suit, self.face_down)

anims: list[AnimCard] = []

def all_done():
    return all(a.done for a in anims)

def queue_card(rank, suit, tx, ty, face_down=False):
    anims.append(AnimCard(rank, suit, tx, ty, face_down))
    play(SND_CARD)

# ── Layout helpers ────────────────────────────────────────────────────────────
def card_x(idx, total, cx=WIDTH//2):
    spacing = min(105, max(CARD_W + 4, (700) // max(total, 1)))
    total_w = spacing * (total - 1) + CARD_W
    return cx - total_w//2 + idx * spacing

DEALER_Y = 110
PLAYER_Y = 390

# ── Game state ────────────────────────────────────────────────────────────────
STATE_START  = 0
STATE_CHIPS  = 1
STATE_PLAY   = 2
STATE_OVER   = 3
STATE_STATS  = 4

state        = STATE_START
chips        = 1000
bet          = 50
base_bet     = 50
records      = [0, 0, 0]   # wins, losses, ties
biggest_win  = 0
total_hands  = 0

shoe: list = make_shoe(4)

my_hand:     list = []
dealer_hand: list = []
split_hand:  list = []
split_on         = False
active_hand      = 0          # 0 = main, 1 = split

outcome      = 0   # 0=none 1=bust 2=win 3=dealer 4=tie 5=blackjack
split_out    = 0
reveal       = False
hand_live    = False
in_play      = False
settled      = False

dealer_timer = 0

RESULT_TEXT  = ["", "BUSTED!", "YOU WIN! :)", "DEALER WINS :(", "TIE", "BLACKJACK! :D"]
RESULT_COLOR = [GOLD, RED_CARD, LIGHT_GREEN, RED_CARD, (200,200,200), GOLD]

# ── Deal from shoe ────────────────────────────────────────────────────────────
def pop_card():
    global shoe
    if len(shoe) < 20:
        shoe = make_shoe(4)
    return shoe.pop()

# ── Start a new hand ──────────────────────────────────────────────────────────
def new_hand():
    global my_hand, dealer_hand, split_hand, split_on, active_hand
    global outcome, split_out, reveal, hand_live, in_play, settled
    global anims, dealer_timer, chips

    my_hand = []; dealer_hand = []; split_hand = []
    split_on = False; active_hand = 0
    outcome = 0; split_out = 0
    reveal = False; hand_live = True; in_play = True; settled = False
    anims = []; dealer_timer = 0
    chips -= bet

    # 2 to player, 2 to dealer (dealer[0] is face-down)
    c = pop_card(); my_hand.append(c)
    queue_card(c[0], c[1], card_x(0, 2, WIDTH//2), PLAYER_Y)

    c = pop_card(); dealer_hand.append(c)
    queue_card(c[0], c[1], card_x(0, 2, WIDTH//2), DEALER_Y, face_down=True)

    c = pop_card(); my_hand.append(c)
    queue_card(c[0], c[1], card_x(1, 2, WIDTH//2), PLAYER_Y)

    c = pop_card(); dealer_hand.append(c)
    queue_card(c[0], c[1], card_x(1, 2, WIDTH//2), DEALER_Y)

# ── Draw table background ─────────────────────────────────────────────────────
def draw_table():
    screen.fill(DARK_FELT)
    pygame.draw.ellipse(screen, FELT, [40, 40, WIDTH-80, HEIGHT-80])
    pygame.draw.ellipse(screen, GOLD, [40, 40, WIDTH-80, HEIGHT-80], 4)
    label(screen, "DEALER", tiny_font, GOLD, WIDTH//2, 78)
    label(screen, "PLAYER", tiny_font, GOLD, WIDTH//2, 362)

# ── Draw all hands (static) ───────────────────────────────────────────────────
def draw_hands():
    # Dealer
    n = len(dealer_hand)
    for i, (r, s) in enumerate(dealer_hand):
        draw_card(screen, card_x(i, n, WIDTH//2), DEALER_Y,
                  r, s, face_down=(i == 0 and not reveal))

    if split_on:
        # Two player hands side by side
        cx1, cx2 = WIDTH//3, 2*WIDTH//3
        for i, (r, s) in enumerate(my_hand):
            draw_card(screen, card_x(i, len(my_hand), cx1), PLAYER_Y, r, s)
        for i, (r, s) in enumerate(split_hand):
            draw_card(screen, card_x(i, len(split_hand), cx2), PLAYER_Y, r, s)
        # Active hand highlight
        hl_cx = cx1 if active_hand == 0 else cx2
        hl_hand = my_hand if active_hand == 0 else split_hand
        n_hl = len(hl_hand)
        total_w = min(105, 700 // max(n_hl, 1)) * (n_hl-1) + CARD_W
        hx = hl_cx - total_w//2 - 6
        pygame.draw.rect(screen, GOLD, [hx, PLAYER_Y-6, total_w+12, CARD_H+12], 3, 10)
        label(screen, "HAND 1", tiny_font, GOLD if active_hand==0 else (180,180,180), cx1, PLAYER_Y-28)
        label(screen, "HAND 2", tiny_font, GOLD if active_hand==1 else (180,180,180), cx2, PLAYER_Y-28)
    else:
        n = len(my_hand)
        for i, (r, s) in enumerate(my_hand):
            draw_card(screen, card_x(i, n, WIDTH//2), PLAYER_Y, r, s)

# ── Settle the hand and pay out ───────────────────────────────────────────────
def settle():
    global outcome, split_out, records, settled, chips
    global biggest_win, total_hands, in_play

    ds = calc_score(dealer_hand)
    ps = calc_score(my_hand)

    # Main hand outcome
    if ps > 21:
        outcome = 1          # bust
    elif is_blackjack(my_hand) and not is_blackjack(dealer_hand):
        outcome = 5          # blackjack
    elif ds > 21 or ps > ds:
        outcome = 2          # win
    elif ps < ds:
        outcome = 3          # dealer wins
    else:
        outcome = 4          # tie

    # Split hand outcome
    if split_on:
        sp = calc_score(split_hand)
        if sp > 21:
            split_out = 1
        elif ds > 21 or sp > ds:
            split_out = 2
        elif sp < ds:
            split_out = 3
        else:
            split_out = 4

    # Payout
    winnings = 0
    if outcome == 5:   winnings += int(bet * 2.5)   # 1.5x profit → return 2.5x
    elif outcome == 2: winnings += bet * 2
    elif outcome == 4: winnings += bet               # push

    if split_on:
        if split_out == 2:   winnings += bet * 2
        elif split_out == 4: winnings += bet

    chips += winnings

    # Stats
    total_hands += 1
    profit = winnings - bet * (2 if split_on else 1)
    if outcome in (2, 5):
        records[0] += 1
        if profit > biggest_win:
            biggest_win = profit
        play(SND_BJ if outcome == 5 else SND_WIN)
    elif outcome in (1, 3):
        records[1] += 1
        play(SND_BUST if outcome == 1 else SND_LOSE)
    else:
        records[2] += 1

    settled = True
    in_play = False

# ─────────────────────────────────────────────────────────────────────────────
# Main loop
# ─────────────────────────────────────────────────────────────────────────────
running = True
while running:
    clock.tick(fps)
    mouse = pygame.mouse.get_pos()

    # ── Draw frame ────────────────────────────────────────────────────────────
    if state == STATE_START:
        screen.fill(DARK_FELT)
        pygame.draw.rect(screen, FELT, [100, 100, WIDTH-200, HEIGHT-200], 0, 20)
        pygame.draw.rect(screen, GOLD, [100, 100, WIDTH-200, HEIGHT-200], 4, 20)
        label(screen, "♠  BLACKJACK  ♣", font,      GOLD,  WIDTH//2, 210)
        label(screen, "Classic Casino",  small_font, (200,200,200), WIDTH//2, 278)
        play_btn  = btn(screen, [WIDTH//2-150, 380, 300, 80], "PLAY",  font, mouse)
        stats_btn = btn(screen, [WIDTH//2-100, 490, 200, 60], "STATS", mid_font, mouse,
                        bg=(40,40,40), hover_bg=(60,60,60), border=GOLD, fg=GOLD)

    elif state == STATE_CHIPS:
        screen.fill(DARK_FELT)
        pygame.draw.rect(screen, FELT, [100, 80, WIDTH-200, HEIGHT-160], 0, 20)
        pygame.draw.rect(screen, GOLD, [100, 80, WIDTH-200, HEIGHT-160], 4, 20)
        label(screen, "SELECT STARTING CHIPS", mid_font, GOLD, WIDTH//2, 150)
        c500  = btn(screen, [WIDTH//2-150, 260, 300, 85], "500 chips",  mid_font, mouse)
        c1000 = btn(screen, [WIDTH//2-150, 380, 300, 85], "1000 chips", mid_font, mouse)
        c2000 = btn(screen, [WIDTH//2-150, 500, 300, 85], "2000 chips", mid_font, mouse)

    elif state == STATE_OVER:
        screen.fill(DARK_FELT)
        ov = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 170)); screen.blit(ov, (0, 0))
        label(screen, "GAME  OVER",         font,       RED_CARD, WIDTH//2, 190)
        label(screen, "You ran out of chips!", mid_font, (220,220,220), WIDTH//2, 280)
        label(screen, f"W:{records[0]}  L:{records[1]}  T:{records[2]}  |  Best win: +{biggest_win}",
              small_font, GOLD, WIDTH//2, 355)
        again_btn = btn(screen, [WIDTH//2-150, 430, 300, 80], "PLAY AGAIN", mid_font, mouse)

    elif state == STATE_STATS:
        screen.fill(DARK_FELT)
        pygame.draw.rect(screen, FELT, [60, 50, WIDTH-120, HEIGHT-60], 0, 20)
        pygame.draw.rect(screen, GOLD, [60, 50, WIDTH-120, HEIGHT-60], 4, 20)
        label(screen, "STATISTICS", font, GOLD, WIDTH//2, 72)
        wr = int(records[0] / max(total_hands, 1) * 100)
        lines = [
            f"Total hands: {total_hands}",
            f"Wins:        {records[0]}",
            f"Losses:      {records[1]}",
            f"Ties:        {records[2]}",
            f"Win rate:    {wr}%",
            f"Biggest win: +{biggest_win} chips",
            f"Current chips: {chips}",
        ]
        for i, ln in enumerate(lines):
            label(screen, ln, small_font, (230,230,230), WIDTH//2, 140 + i*52)
        back_btn = btn(screen, [WIDTH//2-90, 140 + 7*52 + 10, 180, 55], "BACK", mid_font, mouse)

    elif state == STATE_PLAY:
        draw_table()

        # ── Chip / bet panel ──────────────────────────────────────────────────
        pygame.draw.rect(screen, DARK_BOX, [8, 8, 230, 80], 0, 8)
        pygame.draw.rect(screen, GOLD,     [8, 8, 230, 80], 2, 8)
        screen.blit(mid_font.render(f"Chips: {chips}", True, YELLOW),  (18, 14))
        screen.blit(mid_font.render(f"Bet:   {bet}",   True, YELLOW),  (18, 46))

        # Stats shortcut
        stats_btn2 = btn(screen, [WIDTH-155, 10, 140, 50], "STATS", small_font, mouse,
                         bg=DARK_BOX, hover_bg=(60,60,60), border=GOLD, fg=GOLD)

        if not in_play:
            # Bet ±10 buttons + deal
            minus_btn = btn(screen, [WIDTH//2-160, HEIGHT-120, 70, 44], "-10", mid_font, mouse)
            bet_lbl   = mid_font.render(f"BET: {bet}", True, (230,230,230))
            screen.blit(bet_lbl, (WIDTH//2 - bet_lbl.get_width()//2, HEIGHT-118))
            plus_btn  = btn(screen, [WIDTH//2+90,  HEIGHT-120, 70, 44], "+10", mid_font, mouse)
            deal_btn  = btn(screen, [WIDTH//2-140, HEIGHT-68, 280, 60], "DEAL HAND", mid_font, mouse)

            # W/L/T summary
            label(screen, f"W:{records[0]}  L:{records[1]}  T:{records[2]}",
                  small_font, GOLD, WIDTH//2, HEIGHT-140)

            # Result banner
            if outcome != 0:
                res_txt = font.render(RESULT_TEXT[outcome], True, RESULT_COLOR[outcome])
                bx = WIDTH//2 - res_txt.get_width()//2 - 18
                pygame.draw.rect(screen, DARK_BOX, [bx, 305, res_txt.get_width()+36, 52], 0, 10)
                screen.blit(res_txt, (WIDTH//2 - res_txt.get_width()//2, 310))
                if split_on and split_out != 0:
                    s_txt = mid_font.render(f"Split: {RESULT_TEXT[split_out]}",
                                            True, RESULT_COLOR[split_out])
                    screen.blit(s_txt, (WIDTH//2 - s_txt.get_width()//2, 362))

            # Scores after hand
            if outcome != 0:
                ps_txt = small_font.render(f"Player: {calc_score(my_hand)}", True, (200,200,200))
                ds_txt = small_font.render(f"Dealer: {calc_score(dealer_hand)}", True, (200,200,200))
                screen.blit(ps_txt, (WIDTH//2 - ps_txt.get_width()//2, 274))
                screen.blit(ds_txt, (WIDTH//2 - ds_txt.get_width()//2, 86))

        else:
            # HIT / STAND
            hit_btn   = btn(screen, [30,        HEIGHT-68, 200, 60], "HIT",   mid_font, mouse)
            stand_btn = btn(screen, [WIDTH-230,  HEIGHT-68, 200, 60], "STAND", mid_font, mouse)

            # Double (only first two cards, enough chips, no split)
            dbl_btn = None
            if hand_live and len(my_hand) == 2 and chips >= bet and not split_on:
                dbl_btn = btn(screen, [WIDTH//2-60, HEIGHT-68, 120, 60], "DBL", mid_font, mouse)

            # Split (pair on first two cards)
            spl_btn = None
            if (hand_live and len(my_hand) == 2
                    and my_hand[0][0] == my_hand[1][0]
                    and chips >= bet and not split_on):
                spl_btn = btn(screen, [WIDTH//2-55, HEIGHT-138, 110, 50], "SPLIT",
                              small_font, mouse, border=GOLD, hover_bg=(60,60,30))

            # Live score
            live_score = calc_score(my_hand if active_hand == 0 else split_hand)
            label(screen, f"Score: {live_score}", mid_font, (230,230,230), WIDTH//2, 360)
            if reveal:
                label(screen, f"Dealer: {calc_score(dealer_hand)}", mid_font, (230,230,230), WIDTH//2, 82)

        # Draw hands + anims
        if in_play or outcome != 0:
            draw_hands()
        for a in anims:
            a.update(); a.draw(screen)

        # Dealer auto-draw (after player stands)
        if in_play and not hand_live and reveal and all_done():
            ds = calc_score(dealer_hand)
            if ds < 17:
                dealer_timer += 1
                if dealer_timer >= 35:
                    dealer_timer = 0
                    c = pop_card(); dealer_hand.append(c)
                    n = len(dealer_hand)
                    queue_card(c[0], c[1], card_x(n-1, n, WIDTH//2), DEALER_Y)
            else:
                if not settled:
                    settle()

        # Auto-check: chips below minimum
        if chips < base_bet and not in_play:
            state = STATE_OVER

    # ── Events ────────────────────────────────────────────────────────────────
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.MOUSEBUTTONUP:

            # ── Start screen ──────────────────────────────────────────────────
            if state == STATE_START:
                if play_btn.collidepoint(event.pos):
                    state = STATE_CHIPS
                elif stats_btn.collidepoint(event.pos):
                    state = STATE_STATS

            # ── Chip select ───────────────────────────────────────────────────
            elif state == STATE_CHIPS:
                for btn_rect, amount in [(c500, 500), (c1000, 1000), (c2000, 2000)]:
                    if btn_rect.collidepoint(event.pos):
                        chips = amount; bet = 50; base_bet = 50
                        records = [0,0,0]; total_hands = 0; biggest_win = 0
                        in_play = False; outcome = 0
                        state = STATE_PLAY
                        break

            # ── Game over ─────────────────────────────────────────────────────
            elif state == STATE_OVER:
                if again_btn.collidepoint(event.pos):
                    state = STATE_CHIPS

            # ── Stats ─────────────────────────────────────────────────────────
            elif state == STATE_STATS:
                if back_btn.collidepoint(event.pos):
                    state = STATE_START if total_hands == 0 else STATE_PLAY

            # ── Playing ───────────────────────────────────────────────────────
            elif state == STATE_PLAY:
                if stats_btn2.collidepoint(event.pos):
                    state = STATE_STATS

                elif not in_play:
                    if deal_btn.collidepoint(event.pos) and chips >= bet:
                        new_hand(); play(SND_CHIP)
                    elif minus_btn.collidepoint(event.pos) and bet > 10:
                        bet -= 10; play(SND_CHIP)
                    elif plus_btn.collidepoint(event.pos) and bet + 10 <= chips:
                        bet += 10; play(SND_CHIP)

                elif in_play and all_done():
                    cur_hand = my_hand if active_hand == 0 else split_hand
                    cx = (WIDTH//3 if active_hand==0 else 2*WIDTH//3) if split_on else WIDTH//2

                    # HIT
                    if hit_btn.collidepoint(event.pos) and hand_live:
                        c = pop_card(); cur_hand.append(c)
                        queue_card(c[0], c[1], card_x(len(cur_hand)-1, len(cur_hand), cx), PLAYER_Y)
                        if calc_score(cur_hand) >= 21:
                            if split_on and active_hand == 0:
                                active_hand = 1
                            else:
                                hand_live = False; reveal = True

                    # STAND
                    elif stand_btn.collidepoint(event.pos) and hand_live:
                        if split_on and active_hand == 0:
                            active_hand = 1
                        else:
                            hand_live = False; reveal = True

                    # DOUBLE DOWN
                    elif dbl_btn and dbl_btn.collidepoint(event.pos) and hand_live:
                        chips -= bet; bet *= 2
                        c = pop_card(); my_hand.append(c)
                        queue_card(c[0], c[1], card_x(len(my_hand)-1, len(my_hand), WIDTH//2), PLAYER_Y)
                        hand_live = False; reveal = True; play(SND_CHIP)

                    # SPLIT
                    elif spl_btn and spl_btn.collidepoint(event.pos) and hand_live:
                        chips -= bet                       # extra bet for second hand
                        split_hand = [my_hand.pop()]       # move second card to split hand
                        split_on = True; active_hand = 0
                        # Deal one card to each hand
                        c1 = pop_card(); my_hand.append(c1)
                        queue_card(c1[0], c1[1], card_x(1, 2, WIDTH//3), PLAYER_Y)
                        c2 = pop_card(); split_hand.append(c2)
                        queue_card(c2[0], c2[1], card_x(1, 2, 2*WIDTH//3), PLAYER_Y)
                        play(SND_CHIP)

    # ── Auto-bust check ───────────────────────────────────────────────────────
    if state == STATE_PLAY and in_play and hand_live and all_done():
        cur = my_hand if active_hand == 0 else split_hand
        if calc_score(cur) > 21:
            if split_on and active_hand == 0:
                active_hand = 1
            else:
                hand_live = False; reveal = True

    pygame.display.flip()