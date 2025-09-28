import pygame
import sys
import time
import os
os.add_dll_directory(r"D:\allen\side-project\musicplane\fluidsynth-2.4.8-win10-x64\bin")  # Windows 下需要指定 DLL 路徑
import fluidsynth
import numpy as np
import random

# --- 初始化 Pygame ---
pygame.init()
screen_height = 600
screen_width = 1100
screen = pygame.display.set_mode((screen_width, screen_height))
clock = pygame.time.Clock()

# --- 初始化字體 ---
pygame.font.init()
font = pygame.font.SysFont('Consolas', 20)

# --- 初始化 FluidSynth ---
fs = fluidsynth.Synth()
fs.start(driver="dsound")
sfid = fs.sfload(r"D:\allen\side-project\musicplane\Star_Fox_64_GM.sf2")
fs.program_select(0, sfid, 0, 0)  # channel 0, bank 0, preset 40 (小提琴)

# --- 音樂相關函數 ---
def freq_from_semitone(base, semitone):
    return base * (2 ** (semitone / 12))

base_freq = 440.0  # A4

# --- 飛機類別 ---
class Plane:
    def __init__(self, x, y):
        self.image = pygame.image.load('./image/plane.png')
        self.image = pygame.transform.scale(self.image, (100, 100))
        self.rect = self.image.get_rect()
        self.rect.center = (x, y)
        self.speed = 3
        self.current_note = None

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

# --- 快速上下移動設定 ---
semitone_jump = 4
energy_cost = 6

# --- 能量條設定 ---
energy = 0.0
energy_max = 100.0
energy_increase_rate = 3.7
energy_bar_height = 20

# --- 背景和聲設定 ---
C_major = [0, 2, 4, 5, 7, 9, 11]          # C 大調音階
harmony_duration = 2.0
last_harmony_time = time.time()
harmony_notes_playing = []

freq = 442 

# --- 主遊戲迴圈 ---
while True:
    screen.fill((0, 0, 0))

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            if player.current_note is not None:
                fs.noteoff(0, player.current_note)
            for note in harmony_notes_playing:
                fs.noteoff(0, note)
            fs.delete()
            pygame.quit()
            sys.exit()

        # 快速跳躍
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE and energy >= energy_cost:
                player.rect.y -= semitone_jump * 10
                energy -= energy_cost
            if (event.key == pygame.K_LCTRL or event.key == pygame.K_RCTRL) and energy >= energy_cost:
                player.rect.y += semitone_jump * 10
                energy -= energy_cost

    # 持續移動
    keys = pygame.key.get_pressed()
    if keys[pygame.K_UP]:
        player.move_vertical('up')
    if keys[pygame.K_DOWN]:
        player.move_vertical('down')

    player.move_to_center(center_x)
    camera_offset = player.rect.centery - screen_height // 2

    # --- 記錄軌跡與主旋律 ---
    if time.time() - start_time > 0.1:
        music_line.append([player.rect.centerx, player.rect.centery])
        start_time = time.time()

        # 計算主旋律 (C 大調)
        scale_degree = int((screen_height//2 - player.rect.centery) / 10)
        offset_in_scale = C_major[scale_degree % len(C_major)] + (scale_degree // len(C_major)) * 12
        freq = freq_from_semitone(base_freq, offset_in_scale)
        midi_note = int(round(69 + 12 * np.log2(freq / 440.0)))

        # 播放主旋律
        if player.current_note is not None and player.current_note != midi_note:
            fs.noteoff(0, player.current_note)
        if player.current_note != midi_note:
            fs.noteon(0, midi_note, 100)
            player.current_note = midi_note

    # 軌跡左移
    for point in music_line:
        point[0] -= 5
    music_line = [p for p in music_line if p[0] > 0]

    # 畫軌跡
    if len(music_line) > 1:
        adjusted_points = [(p[0], p[1] - camera_offset) for p in music_line]
        pygame.draw.lines(screen, (0, 255, 0), False, adjusted_points, 3)

    # 畫飛機
    player.draw(camera_offset)

    # --- 能量條 ---
    delta_time = clock.get_time() / 1000.0
    energy += energy_increase_rate * delta_time
    if energy > energy_max:
        energy = energy_max
    pygame.draw.rect(screen, (50, 50, 50), (0, 0, screen_width, energy_bar_height))
    bar_width = int((energy / energy_max) * screen_width)
    pygame.draw.rect(screen, (255, 0, 0), (0, 0, bar_width, energy_bar_height))

    midi_note = int(round(69 + 12 * np.log2(freq / 440.0)))
    current_freq = freq

    text_surface = font.render(f"MIDI: {midi_note} | Freq: {current_freq:.1f} Hz", True, (255, 255, 255))
    screen.blit(text_surface, (10, energy_bar_height + 5))  # 放在能量條下方 5px

    # --- 和聲播放 ---
    current_time = time.time()
    if current_time - last_harmony_time >= 2.0:
        # 關掉上一個和聲
        for note in harmony_notes_playing:
            fs.noteoff(0, note)
        harmony_notes_playing = []

        # 計算和聲音符
        scale_degree = int((screen_height//2 - player.rect.centery) / 10)
        offset_in_scale = C_major[scale_degree % len(C_major)] + (scale_degree // len(C_major)) * 12

        # 上行或下行大三度/五度
        if player.rect.centery < screen_height//2:
            harmony_offset = random.choice([4, 7])
        else:
            harmony_offset = random.choice([-4, -7])

        freq_h = freq_from_semitone(base_freq, offset_in_scale + harmony_offset)
        midi_note_h = int(round(69 + 12 * np.log2(freq_h / 440.0)))
        fs.noteon(0, midi_note_h, 80)
        harmony_notes_playing.append(midi_note_h)

        last_harmony_time = current_time

    # 停止播放超過 2 秒的和聲
    if harmony_notes_playing:
        if current_time - last_harmony_time >= harmony_duration:
            for note in harmony_notes_playing:
                fs.noteoff(0, note)
            harmony_notes_playing = []

    pygame.display.update()
    clock.tick(60)