import pygame
import sys
import copy
import random
import math
import time

# --- 초기 설정 ---
pygame.init()

BOARD_SIZE = 640
SIDE_WIDTH = 250 
WIDTH = BOARD_SIZE + SIDE_WIDTH * 2
HEIGHT = BOARD_SIZE
CELL = BOARD_SIZE // 8

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("AUGMENT CHESS - Professional V13.0")

# --- 폰트 로드 ---
def get_font(size, bold=False, is_piece=False):
    if is_piece:
        piece_fonts = ["segoeuisymbol", "quivira", "dejavusans", "freeserif", "arial"]
        for f in piece_fonts:
            try:
                found = pygame.font.SysFont(f, size)
                if found: return found
            except: continue
    text_fonts = ["malgungothic", "nanumgothic", "notosansckjkr", "arial"]
    for f in text_fonts:
        try:
            found = pygame.font.SysFont(f, size, bold=bold)
            if found: return found
        except: continue
    return pygame.font.SysFont(None, size)

font_piece = get_font(60, is_piece=True)
font_title = get_font(28, True)
font_menu = get_font(20, True)
font_small = get_font(14, True)
font_log = get_font(13)
font_timer = get_font(32, True)

PIECE_UNICODE = {
    "K": "♔", "Q": "♕", "R": "♖", "B": "♗", "N": "♘", "P": "♙",
    "k": "♚", "q": "♛", "r": "♜", "b": "♝", "n": "♞", "p": "♟"
}

# --- 게임 상태 ---
STATE_LOBBY = "LOBBY"
STATE_GAME = "GAME"
STATE_AUGMENT_SELECT = "AUGMENT_SELECT"
STATE_SETTINGS = "SETTINGS"

AUGMENT_SCHEDULE = [3, 6, 10, 15, 20, 25, 30, 40, 50]

AUGMENT_POOL = [
    {"id": "apfsds", "name": "열화우라늄날개안정분리철갑탄", "desc": "비숍 이동 시 주변 1칸 적/아군 삭제(킹 제외) 후 비숍 사망"},
    {"id": "descendant_of_khan", "name": "칸의 후예", "desc": "비숍이 나이트로 변경. 킹이 나이트의 행마법 획득"},
    {"id": "true_king", "name": "진정한 왕은 누구인가?", "desc": "퀸 삭제. 킹이 퀸의 행마법 획득"},
    {"id": "colossus", "name": "체크메이트의 거신병", "desc": "내 모든 폰 전멸 시 d열 1행에 퀸 소환"},
    {"id": "chess960", "name": "체스 960", "desc": "내 기물(폰/킹 제외)의 위치를 무작위로 뒤섞음"},
    {"id": "road_to_heaven", "name": "천국에 가는 길", "desc": "다음 증강 선택 시 확정으로 '중력 반전' 등장"},
    {"id": "undo_master", "name": "Undo!", "desc": "되돌리기 무제한 활성화"},
    {"id": "pawn_front_line", "name": "전방 전선", "desc": "모든 폰 1칸 전진(기물 삭제, 킹 제외)"},
    {"id": "knight_slayer", "name": "초살병기 나이트", "desc": "나이트에게 룩의 행마 추가"},
    {"id": "pawn_world_nerfed", "name": "쇼킹 폰 월드", "desc": "상대 무작위 기물 3개를 폰으로 변환"},
    {"id": "time_stop", "name": "시간 정지", "desc": "3턴간 나만 행동 (킹 전용 무적 이동 가능)"},
    {"id": "pawn_side", "name": "졸병 진화", "desc": "폰이 좌우로도 이동 가능"},
    {"id": "knight_bishop", "name": "결전병기 나이트", "desc": "나이트가 비숍처럼 대각선 이동 가능"},
    {"id": "bishop_sniper", "name": "저격 비숍", "desc": "비숍이 기물을 뛰어넘어 공격 가능"},
    {"id": "meteor_strike", "name": "메테오 스트라이크", "desc": "룩이 기물을 관통하여 뒤까지 공격"},
    {"id": "kings_attack", "name": "킹스 어택", "desc": "킹이 대각선 2칸 위치로 도약 가능"},
    {"id": "necromancy", "name": "네크로맨시", "desc": "킹 이동 불가, 대신 주변 빈 공간에 폰 소환 가능"},
    {"id": "gravity_flip", "name": "중력 반전", "desc": "내 폰들의 전진 방향이 반대로 변경됨"},
    {"id": "royal_guard", "name": "로열 가드", "desc": "킹 주변 8칸의 아군 기물은 잡히지 않음"}
]

class ChessLogic:
    def __init__(self):
        self.reset()

    def reset(self):
        self.board = [
            list("rnbqkbnr"), list("pppppppp"), list("........"), list("........"),
            list("........"), list("........"), list("PPPPPPPP"), list("RNBQKBNR"),
        ]
        self.turn = "w"
        self.full_turns = 1
        self.history = []
        self.move_log = []
        self.augments = {"w": [], "b": []}
        self.time_stop_left = {"w": 0, "b": 0}
        self.gravity_flip = False
        self.heaven_trigger = {"w": False, "b": False}
        self.game_over = False
        self.winner = None
        # 타이머
        self.turn_start_time = time.time()
        self.total_time = {"w": 0.0, "b": 0.0}
        # 캐슬링 및 앙파상 상태
        self.moved = {"K": False, "k": False, "R1": False, "R8": False, "r1": False, "r8": False}
        self.en_passant_target = None # (r, c)

    def update_timers(self):
        if self.game_over: return
        now = time.time()
        delta = now - self.turn_start_time
        self.total_time[self.turn] += delta
        self.turn_start_time = now

    def save_state(self):
        state = {
            "board": [row[:] for row in self.board],
            "turn": self.turn,
            "full_turns": self.full_turns,
            "augments": copy.deepcopy(self.augments),
            "time_stop_left": self.time_stop_left.copy(),
            "gravity_flip": self.gravity_flip,
            "heaven_trigger": self.heaven_trigger.copy(),
            "move_log": list(self.move_log),
            "game_over": self.game_over,
            "winner": self.winner,
            "total_time": self.total_time.copy(),
            "moved": self.moved.copy(),
            "en_passant_target": self.en_passant_target
        }
        self.history.append(state)

    def undo(self):
        if not self.history: return False
        last = self.history.pop()
        for k, v in last.items(): setattr(self, k, v)
        self.turn_start_time = time.time()
        return True

    def get_moves_raw(self, r, c, attack=False):
        p = self.board[r][c]
        if p == ".": return []
        is_w = p.isupper()
        color = "w" if is_w else "b"
        moves = []

        if p.lower() == "p":
            d = -1 if is_w else 1
            if self.gravity_flip: d = -d
            # 직진
            if not attack and 0 <= r+d < 8 and self.board[r+d][c] == ".":
                moves.append((r+d, c))
                sr = 6 if is_w else 1
                if self.gravity_flip: sr = 1 if is_w else 6
                if r == sr and 0 <= r+2*d < 8 and self.board[r+2*d][c] == "." and self.board[r+d][c] == ".":
                    moves.append((r+2*d, c))
            # 공격
            for dc in [-1, 1]:
                if 0 <= r+d < 8 and 0 <= c+dc < 8:
                    target = self.board[r+d][c+dc]
                    if (target != "." and (target.islower() if is_w else target.isupper())) or attack:
                        moves.append((r+d, c+dc))
                    # 앙파상
                    if not attack and self.en_passant_target == (r+d, c+dc):
                        moves.append((r+d, c+dc))
            
            if "졸병 진화" in self.augments[color]:
                for dc in [-1, 1]:
                    if 0 <= c+dc < 8 and self.board[r][c+dc] == ".": moves.append((r, c+dc))

        elif p.lower() == "n" or (p.lower() == "k" and "칸의 후예" in self.augments[color]):
            steps = [(2,1),(1,2),(-1,2),(-2,1),(-2,-1),(-1,-2),(1,-2),(2,-1)]
            for dr, dc in steps:
                nr, nc = r+dr, c+dc
                if 0 <= nr < 8 and 0 <= nc < 8: moves.append((nr, nc))
            if p.lower() == "n":
                if "초살병기 나이트" in self.augments[color]:
                    for dr, dc in [(1,0),(-1,0),(0,1),(0,-1)]:
                        nr, nc = r, c
                        while True:
                            nr += dr; nc += dc
                            if not (0 <= nr < 8 and 0 <= nc < 8): break
                            moves.append((nr, nc))
                            if self.board[nr][nc] != ".": break
                if "결전병기 나이트" in self.augments[color]:
                    for dr, dc in [(1,1),(1,-1),(-1,1),(-1,-1)]:
                        nr, nc = r, c
                        while True:
                            nr += dr; nc += dc
                            if not (0 <= nr < 8 and 0 <= nc < 8): break
                            moves.append((nr, nc))
                            if self.board[nr][nc] != ".": break

        if p.lower() in ["r", "b", "q"] or (p.lower() == "k" and "진정한 왕은 누구인가?" in self.augments[color]):
            dirs = []
            if p.lower() in ["b", "q"] or (p.lower() == "k" and "진정한 왕은 누구인가?" in self.augments[color]): dirs += [(1,1),(1,-1),(-1,1),(-1,-1)]
            if p.lower() in ["r", "q"] or (p.lower() == "k" and "진정한 왕은 누구인가?" in self.augments[color]): dirs += [(1,0),(-1,0),(0,1),(0,-1)]
            for dr, dc in dirs:
                nr, nc = r, c
                while True:
                    nr += dr; nc += dc
                    if not (0 <= nr < 8 and 0 <= nc < 8): break
                    moves.append((nr, nc))
                    if self.board[nr][nc] != ".":
                        if "저격 비숍" in self.augments[color] and p.lower() == "b": pass
                        elif "메테오 스트라이크" in self.augments[color] and p.lower() == "r": pass
                        else: break
        
        if p.lower() == "k":
            if "네크로맨시" in self.augments[color]:
                for dr in range(-1, 2):
                    for dc in range(-1, 2):
                        nr, nc = r+dr, c+dc
                        if 0 <= nr < 8 and 0 <= nc < 8 and self.board[nr][nc] == ".": moves.append((nr, nc))
            else:
                for dr in range(-1, 2):
                    for dc in range(-1, 2):
                        if dr == 0 and dc == 0: continue
                        nr, nc = r+dr, c+dc
                        if 0 <= nr < 8 and 0 <= nc < 8: moves.append((nr, nc))
            
            # 캐슬링
            if not attack:
                kr, kc = (7, 4) if is_w else (0, 4)
                if r == kr and c == kc and not self.moved["K" if is_w else "k"] and not self.is_in_check(color):
                    # 킹사이드
                    if not self.moved["R8" if is_w else "r8"] and self.board[kr][5] == "." and self.board[kr][6] == ".":
                        moves.append((kr, 6))
                    # 퀸사이드
                    if not self.moved["R1" if is_w else "r1"] and self.board[kr][1] == "." and self.board[kr][2] == "." and self.board[kr][3] == ".":
                        moves.append((kr, 2))

            if "킹스 어택" in self.augments[color]:
                for dr, dc in [(2,2),(2,-2),(-2,2),(-2,-2)]:
                    nr, nc = r+dr, c+dc
                    if 0 <= nr < 8 and 0 <= nc < 8: moves.append((nr, nc))
        return list(set(moves))

    def get_legal_moves(self, r, c):
        p = self.board[r][c]
        color = "w" if p.isupper() else "b"
        raw = self.get_moves_raw(r, c)
        legal = []
        for nr, nc in raw:
            target = self.board[nr][nc]
            if target != "." and ((color=="w" and target.isupper()) or (color=="b" and target.islower())): continue
            
            # 로열 가드 증강
            if target != "." and "로열 가드" in self.augments["b" if color=="w" else "w"]:
                opp_color = "b" if color=="w" else "w"
                opp_king = "k" if opp_color=="b" else "K"
                kr, kc = -1, -1
                for r_i in range(8):
                    for c_i in range(8):
                        if self.board[r_i][c_i] == opp_king: kr, kc = r_i, c_i; break
                if abs(nr-kr) <= 1 and abs(nc-kc) <= 1: continue

            # 가상 보드 체크
            temp = [row[:] for row in self.board]
            self.board[nr][nc] = p; self.board[r][c] = "."
            if not self.is_in_check(color): legal.append((nr, nc))
            self.board = temp
        return legal

    def is_in_check(self, color):
        opp = "b" if color == "w" else "w"
        tk = "K" if color == "w" else "k"
        kr, kc = -1, -1
        for r in range(8):
            for c in range(8):
                if self.board[r][c] == tk: kr, kc = r, c; break
        if kr == -1: return False
        for r in range(8):
            for c in range(8):
                p = self.board[r][c]
                if p != "." and ((opp == "w" and p.isupper()) or (opp == "b" and p.islower())):
                    if (kr, kc) in self.get_moves_raw(r, c, True): return True
        return False

    def has_moves(self, color):
        for r in range(8):
            for c in range(8):
                p = self.board[r][c]
                if p != "." and ((color == "w" and p.isupper()) or (color == "b" and p.islower())):
                    if self.get_legal_moves(r, c): return True
        return False

    def make_move(self, r1, c1, r2, c2):
        self.update_timers()
        self.save_state()
        p = self.board[r1][c1]
        is_w = p.isupper()
        color = "w" if is_w else "b"
        
        # 앙파상 처리
        if p.lower() == "p" and (r2, c2) == self.en_passant_target:
            self.board[r1][c2] = "."

        # 캐슬링 처리
        if p.lower() == "k":
            if abs(c2 - c1) == 2:
                if c2 == 6: # 킹사이드
                    self.board[r2][5] = "R" if is_w else "r"
                    self.board[r2][7] = "."
                elif c2 == 2: # 퀸사이드
                    self.board[r2][3] = "R" if is_w else "r"
                    self.board[r2][0] = "."
            self.moved["K" if is_w else "k"] = True
        
        if p.lower() == "r":
            if r1 == 7 and c1 == 0: self.moved["R1"] = True
            elif r1 == 7 and c1 == 7: self.moved["R8"] = True
            elif r1 == 0 and c1 == 0: self.moved["r1"] = True
            elif r1 == 0 and c1 == 7: self.moved["r8"] = True

        # 이동 실행
        if "열화우라늄날개안정분리철갑탄" in self.augments[color] and p.lower() == "b":
            for dr in range(-1, 2):
                for dc in range(-1, 2):
                    nr, nc = r2+dr, c2+dc
                    if 0 <= nr < 8 and 0 <= nc < 8 and self.board[nr][nc].lower() != "k": self.board[nr][nc] = "."
            self.board[r1][c1] = "."
        else:
            self.board[r2][c2] = p
            self.board[r1][c1] = "."

        # 승급
        if (p == "P" and r2 == 0) or (p == "p" and r2 == 7):
            self.board[r2][c2] = "Q" if p == "P" else "q"

        # 앙파상 타겟 설정
        self.en_passant_target = None
        if p.lower() == "p" and abs(r2 - r1) == 2:
            self.en_passant_target = ((r1 + r2) // 2, c1)

        # 턴 종료 처리
        if self.time_stop_left[color] > 0:
            self.time_stop_left[color] -= 1
        else:
            self.turn = "b" if color == "w" else "w"
            if self.turn == "w": self.full_turns += 1
        
        self.turn_start_time = time.time() 

        if not self.has_moves(self.turn):
            self.game_over = True
            if self.is_in_check(self.turn):
                self.winner = "WHITE" if self.turn == "b" else "BLACK"
                return "CHECKMATE"
            else:
                self.winner = "DRAW"
                return "STALEMATE"

        if self.full_turns in AUGMENT_SCHEDULE and self.turn == "w":
            return "AUG_PHASE"
        return "OK"

class GameApp:
    def __init__(self):
        self.state = STATE_LOBBY
        self.game = ChessLogic()
        self.is_augment_mode = True
        self.selected = None
        self.valid_moves = []
        self.aug_phase_step = "WHITE"
        self.current_selection = []
        self.available_pool = list(AUGMENT_POOL)
        
        self.shake_enabled = True
        self.timer_visible = True
        self.board_theme = "classic"
        self.themes = {
            "classic": {"light": (235, 235, 210), "dark": (120, 150, 90)},
            "dark": {"light": (100, 100, 105), "dark": (45, 45, 55)},
            "ocean": {"light": (173, 216, 230), "dark": (70, 130, 180)}
        }
        self.shake_amount = 0
        self.log_scroll_y = 0
        self.log_container_height = HEIGHT - 120
        
        # 버튼
        self.rect_start_aug = pygame.Rect(WIDTH//2 - 120, HEIGHT//2 - 60, 240, 50)
        self.rect_start_norm = pygame.Rect(WIDTH//2 - 120, HEIGHT//2 + 10, 240, 50)
        self.rect_settings = pygame.Rect(WIDTH//2 - 120, HEIGHT//2 + 80, 240, 50)
        
        self.rect_set_shake = pygame.Rect(WIDTH//2 - 100, 220, 200, 40)
        self.rect_set_timer = pygame.Rect(WIDTH//2 - 100, 280, 200, 40)
        self.rect_set_theme = pygame.Rect(WIDTH//2 - 100, 340, 200, 40)
        self.rect_set_back = pygame.Rect(WIDTH//2 - 100, 450, 200, 40)

        rx = SIDE_WIDTH + BOARD_SIZE + 20
        self.rect_side_undo = pygame.Rect(rx, HEIGHT - 150, 210, 45)
        self.rect_side_lobby = pygame.Rect(rx, HEIGHT - 90, 210, 45)

        self.aug_cards = [pygame.Rect(WIDTH//2 - 380, 220, 230, 320), 
                          pygame.Rect(WIDTH//2 - 115, 220, 230, 320),
                          pygame.Rect(WIDTH//2 + 150, 220, 230, 320)]

    def apply_aug(self, color, aug):
        self.game.augments[color].append(aug["name"])
        is_w = (color == "w")
        
        if aug["id"] == "descendant_of_khan":
            target = "B" if is_w else "b"
            replace = "N" if is_w else "n"
            for r in range(8):
                for c in range(8):
                    if self.game.board[r][c] == target: self.game.board[r][c] = replace
        elif aug["id"] == "true_king":
            target = "Q" if is_w else "q"
            for r in range(8):
                for c in range(8):
                    if self.game.board[r][c] == target: self.game.board[r][c] = "."
        elif aug["id"] == "road_to_heaven": 
            self.game.heaven_trigger[color] = True
        elif aug["id"] == "time_stop": 
            self.game.time_stop_left[color] = 3
        elif aug["id"] == "gravity_flip": 
            self.game.gravity_flip = True
        elif aug["id"] == "pawn_world_nerfed":
            opp_color = "b" if color == "w" else "w"
            targets = []
            for r in range(8):
                for c in range(8):
                    pc = self.game.board[r][c]
                    if pc != "." and ((opp_color == "w" and pc.isupper()) or (opp_color == "b" and pc.islower())) and pc.lower() != "k":
                        targets.append((r, c))
            for tr, tc in random.sample(targets, min(3, len(targets))):
                self.game.board[tr][tc] = "P" if opp_color == "w" else "p"
        elif aug["id"] == "pawn_front_line":
            d = -1 if is_w else 1
            if self.game.gravity_flip: d = -d
            temp_board = [row[:] for row in self.game.board]
            pawn = "P" if is_w else "p"
            for r in range(8):
                for c in range(8):
                    if self.game.board[r][c] == pawn:
                        nr = r + d
                        if 0 <= nr < 8 and temp_board[nr][c].lower() != "k":
                            temp_board[nr][c] = pawn
                            temp_board[r][c] = "."
            self.game.board = temp_board
        elif aug["id"] == "chess960":
            r_idx = 7 if color == "w" else 0
            pcs = [self.game.board[r_idx][c] for c in range(8) if self.game.board[r_idx][c].lower() not in ["k", "p"]]
            random.shuffle(pcs)
            idx = 0
            for c in range(8):
                if self.game.board[r_idx][c].lower() not in ["k", "p"]:
                    self.game.board[r_idx][c] = pcs[idx]; idx += 1
        
        # '천국에 가는 길' 사용 시 다음 풀에 '중력 반전' 강제 포함 처리
        if aug["id"] != "road_to_heaven":
            if self.available_pool:
                self.available_pool = [a for a in self.available_pool if a["id"] != aug["id"]]

    def draw_lobby(self):
        screen.fill((20, 20, 25))
        title = font_title.render("AUGMENT CHESS V13.0", True, (0, 255, 150))
        screen.blit(title, title.get_rect(center=(WIDTH//2, HEIGHT//2 - 150)))
        
        for rect, text, col in [(self.rect_start_aug, "증강 체스 시작", (180, 130, 30)), 
                                (self.rect_start_norm, "일반 체스 시작", (80, 100, 120)),
                                (self.rect_settings, "세팅", (100, 100, 105))]:
            pygame.draw.rect(screen, col, rect, border_radius=10)
            txt_surf = font_menu.render(text, True, (255, 255, 255))
            screen.blit(txt_surf, txt_surf.get_rect(center=rect.center))

    def draw_settings(self):
        screen.fill((25, 25, 30))
        title = font_title.render("SETTINGS", True, (255, 255, 255))
        screen.blit(title, title.get_rect(center=(WIDTH//2, 100)))
        for rect, text in [(self.rect_set_shake, f"화면 진동: {'ON' if self.shake_enabled else 'OFF'}"),
                           (self.rect_set_timer, f"타이머 표시: {'ON' if self.timer_visible else 'OFF'}"),
                           (self.rect_set_theme, f"테마: {self.board_theme.upper()}")]:
            pygame.draw.rect(screen, (60, 60, 70), rect, border_radius=5)
            s_surf = font_menu.render(text, True, (255, 255, 255))
            screen.blit(s_surf, s_surf.get_rect(center=rect.center))
        pygame.draw.rect(screen, (100, 50, 50), self.rect_set_back, border_radius=5)
        b_surf = font_menu.render("BACK", True, (255, 255, 255))
        screen.blit(b_surf, b_surf.get_rect(center=self.rect_set_back.center))

    def draw_left_panel(self):
        panel_rect = pygame.Rect(0, 0, SIDE_WIDTH, HEIGHT)
        pygame.draw.rect(screen, (30, 30, 35), panel_rect)
        pygame.draw.line(screen, (60, 60, 70), (SIDE_WIDTH-1, 0), (SIDE_WIDTH-1, HEIGHT), 2)
        title = font_title.render("GAME RECORD", True, (200, 200, 200))
        screen.blit(title, (20, 25))
        log_surface = pygame.Surface((SIDE_WIDTH - 40, len(self.game.move_log) * 22 + 50), pygame.SRCALPHA)
        for i, log in enumerate(self.game.move_log):
            turn_num = i // 2 + 1
            color_prefix = "W: " if i % 2 == 0 else "B: "
            txt = font_log.render(f"{turn_num}. {color_prefix}{log}", True, (180, 180, 180))
            log_surface.blit(txt, (10, i * 22))
        screen.blit(log_surface, (20, 70 - self.log_scroll_y), area=pygame.Rect(0, self.log_scroll_y, SIDE_WIDTH-20, self.log_container_height))
        if log_surface.get_height() > self.log_container_height:
            sb_h = max(30, self.log_container_height * (self.log_container_height / log_surface.get_height()))
            sb_y = 70 + (self.log_scroll_y / (log_surface.get_height() - self.log_container_height)) * (self.log_container_height - sb_h)
            pygame.draw.rect(screen, (80, 80, 90), (SIDE_WIDTH - 10, sb_y, 4, sb_h), border_radius=2)

    def draw_right_panel(self):
        x = SIDE_WIDTH + BOARD_SIZE
        pygame.draw.rect(screen, (25, 25, 30), (x, 0, SIDE_WIDTH, HEIGHT))
        pygame.draw.line(screen, (60, 60, 70), (x, 0), (x, HEIGHT), 2)
        if self.timer_visible:
            curr_t = {"w": self.game.total_time["w"], "b": self.game.total_time["b"]}
            if not self.game.game_over: curr_t[self.game.turn] += (time.time() - self.game.turn_start_time)
            # 백색 타이머
            pygame.draw.rect(screen, (240, 240, 240) if self.game.turn == 'w' else (50, 50, 55), (x + 20, 20, SIDE_WIDTH - 40, 80), border_radius=10)
            w_time_str = f"{int(curr_t['w']) // 60:02}:{int(curr_t['w']) % 60:02}"
            screen.blit(font_small.render("WHITE TOTAL TIME", True, (80, 80, 80) if self.game.turn == 'w' else (180, 180, 180)), (x + 35, 30))
            screen.blit(font_timer.render(w_time_str, True, (20, 20, 20) if self.game.turn == 'w' else (200, 200, 200)), (x + 35, 50))
            # 흑색 타이머
            pygame.draw.rect(screen, (40, 40, 45) if self.game.turn == 'b' else (50, 50, 55), (x + 20, 110, SIDE_WIDTH - 40, 80), border_radius=10)
            if self.game.turn == 'b': pygame.draw.rect(screen, (0, 255, 150), (x + 20, 110, SIDE_WIDTH - 40, 80), 2, border_radius=10)
            b_time_str = f"{int(curr_t['b']) // 60:02}:{int(curr_t['b']) % 60:02}"
            screen.blit(font_small.render("BLACK TOTAL TIME", True, (180, 180, 180)), (x + 35, 120))
            screen.blit(font_timer.render(b_time_str, True, (255, 255, 255)), (x + 35, 140))
        turn_txt = font_menu.render(f"▶ {'WHITE' if self.game.turn == 'w' else 'BLACK'} TURN", True, (255, 215, 0))
        screen.blit(turn_txt, (x + 25, 210))
        screen.blit(font_small.render("[ACTIVE AUGMENTS]", True, (0, 255, 150)), (x + 20, 250))
        for i, aug in enumerate(self.game.augments[self.game.turn][-10:]):
            screen.blit(font_log.render(f"• {aug}", True, (200, 200, 200)), (x + 25, 275 + i * 18))
        for rect, text, col in [(self.rect_side_undo, "무르기 (UNDO)", (100, 50, 50)), (self.rect_side_lobby, "로비로 (LOBBY)", (60, 60, 70))]:
            pygame.draw.rect(screen, col, rect, border_radius=8)
            t_surf = font_menu.render(text, True, (255, 255, 255))
            screen.blit(t_surf, t_surf.get_rect(center=rect.center))

    def draw_game(self):
        offset_x, offset_y = 0, 0
        if self.shake_amount > 0:
            offset_x = random.randint(-int(self.shake_amount), int(self.shake_amount))
            offset_y = random.randint(-int(self.shake_amount), int(self.shake_amount))
            self.shake_amount *= 0.9
            if self.shake_amount < 0.5: self.shake_amount = 0
        screen.fill((20, 20, 25))
        bx = SIDE_WIDTH
        theme = self.themes[self.board_theme]
        for r in range(8):
            for c in range(8):
                col = theme["light"] if (r + c) % 2 == 0 else theme["dark"]
                pygame.draw.rect(screen, col, (bx + c * CELL + offset_x, r * CELL + offset_y, CELL, CELL))
                if self.selected == (r, c): pygame.draw.rect(screen, (255, 255, 0), (bx + c * CELL + offset_x, r * CELL + offset_y, CELL, CELL), 4)
                if (r, c) in self.valid_moves:
                    ov = pygame.Surface((CELL, CELL), pygame.SRCALPHA); pygame.draw.circle(ov, (0, 0, 0, 60), (CELL//2, CELL//2), 10)
                    screen.blit(ov, (bx + c * CELL + offset_x, r * CELL + offset_y))
                p = self.game.board[r][c]
                if p != ".":
                    txt = font_piece.render(PIECE_UNICODE[p], True, (0,0,0) if p.isupper() else (40,40,40))
                    screen.blit(txt, txt.get_rect(center=(bx + c * CELL + CELL//2 + offset_x, r * CELL + CELL//2 + offset_y)))
        self.draw_left_panel(); self.draw_right_panel()
        if self.state == STATE_AUGMENT_SELECT:
            ov = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA); ov.fill((0,0,0,230)); screen.blit(ov, (0,0))
            title = font_title.render(f"SELECT AUGMENT: {self.aug_phase_step}", True, (255, 215, 0))
            screen.blit(title, title.get_rect(center=(WIDTH//2, 80)))
            for i, aug in enumerate(self.current_selection):
                rect = self.aug_cards[i]
                pygame.draw.rect(screen, (45, 45, 60), rect, border_radius=15); pygame.draw.rect(screen, (255, 215, 0), rect, 2, border_radius=15)
                n = font_menu.render(aug["name"], True, (255, 255, 255)); screen.blit(n, n.get_rect(center=(rect.centerx, rect.y + 40)))
                y_o = 100
                for line in [aug["desc"][j:j+14] for j in range(0, len(aug["desc"]), 14)]:
                    l_s = font_small.render(line, True, (200, 200, 200)); screen.blit(l_s, l_s.get_rect(center=(rect.centerx, rect.y + y_o))); y_o += 22
        if self.game.game_over:
            ov = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA); ov.fill((0,0,0,180)); screen.blit(ov, (0,0))
            res_txt = f"GAME OVER: {self.game.winner} WIN!" if self.game.winner != "DRAW" else "GAME OVER: DRAW"
            screen.blit(font_title.render(res_txt, True, (255, 255, 0)), font_title.render(res_txt, True, (255, 255, 0)).get_rect(center=(WIDTH//2, HEIGHT//2 - 20)))
            lobby_rect = pygame.Rect(WIDTH//2 - 100, HEIGHT//2 + 40, 200, 50); pygame.draw.rect(screen, (80, 80, 90), lobby_rect, border_radius=10)
            l_surf = font_menu.render("RETURN TO LOBBY", True, (255, 255, 255)); screen.blit(l_surf, l_surf.get_rect(center=lobby_rect.center))

    def handle_click(self, pos):
        if self.state == STATE_LOBBY:
            if self.rect_start_aug.collidepoint(pos): self.game.reset(); self.is_augment_mode = True; self.state = STATE_GAME
            elif self.rect_start_norm.collidepoint(pos): self.game.reset(); self.is_augment_mode = False; self.state = STATE_GAME
            elif self.rect_settings.collidepoint(pos): self.state = STATE_SETTINGS
        elif self.state == STATE_SETTINGS:
            if self.rect_set_shake.collidepoint(pos): self.shake_enabled = not self.shake_enabled
            elif self.rect_set_timer.collidepoint(pos): self.timer_visible = not self.timer_visible
            elif self.rect_set_theme.collidepoint(pos):
                ts = list(self.themes.keys())
                self.board_theme = ts[(ts.index(self.board_theme) + 1) % len(ts)]
            elif self.rect_set_back.collidepoint(pos): self.state = STATE_LOBBY
        elif self.state == STATE_GAME:
            if self.rect_side_undo.collidepoint(pos): self.game.undo(); return
            if self.rect_side_lobby.collidepoint(pos): self.state = STATE_LOBBY; return
            if self.game.game_over:
                if pygame.Rect(WIDTH//2 - 100, HEIGHT//2 + 40, 200, 50).collidepoint(pos): self.state = STATE_LOBBY
                return
            x, y = pos
            if SIDE_WIDTH <= x <= SIDE_WIDTH + BOARD_SIZE:
                c, r = (x - SIDE_WIDTH)//CELL, y//CELL
                if self.selected:
                    if (r, c) in self.valid_moves:
                        p_from = self.game.board[self.selected[0]][self.selected[1]]
                        res = self.game.make_move(self.selected[0], self.selected[1], r, c)
                        self.game.move_log.append(f"{p_from}{chr(97+c)}{8-r}")
                        self.log_scroll_y = max(0, len(self.game.move_log) * 22 - self.log_container_height)
                        if res == "CHECKMATE" and self.shake_enabled: self.shake_amount = 25
                        if self.is_augment_mode and res == "AUG_PHASE":
                            self.state = STATE_AUGMENT_SELECT; self.aug_phase_step = "WHITE"
                            self.prepare_selection("w")
                    self.selected, self.valid_moves = None, []
                else:
                    p = self.game.board[r][c]
                    if p != "." and ((self.game.turn == "w" and p.isupper()) or (self.game.turn == "b" and p.islower())):
                        self.selected = (r, c); self.valid_moves = self.game.get_legal_moves(r, c)
        elif self.state == STATE_AUGMENT_SELECT:
            for i, rect in enumerate(self.aug_cards):
                if rect.collidepoint(pos) and i < len(self.current_selection):
                    color = "w" if self.aug_phase_step == "WHITE" else "b"
                    self.apply_aug(color, self.current_selection[i])
                    if self.aug_phase_step == "WHITE":
                        self.aug_phase_step = "BLACK"
                        self.prepare_selection("b")
                    else: self.state = STATE_GAME

    def prepare_selection(self, color):
        pool = list(self.available_pool)
        # 천국에 가는 길 로직: 중력 반전 강제 등장
        if self.game.heaven_trigger[color]:
            gv = [a for a in pool if a["id"] == "gravity_flip"]
            others = [a for a in pool if a["id"] != "gravity_flip"]
            if gv:
                random.shuffle(others)
                self.current_selection = gv + others[:2]
                self.game.heaven_trigger[color] = False # 트리거 소모
                return
        self.current_selection = random.sample(pool, min(3, len(pool)))

    def run(self):
        clock = pygame.time.Clock()
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT: pygame.quit(); sys.exit()
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 4: self.log_scroll_y = max(0, self.log_scroll_y - 22)
                    elif event.button == 5: self.log_scroll_y = min(max(0, len(self.game.move_log) * 22 - self.log_container_height), self.log_scroll_y + 22)
                    else: self.handle_click(event.pos)
            if self.state == STATE_LOBBY: self.draw_lobby()
            elif self.state == STATE_SETTINGS: self.draw_settings()
            else: self.draw_game()
            pygame.display.flip(); clock.tick(60)

if __name__ == "__main__":
    app = GameApp()
    app.run()