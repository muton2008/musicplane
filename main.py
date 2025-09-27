import pygame
import sys
import time
import os
os.add_dll_directory(r"D:\allen\side-project\musicplane\fluidsynth-2.4.8-win10-x64\bin")  # Windows 下需要指定 DLL 路徑
import fluidsynth
import numpy as np

# --- 初始化 Pygame ---
pygame.init()
screen_height = 600
screen_width = 1100
screen = pygame.display.set_mode((screen_width, screen_height))
clock = pygame.time.Clock()

# --- 初始化 FluidSynth ---
fs = fluidsynth.Synth()
fs.start(driver="dsound")  # Windows 用 dsound，Mac/Linux 用 coreaudio/alsa
sfid = fs.sfload(r"D:\allen\side-project\musicplane\Star_Fox_64_GM.sf2")  # 載入 SoundFont
fs.program_select(0, sfid, 0, 0)  # channel 0, bank 0, preset 40 (小提琴)

def freq_from_semitone(base, semitone):
    return base * (2 ** (semitone / 12))

base_freq = 440.0  # A4

def play_note_midi(freq, vel=100):
    """把頻率換成最接近的 MIDI note 播放"""
    midi_note = int(round(69 + 12 * (np.log2(freq / 440.0))))
    fs.noteon(0, midi_note, vel)
    # 停留短時間後關掉音符
    fs.noteoff(0, midi_note)

# --- 飛機類別 ---
class Plane:
    def __init__(self, x, y):
        self.image = pygame.image.load('./image/plane.png')
        self.image = pygame.transform.scale(self.image, (100, 100))
        self.rect = self.image.get_rect()
        self.rect.center = (x, y)
        self.speed = 3
        self.current_note = None  # 用於持續播放音符

    def draw(self, camera_offset):
        screen.blit(self.image, (self.rect.x, self.rect.y - camera_offset))

    def move_vertical(self, direction):
        if direction == 'up':
            self.rect.y -= self.speed
        if direction == 'down':
            self.rect.y += self.speed

    def move_to_center(self, center_x):
        if self.rect.centerx < center_x:
            self.rect.x += self.speed

# --- 初始化飛機 ---
player = Plane(100, screen_height // 2)

# --- 遊戲變數 ---
music_line = []
start_time = time.time()
center_x = screen_width // 2
camera_offset = 0

# --- 快速上下移動 4 度消耗能量 ---
semitone_jump = 4
energy_cost = 6.5

# --- 能量條設定 ---
energy = 0.0               # 初始能量
energy_max = 100.0          # 能量最大值
energy_increase_rate = 3.3  # 每秒增加量 (可調整)
energy_bar_height = 20      # 能量條高度

# --- 背景和聲設定 ---
harmony_interval_semitones = [3, 5, 7]  # 3度、完全4度、5度 (半音距)
harmony_duration = 2.0  # 音長 2 秒
harmony_timer = 0.0     # 計時器
last_harmony_time = time.time()
harmony_notes_playing = []

# --- 主遊戲迴圈 ---
while True:
    screen.fill((0, 0, 0))

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            # 停止播放音符
            if player.current_note is not None:
                fs.noteoff(0, player.current_note)
            fs.delete()
            pygame.quit()
            sys.exit()
        
        # --- 處理快速跳躍按鍵 ---
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE and energy >= energy_cost:
                player.rect.y -= semitone_jump * 10
                energy -= energy_cost
            if (event.key == pygame.K_LCTRL or event.key == pygame.K_RCTRL) and energy >= energy_cost:
                player.rect.y += semitone_jump * 10
                energy -= energy_cost

    keys = pygame.key.get_pressed()
    if keys[pygame.K_UP]:
        player.move_vertical('up')
    if keys[pygame.K_DOWN]:
        player.move_vertical('down')

    player.move_to_center(center_x)

    # --- 鏡頭跟隨 ---
    camera_offset = player.rect.centery - screen_height // 2
    """
    top_threshold = camera_offset + screen_height // 5
    bottom_threshold = camera_offset + screen_height * 4 // 5
    if player.rect.centery < top_threshold:
        camera_offset -= player.speed
    elif player.rect.centery > bottom_threshold:
        camera_offset += player.speed
    """

    # --- 記錄軌跡與音符控制 ---
    if time.time() - start_time > 0.1:
        # 記錄軌跡
        music_line.append([player.rect.centerx, player.rect.centery])
        start_time = time.time()

        # 計算音高
        offset = (screen_height//2 - player.rect.centery) // 10  # 每 10px = 1 半音
        freq = freq_from_semitone(base_freq, offset)
        midi_note = int(round(69 + 12 * (np.log2(freq / 440.0))))

        # 若音符不同，先關掉舊音符
        if player.current_note is not None and player.current_note != midi_note:
            fs.noteoff(0, player.current_note)

        # 播放或更新音符
        if player.current_note != midi_note:
            fs.noteon(0, midi_note, 100)
            player.current_note = midi_note

    # --- 軌跡左移 ---
    for point in music_line:
        point[0] -= 5
    music_line = [p for p in music_line if p[0] > 0]

    # --- 畫軌跡 ---
    if len(music_line) > 1:
        adjusted_points = [(p[0], p[1] - camera_offset) for p in music_line]
        pygame.draw.lines(screen, (0, 255, 0), False, adjusted_points, 3)

    # --- 畫飛機 ---
    player.draw(camera_offset)

    # --- 能量條更新 ---
    delta_time = clock.get_time() / 1000.0  # 取得上一幀耗時 (秒)
    energy += energy_increase_rate * delta_time
    if energy > energy_max:
        energy = energy_max

    # 繪製能量條背景
    pygame.draw.rect(screen, (50, 50, 50), (0, 0, screen_width, energy_bar_height))
    # 繪製能量條前景
    bar_width = int((energy / energy_max) * screen_width)
    pygame.draw.rect(screen, (255, 0, 0), (0, 0, bar_width, energy_bar_height))

    current_time = time.time()
    if current_time - last_harmony_time >= 2.0:
        # 關掉上一組和聲
        for note in harmony_notes_playing:
            fs.noteoff(0, note)
        harmony_notes_playing = []

        # 計算新的和聲音符
        offset = (screen_height//2 - player.rect.centery) // 10
        base_freq = freq_from_semitone(440.0, offset)
        harmony_notes_playing = []
        for semitone_offset in harmony_interval_semitones:
            freq = freq_from_semitone(base_freq, semitone_offset)
            midi_note = int(round(69 + 12 * np.log2(freq / 440.0)))
            fs.noteon(0, midi_note, 80)
            harmony_notes_playing.append(midi_note)
        
        last_harmony_time = current_time

    # --- 在主迴圈最後，每幀檢查是否關閉2秒和聲 ---
    if harmony_notes_playing:
        if current_time - last_harmony_time >= harmony_duration:
            for note in harmony_notes_playing:
                fs.noteoff(0, note)
            harmony_notes_playing = []

    pygame.display.update()
    clock.tick(60)