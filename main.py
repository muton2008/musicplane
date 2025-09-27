import pygame
import sys
import time

pygame.init()

screen_height = 600 
screen_width = 1100 
screen = pygame.display.set_mode((screen_width, screen_height))
clock = pygame.time.Clock()

class Plane:
    def __init__(self, x, y):
        self.image = pygame.image.load('./image/plane.png')
        self.image = pygame.transform.scale(self.image, (100, 100))
        self.rect = self.image.get_rect()
        self.rect.center = (x, y)
        self.speed = 3

    def draw(self, camera_offset):
        # 把飛機畫在相對於鏡頭的座標
        screen.blit(self.image, (self.rect.x, self.rect.y - camera_offset))

    def move_vertical(self, direction):
        if direction == 'up':
            self.rect.y -= self.speed
        if direction == 'down':
            self.rect.y += self.speed

    def move_to_center(self, center_x):
        if self.rect.centerx < center_x:
            self.rect.x += self.speed  # 自動往右飛


player = Plane(100, screen_height // 2)

# 音樂線條（存點）
music_line = []
start_time = time.time()

center_x = screen_width // 2  # 飛到螢幕寬度的 1/2 就停下
camera_offset = 0             # 鏡頭初始偏移量

while True:
    screen.fill((0, 0, 0))

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

    keys = pygame.key.get_pressed()
    if keys[pygame.K_UP]:
        player.move_vertical('up')
    if keys[pygame.K_DOWN]:
        player.move_vertical('down')

    # 水平自動移動直到到達中央
    player.move_to_center(center_x)

    # -------- 鏡頭跟隨判斷 --------
    top_threshold = camera_offset + screen_height // 5
    bottom_threshold = camera_offset + screen_height * 4 // 5

    if player.rect.centery < top_threshold:
        camera_offset -= player.speed   # 鏡頭往上
    elif player.rect.centery > bottom_threshold:
        camera_offset += player.speed   # 鏡頭往下

    # 每 0.1 秒記錄一次 (世界座標)
    if time.time() - start_time > 0.1:
        music_line.append([player.rect.centerx, player.rect.centery])
        start_time = time.time()

    # 所有點往左移動 (世界座標)
    for point in music_line:
        point[0] -= 5

    # 移除超出螢幕的點 (轉換後判斷)
    music_line = [p for p in music_line if p[0] > 0]

    # 畫線 (套用鏡頭偏移量)
    if len(music_line) > 1:
        adjusted_points = [(p[0], p[1] - camera_offset) for p in music_line]
        pygame.draw.lines(screen, (0, 255, 0), False, adjusted_points, 3)

    # 畫飛機
    player.draw(camera_offset)

    pygame.display.update()
    clock.tick(60)
