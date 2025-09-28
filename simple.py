import pygame
import sys
import time
import numpy as np
import random
import pyganim
from PIL import Image
import os 
import math


"""
bird painter:https://pixabay.com/gifs/humming-bird-bird-fly-wings-4234/
owl painter:https://pixabay.com/gifs/bird-hark-eagle-fly-flying-wings-15079/
pake command: 
exe小:nuitka --standalone --onefile --plugin-enable=pylint-warnings --output-dir=dist simple.py
快速編譯/exe大:python -m nuitka --standalone --onefile --lto=no simple.py
"""

# --- 初始化 Pygame ---
pygame.init()
# 設置混音器參數，確保聲音品質
pygame.mixer.init(frequency=44100, size=-16, channels=2) 
screen_height = 600
screen_width = 1100
screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption("Procedural Music Plane Game")
clock = pygame.time.Clock()

# --- 遊戲狀態 ---
GAME_STATE = {
    'RUNNING': 1,
    'WIN': 2,
    'LOSE': 3
}
current_game_state = GAME_STATE['RUNNING'] 

# --- 遊戲常數 ---
OWL_SCORE = -0.4
BIRD_SCORE = 0.25
WIN_SCORE = 500.0
LOSE_SCORE = 0.0
SPAWN_INTERVAL = 40 # 將生成間隔作為全域常數
energy_max = 500.0
energy_bar_height = 20

# --- 初始化字體 ---
pygame.font.init()
font = pygame.font.SysFont('Consolas', 20)
large_font = pygame.font.SysFont('Consolas', 48, bold=True)
button_font = pygame.font.SysFont('Consolas', 30, bold=True)

# --- 圖片與動畫設定 ---
BIRD_PATH = os.path.join('.', 'image', 'bird.gif')
OWL_PATH = os.path.join('.', 'image', 'owl.gif')

BIRD_SCALE = (100, 100)
OWL_SCALE = (100, 100) 
# -----------------------------

# --- 載入 GIF 函數  ---
def load_gif_animation(path, new_scale, flip_x=False):
    pil_img = Image.open(path)
    frames = []
    DEFAULT_DURATION_MS = 100 
    try:
        while True:
            frame = pil_img.convert('RGBA')
            mode = frame.mode
            size = frame.size
            data = frame.tobytes()
            
            pygame_image = pygame.image.fromstring(data, size, mode)
            pygame_image = pygame.transform.scale(pygame_image, new_scale)
            if flip_x:
                pygame_image = pygame.transform.flip(pygame_image, True, False)
            duration_ms = pil_img.info.get('duration', DEFAULT_DURATION_MS)
            duration_int_ms = max(int(duration_ms), 10) 
            frames.append((pygame_image, duration_int_ms))
            pil_img.seek(pil_img.tell() + 1)
    except EOFError:
        pass
    except Exception as e:
        print(f"載入 GIF 發生錯誤：{e}")
        temp_surface = pygame.Surface(new_scale)
        temp_surface.fill((255, 0, 255))
        anim = pyganim.PygAnimation([(temp_surface, 1000)])
        anim.play()
        return anim
    if not frames:
        raise ValueError(f"無法從路徑 {path} 載入任何 GIF 幀。請確認檔案存在且非空。")
    anim = pyganim.PygAnimation(frames)
    anim.play()
    return anim

# --- 全域載入動畫 ---
try:
    BIRD_ANIM = load_gif_animation(BIRD_PATH, BIRD_SCALE, flip_x=False) 
    OWL_ANIM = load_gif_animation(OWL_PATH, OWL_SCALE, flip_x=True) 
except Exception as e:
    print(f"警告：GIF 載入失敗，將使用預設佔位圖。錯誤: {e}")
    # 提供一個基本的 PygAnimation 作為 fallback
    TEMP_SURF_BIRD = pygame.Surface(BIRD_SCALE, pygame.SRCALPHA)
    TEMP_SURF_BIRD.fill((0, 255, 255, 128))
    BIRD_ANIM = pyganim.PygAnimation([(TEMP_SURF_BIRD, 1000)])
    BIRD_ANIM.play()
    
    TEMP_SURF_OWL = pygame.Surface(OWL_SCALE, pygame.SRCALPHA)
    TEMP_SURF_OWL.fill((255, 0, 255, 128))
    OWL_ANIM = pyganim.PygAnimation([(TEMP_SURF_OWL, 1000)])
    OWL_ANIM.play()
# -----------------------------

# --- 飛行物件類別 ---
class FlyingObject:
    def __init__(self, x, y, anim_obj, obj_size, speed=3, obj_type="unknown"): 
        self.anim = anim_obj
        self.rect = pygame.Rect(x, y, obj_size[0], obj_size[1]) 
        self.speed = speed
        self.type = obj_type 

    def move(self):
        self.rect.x -= self.speed

    def draw(self, surface, camera_offset):
        self.anim.blit(surface, (self.rect.x, self.rect.y - camera_offset))
# -----------------------------


# --- 音樂相關函數 ---
def freq_from_semitone(base, semitone):
    return base * (2 ** (semitone / 12))

def generate_sound(freq, duration=1.0, volume=0.2, sample_rate=44100, harmonics=7):
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    waveform = np.zeros_like(t)
    for n in range(1, harmonics + 1):  
        partial = np.sin(2 * np.pi * freq * n * t)
        waveform += (1.0 / n) * partial 
    max_amp = np.max(np.abs(waveform))
    if max_amp > 0:
        waveform /= max_amp
    waveform = (waveform * 32767 * volume).astype(np.int16)
    stereo_waveform = np.column_stack([waveform, waveform])
    sound = pygame.sndarray.make_sound(stereo_waveform)
    sound.set_volume(volume)
    return sound

def generate_drum(duration=0.5, sample_rate=44100):
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    freq = 100
    envelope = np.exp(-5 * t)
    wave = np.sin(2 * np.pi * freq * t) * envelope
    noise = (np.random.rand(len(t)) * 2 - 1) * 0.2 * envelope
    wave += noise
    audio = np.int16(wave * 32767)
    stereo = np.column_stack((audio, audio))
    sound = pygame.sndarray.make_sound(stereo)
    return sound

drum_sound = generate_drum()
base_freq = 440.0 

# --- 飛機類別 ---
class Plane:
    def __init__(self, x, y):
        try:
            self.image = pygame.image.load('./image/plane.png').convert_alpha()
        except pygame.error:
            print("WARNING: 'image/plane.png' not found. Using a square.")
            self.image = pygame.Surface((100, 100), pygame.SRCALPHA)
            self.image.fill((100, 100, 255, 180))

        self.image = pygame.transform.scale(self.image, (100, 100))
        self.base_image = self.image  
        self.rect = self.image.get_rect()
        self.rect.center = (x, y)
        self.speed = 3
        self.current_freq = None
        self.current_sound = None
        self.tilt_angle = 0  
        self.paused = False 
        self.max_tilt = 20
        self.detection_radius = 85
        self.show_radius = True 

    def draw(self, camera_offset):
        if self.show_radius:
            radius_center_screen = (self.rect.centerx, self.rect.centery - camera_offset)
            pygame.draw.circle(screen, (255, 255, 255), radius_center_screen, self.detection_radius, 1) 
        
        rotated_img = pygame.transform.rotate(self.base_image, self.tilt_angle)
        new_rect = rotated_img.get_rect(center=(self.rect.centerx, self.rect.centery - camera_offset)) 
        screen.blit(rotated_img, new_rect.topleft)

    def move_vertical(self, direction):
        if direction == 'up':
            self.rect.y -= self.speed
            self.tilt_angle = min(self.tilt_angle + 2, self.max_tilt)  
        if direction == 'down':
            self.rect.y += self.speed
            self.tilt_angle = max(self.tilt_angle - 2, -self.max_tilt)  

    def update_tilt(self):
        if self.tilt_angle > 0:
            self.tilt_angle = max(0, self.tilt_angle - 1)
        elif self.tilt_angle < 0:
            self.tilt_angle = min(0, self.tilt_angle + 1)

    def move_to_center(self, center_x):
        if self.rect.centerx < center_x:
            self.rect.x += self.speed

    def get_objects_in_radius(self, objects_list):
        player_center_world = self.rect.center 
        nearby_objects = []
        
        for obj in objects_list:
            obj_center = obj.rect.center
            distance = np.linalg.norm(np.array(player_center_world) - np.array(obj_center))
            
            if distance <= self.detection_radius:
                nearby_objects.append(obj)
                
        type_counts = {}
        delta_score = 0
        for obj in nearby_objects:
            obj_type = obj.type
            type_counts[obj_type] = type_counts.get(obj_type, 0) + 1
            
            if obj_type == 'owl':
                delta_score += OWL_SCORE 
            elif obj_type == 'bird':
                delta_score += BIRD_SCORE 
                
        return nearby_objects, type_counts, delta_score


# --- 遊戲主流程變數初始化 ---
center_x = screen_width // 2
camera_offset = 0
semitone_jump = 5
energy_cost = 5.8
energy_increase_rate = 2.6
C_major = [0, 2, 4, 5, 7, 9, 11] 
freq = 442
elapsed_time_sec = 0.0 

player = None
flying_objects = []
spawn_timer = 0
music_line = []
start_game_time = 0.0
music_time_start = 0.0
energy = 180.0
current_delta_score = 0
nearby_objects = []
type_counts = {}

music_mode = False

# --- 遊戲初始化和重置函數 ---
def reset_game():
    global player, flying_objects, spawn_timer, music_line, start_game_time, music_time_start, energy, current_game_state, current_delta_score, nearby_objects, type_counts, elapsed_time_sec

    # 停止所有正在播放的聲音
    if player and player.current_sound:
        player.current_sound.stop()
    pygame.mixer.stop() 

    # 重置遊戲狀態
    current_game_state = GAME_STATE['RUNNING']

    # 重置時間 
    start_game_time = time.time()
    music_time_start = time.time() # 專門用於音樂節拍的計時器
    elapsed_time_sec = 0.0

    # 重置飛機
    player = Plane(100, screen_height // 2)
    
    # 重置物件和分數
    flying_objects = []
    spawn_timer = 0
    music_line = []
    energy = 200.0
    current_delta_score = 0
    nearby_objects = []
    type_counts = {}
    player.paused = False 

# --- 終止畫面繪製函數 ---
def draw_end_screen(state, time_taken=None):
    overlay = pygame.Surface((screen_width, screen_height))
    overlay.set_alpha(150)
    overlay.fill((0, 0, 0))
    screen.blit(overlay, (0, 0))

    if state == GAME_STATE['WIN']:
        text = "SUCCESS! Mission Accomplished"
        color = (0, 255, 0)
    else:
        text = "GAME OVER"
        color = (255, 0, 0)
        
    title_surface = large_font.render(text, True, color)
    title_rect = title_surface.get_rect(center=(screen_width // 2, screen_height // 2 - 100))
    screen.blit(title_surface, title_rect)
    
    if time_taken is not None:
        minutes = int(time_taken // 60)
        seconds = int(time_taken % 60)
        time_text = f"Time: {minutes:02d}m {seconds:02d}s"
        time_surface = font.render(time_text, True, (255, 255, 255))
        time_rect = time_surface.get_rect(center=(screen_width // 2, screen_height // 2 - 30))
        screen.blit(time_surface, time_rect)

    button_text = "RESTART (R)"
    button_color = (0, 150, 255)
    hover_color = (0, 200, 255)
    
    button_width = 250
    button_height = 60
    button_x = (screen_width - button_width) // 2
    button_y = screen_height // 2 + 50
    
    button_rect = pygame.Rect(button_x, button_y, button_width, button_height)
    
    mouse_pos = pygame.mouse.get_pos()
    current_color = hover_color if button_rect.collidepoint(mouse_pos) else button_color
    
    pygame.draw.rect(screen, current_color, button_rect, border_radius=10)
    pygame.draw.rect(screen, (255, 255, 255), button_rect, 3, border_radius=10)
    
    text_surface = button_font.render(button_text, True, (255, 255, 255))
    text_rect = text_surface.get_rect(center=button_rect.center)
    screen.blit(text_surface, text_rect)
    
    return button_rect

# --- 啟動遊戲 (第一次初始化) ---
reset_game() 

# --- 主遊戲迴圈 ---
while True:
    if music_mode:
        WIN_SCORE = math.inf
        energy += 350
    
    # --- 事件處理 ---
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            if player and player.current_sound:
                player.current_sound.stop()
            pygame.quit()
            sys.exit()

        if current_game_state == GAME_STATE['RUNNING']:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if player and player.current_sound:
                        player.current_sound.stop()
                    pygame.quit()
                    sys.exit()
                
                # ... 快速跳躍邏輯 ...
                if event.key == pygame.K_w and energy >= energy_cost:
                    player.rect.y -= semitone_jump * 10
                    player.tilt_angle = player.max_tilt 
                    energy -= energy_cost
                
                if event.key == pygame.K_s and energy >= energy_cost:
                    player.rect.y += semitone_jump * 10
                    player.tilt_angle = -player.max_tilt 
                    energy -= energy_cost
                
                if event.key == pygame.K_SPACE:  
                    drum_sound.play()

                if event.key == pygame.K_p:
                    music_mode = True
        
        elif current_game_state in [GAME_STATE['WIN'], GAME_STATE['LOSE']]:
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1: 
                    # 檢查按鈕點擊
                    if 'restart_button_rect' in locals() and restart_button_rect.collidepoint(event.pos):
                        reset_game()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_r: 
                 reset_game()


    # --- 遊戲邏輯與繪圖 ---
    screen.fill((0, 0, 0))
    keys = pygame.key.get_pressed()
    
    if current_game_state == GAME_STATE['RUNNING']:
        
        # 1. 玩家移動
        if keys[pygame.K_UP]:
            player.move_vertical('up')
        if keys[pygame.K_DOWN]:
            player.move_vertical('down')
            
        player.move_to_center(center_x)
        camera_offset = player.rect.centery - screen_height // 2
        
        # 2. 飛行物件生成與更新
        spawn_timer += 1
        if spawn_timer > SPAWN_INTERVAL:
            spawn_timer = 0
            y_pos = random.randint(camera_offset - 20, camera_offset + screen_height + 20 - max(BIRD_SCALE[1], OWL_SCALE[1])) 
            x_pos = screen_width + random.randint(0, 200) 
            
            if random.random() < 0.39:
                flying_objects.append(
                    FlyingObject(x_pos, y_pos, BIRD_ANIM, BIRD_SCALE, speed=random.randint(3, 5), obj_type='bird')
                )
            else:
                flying_objects.append(
                    FlyingObject(x_pos, y_pos, OWL_ANIM, OWL_SCALE, speed=random.randint(4, 7), obj_type='owl')
                )

        for obj in flying_objects[:]:
            obj.move()
            obj.draw(screen, camera_offset) 
            if obj.rect.right < 0:
                flying_objects.remove(obj)
        
        # 3. 能源更新 (持續回饋)
        delta_time = clock.get_time() / 1000.0
        energy += energy_increase_rate * delta_time 

        # 4. 音樂/偵測邏輯
        if keys[pygame.K_a]:
            if not player.paused:
                if player.current_sound:
                    player.current_sound.stop()
                player.paused = True
            player.show_radius = False
            nearby_objects = []
            type_counts = {}
            current_delta_score = 0
            energy -= 0.11
        else:
            if player.paused:
                player.paused = False
                if player.current_freq:
                    # 修正：確保重新播放時使用上次的頻率
                    sound = generate_sound(player.current_freq, duration=1.0, harmonics=6) 
                    sound.play(loops=-1)
                    player.current_sound = sound
                    
            player.show_radius = True
            
            nearby_objects, type_counts, current_delta_score = player.get_objects_in_radius(flying_objects)
            energy += current_delta_score

        # 5. 限制能源上下限 
        energy = max(LOSE_SCORE, min(energy, energy_max))
        
        # 6. 檢查勝利/失敗條件 (修正邏輯：狀態應只切換一次)
        if energy >= WIN_SCORE:
            if current_game_state == GAME_STATE['RUNNING']:
                if player.current_sound: player.current_sound.stop()
                elapsed_time_sec = time.time() - start_game_time 
                current_game_state = GAME_STATE['WIN']
        elif energy <= LOSE_SCORE:
            if current_game_state == GAME_STATE['RUNNING']:
                if player.current_sound: player.current_sound.stop()
                current_game_state = GAME_STATE['LOSE']
        
        # 7. 音樂和軌跡繪製 (僅在未暫停時)
        if player.paused == False:
            # 修正：使用 music_time_start 進行音樂節拍控制
            if time.time() - music_time_start > 0.1:
                music_line.append([player.rect.centerx, player.rect.centery])
                music_time_start = time.time()

                scale_degree = int((screen_height // 2 - player.rect.centery) / 10)
                offset_in_scale = C_major[scale_degree % len(C_major)] + (scale_degree // len(C_major)) * 12
                freq = freq_from_semitone(base_freq, offset_in_scale)

                if player.current_freq != freq:
                    if player.current_sound:
                        player.current_sound.stop()
                    sound = generate_sound(freq, duration=1.0, harmonics=6) 
                    sound.play(loops=-1)
                    player.current_freq = freq
                    player.current_sound = sound
            
            # 軌跡左移與繪製
            for point in music_line:
                point[0] -= 5
            music_line = [p for p in music_line if p[0] > 0]
            if len(music_line) > 1:
                adjusted_points = [(p[0], p[1] - camera_offset) for p in music_line]
                pygame.draw.lines(screen, (0, 255, 0), False, adjusted_points, 3)

        # 8. 畫飛機和資訊顯示
        player.draw(camera_offset)
        player.update_tilt()

        # 9. 能量條與資訊顯示
        pygame.draw.rect(screen, (50, 50, 50), (0, 0, screen_width, energy_bar_height))
        bar_width = int((energy / energy_max) * screen_width)
        pygame.draw.rect(screen, (255, 0, 0), (0, 0, bar_width, energy_bar_height))

        # 確保在遊戲進行中 freq 有一個有效值
        current_freq = player.current_freq if player.current_freq else freq
        midi_note = int(round(69 + 12 * np.log2(current_freq / 440.0)))
        text_surface = font.render(f"MIDI: {midi_note} | Freq: {current_freq:.1f} Hz | Score: {energy:.1f} / {WIN_SCORE:.1f}", True, (255, 255, 255))
        screen.blit(text_surface, (10, energy_bar_height + 5))

        detection_text = f"Nearby ({len(nearby_objects)}): "
        if type_counts:
            detection_text += ", ".join([f"{t}: {c}" for t, c in type_counts.items()])
            detection_text += f" | Score Change: {current_delta_score:.2f}"
        else:
            detection_text += "None"
            
        detection_surface = font.render(detection_text, True, (255, 255, 0))
        screen.blit(detection_surface, (10, energy_bar_height + 30))

    elif current_game_state == GAME_STATE['WIN']:
        # 勝利畫面
        restart_button_rect = draw_end_screen(GAME_STATE['WIN'], elapsed_time_sec)

    elif current_game_state == GAME_STATE['LOSE']:
        # 失敗畫面
        restart_button_rect = draw_end_screen(GAME_STATE['LOSE'])


    pygame.display.update()
    clock.tick(60)