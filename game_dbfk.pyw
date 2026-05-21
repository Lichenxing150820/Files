import pygame
import random
import time
import tkinter as tk
import sys

running = True

root = tk.Tk()
root.geometry("200x160")  # 修复：添加引号
root.title("控制台")

def a():
    global screen_width, screen_height, screen
    screen_width = 1920
    screen_height = 1080
    screen = pygame.display.set_mode((screen_width, screen_height))

def b():
    global screen_width, screen_height, screen
    screen_width = 900
    screen_height = 600
    screen = pygame.display.set_mode((screen_width, screen_height))

def c():
    pygame.quit()
    root.quit()
    sys.exit(0)
    running = False
def d():
    global screen_width, screen_height, screen
    screen_width = 1530
    screen_height = 800
    screen = pygame.display.set_mode((screen_width, screen_height))

button1 = tk.Button(root, text="big", command=a)
button1.pack(padx=5, pady=5)

button4 = tk.Button(root, text="middle", command=d)
button4.pack(padx=5, pady=5)

button2 = tk.Button(root, text="small", command=b)
button2.pack(padx=5, pady=5)

button3 = tk.Button(root, text="exit", command=c)
button3.pack(padx=5, pady=5)

# 初始化pygame
pygame.init()

# 设置屏幕尺寸
screen_width = 1530
screen_height = 800
screen = pygame.display.set_mode((screen_width, screen_height))

# 设置颜色
white = (255, 255, 255)
black = (0, 0, 0)
red = (255, 0, 0)

# 设置标题
pygame.display.set_caption("躲避方块游戏")

# 设置时钟
clock = pygame.time.Clock()
fps = 60

# 玩家类
class Player(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.image = pygame.Surface((20, 20))
        self.image.fill(red)
        self.rect = self.image.get_rect()
        self.rect.center = (screen_width // 2, screen_height // 2)
        self.speed = 5

    def update(self):
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:
            self.rect.x -= self.speed
        if keys[pygame.K_RIGHT]:
            self.rect.x += self.speed
        if keys[pygame.K_UP]:
            self.rect.y -= self.speed
        if keys[pygame.K_DOWN]:
            self.rect.y += self.speed
        if keys[pygame.K_ESCAPE]:
            pygame.quit()
            root.quit()
            sys.exit(0)
            running = False

# 敌人类
class Enemy(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.image = pygame.Surface((20, 20))
        self.image.fill(black)
        self.rect = self.image.get_rect()
        self.rect.x = random.randint(0, screen_width - self.rect.width)
        self.rect.y = random.randint(-50, -10)
        self.speed = random.randint(1, 3)

    def update(self):
        self.rect.y += self.speed
        if self.rect.top > screen_height:
            self.rect.x = random.randint(0, screen_width - self.rect.width)
            self.rect.y = random.randint(-50, -10)
            self.speed = random.randint(1, 3)

# 创建玩家和敌人组
player = Player()
player_group = pygame.sprite.Group()
player_group.add(player)

enemy_group = pygame.sprite.Group()
for i in range(10):
    enemy = Enemy()
    enemy_group.add(enemy)

# 游戏主循环控制标志

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            root.quit()
            running = False
            sys.exit(0)
    # 更新
    player_group.update()
    enemy_group.update()
    
    # 检查碰撞
    if pygame.sprite.spritecollide(player, enemy_group, True):
        print("游戏结束！")
        pygame.display.set_caption("躲避方块游戏_游戏结束！")
        time.sleep(1)
        pygame.display.set_caption("躲避方块游戏")

        # 重置游戏状态
        player.rect.center = (screen_width // 2, screen_height // 2)  # 重置玩家位置
        enemy_group.empty()  # 清空敌人组
        for i in range(10):
            enemy = Enemy()
            enemy_group.add(enemy)  # 重新生成敌人

    # 绘制
    screen.fill(white)
    player_group.draw(screen)
    enemy_group.draw(screen)
    
    # 刷新屏幕
    pygame.display.flip()
    root.update()  # 更新tkinter窗口
    # 控制帧率
    clock.tick(fps)

# 退出pygame
pygame.quit()
