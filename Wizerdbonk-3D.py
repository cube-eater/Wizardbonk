import os
# Force GLX platform for Linux/X11
os.environ['PYOPENGL_PLATFORM'] = 'glx'

from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import sys
import math

# --- GLOBALS & CONFIG ---
window = None
frame = 0
keys = {}
rng_state = 123456

# Game State
enemies = []
projectiles = []
slime_trails = []  
fire_trails = []   
xp_orbs = []       
obstacles = [] 
defeated_count = 0
game_over = False
paused = False
game_won = False # WIN CONDITION

portal_active = False
portal = None 
current_boss = None

# Spell System
AVAILABLE_SPELLS = ["fireball", "fire_step", "bullet_hell", "lifesteal", "rock_armour"]
level_up_pending = False
spell_choices = []
bullet_hell_charges = 0
bullet_hell_cooldown = 0
rock_armour_rocks = []

# --- RANDOMNESS (LCG) ---
def lcg_random():
    global rng_state
    rng_state = (1103515245 * rng_state + 12345) % 2147483648
    return rng_state / 2147483648.0

def lcg_randint(a, b):
    return a + int(lcg_random() * (b - a + 1))

def lcg_uniform(a, b):
    return a + lcg_random() * (b - a)

# --- RENDERING HELPERS ---

def draw_box(x, y, z, sx, sy, sz, color, angle=0):
    glColor3f(*color)
    hx, hy, hz = sx / 2.0, sy / 2.0, sz / 2.0
    base_corners = [(-hx, -hy), ( hx, -hy), ( hx,  hy), (-hx,  hy)]
    rad = math.radians(angle)
    c_ang, s_ang = math.cos(rad), math.sin(rad)
    
    wc = []
    for bx, by in base_corners:
        rx = bx * c_ang - by * s_ang + x
        ry = bx * s_ang + by * c_ang + y
        wc.append((rx, ry))
    
    top_z, bottom_z = z + hz, z - hz
    glBegin(GL_QUADS)
    glNormal3f(0, 0, 1)
    for i in range(4): glVertex3f(wc[i][0], wc[i][1], top_z)
    glNormal3f(0, 0, -1)
    for i in [3, 2, 1, 0]: glVertex3f(wc[i][0], wc[i][1], bottom_z)
    indices = [(0,1), (1,2), (2,3), (3,0)]
    for i1, i2 in indices:
        glVertex3f(wc[i1][0], wc[i1][1], bottom_z)
        glVertex3f(wc[i2][0], wc[i2][1], bottom_z)
        glVertex3f(wc[i2][0], wc[i2][1], top_z)
        glVertex3f(wc[i1][0], wc[i1][1], top_z)
    glEnd()

def draw_cylinder_approx(x, y, z, radius, height, color, segments=12):
    glColor3f(*color)
    glBegin(GL_TRIANGLES)
    for i in range(segments):
        theta1 = 2.0 * math.pi * i / segments
        theta2 = 2.0 * math.pi * (i + 1) / segments
        x1, y1 = radius * math.cos(theta1), radius * math.sin(theta1)
        x2, y2 = radius * math.cos(theta2), radius * math.sin(theta2)
        glNormal3f(0, 0, 1)
        glVertex3f(x, y, z + height)
        glVertex3f(x + x1, y + y1, z + height)
        glVertex3f(x + x2, y + y2, z + height)
        glNormal3f(0, 0, -1)
        glVertex3f(x, y, z)
        glVertex3f(x + x2, y + y2, z)
        glVertex3f(x + x1, y + y1, z)
    glEnd()
    glBegin(GL_QUADS)
    for i in range(segments):
        theta1 = 2.0 * math.pi * i / segments
        theta2 = 2.0 * math.pi * (i + 1) / segments
        x1, y1 = radius * math.cos(theta1), radius * math.sin(theta1)
        x2, y2 = radius * math.cos(theta2), radius * math.sin(theta2)
        glNormal3f(x1, y1, 0)
        glVertex3f(x + x1, y + y1, z)
        glVertex3f(x + x2, y + y2, z)
        glVertex3f(x + x2, y + y2, z + height)
        glVertex3f(x + x1, y + y1, z + height)
    glEnd()

def draw_cone_approx(x, y, z, radius, height, color, segments=8):
    glColor3f(*color)
    # Cone sides
    glBegin(GL_TRIANGLES)
    for i in range(segments):
        theta1 = 2.0 * math.pi * i / segments
        theta2 = 2.0 * math.pi * (i + 1) / segments
        x1, y1 = radius * math.cos(theta1), radius * math.sin(theta1)
        x2, y2 = radius * math.cos(theta2), radius * math.sin(theta2)
        glVertex3f(x, y, z + height)
        glVertex3f(x + x1, y + y1, z)
        glVertex3f(x + x2, y + y2, z)
    glEnd()
    # Cone base
    glBegin(GL_TRIANGLE_FAN)
    glVertex3f(x, y, z)
    for i in range(segments + 1):
        theta = 2.0 * math.pi * i / segments
        glVertex3f(x + radius * math.cos(theta), y + radius * math.sin(theta), z)
    glEnd()

# --- UTILS ---
def check_aabb_collision(box1, box2):
    return (box1[0] <= box2[1] and box1[1] >= box2[0] and
            box1[2] <= box2[3] and box1[3] >= box2[2] and
            box1[4] <= box2[5] and box1[5] >= box2[4])

# --- CAMERA ---
class Camera:
    def __init__(self):
        self.distance = 800
        self.angle_x = 0
        self.angle_y = 45
        self.target = [0, 0, 0]
        self.last_mouse_x = 0
        self.last_mouse_y = 0
        self.mouse_dragging = False
        self.mode = "third" # third, first

    def update(self, request_target):
        self.target = request_target

    def apply(self):
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(60, 1.25, 1, 3000)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        
        rad_x = math.radians(self.angle_x)
        rad_y = math.radians(self.angle_y)
        
        if self.mode == "third":
            cam_x = self.target[0] + self.distance * math.sin(rad_x) * math.cos(rad_y)
            cam_z = self.target[2] + self.distance * math.sin(rad_y)
            cam_y = self.target[1] - self.distance * math.cos(rad_x) * math.cos(rad_y)
            gluLookAt(cam_x, cam_y, cam_z, self.target[0], self.target[1], self.target[2] + 50, 0, 0, 1)
        else:
            eye_x, eye_y, eye_z = self.target[0], self.target[1], self.target[2] + 70
            fwd_x = -math.sin(rad_x) * math.cos(rad_y)
            fwd_y =  math.cos(rad_x) * math.cos(rad_y)
            fwd_z = -math.sin(rad_y)
            gluLookAt(eye_x, eye_y, eye_z, eye_x + fwd_x*100, eye_y + fwd_y*100, eye_z + fwd_z*100, 0, 0, 1)

    def mouse_listener(self, button, state, x, y):
        if button == GLUT_RIGHT_BUTTON or button == GLUT_LEFT_BUTTON:
            if state == GLUT_DOWN:
                self.mouse_dragging = True
                self.last_mouse_x = x
                self.last_mouse_y = y
            else:
                self.mouse_dragging = False

    def mouse_motion(self, x, y):
        if self.mouse_dragging:
            dx = x - self.last_mouse_x
            dy = y - self.last_mouse_y
            self.angle_x += dx * 0.5
            self.angle_y += dy * 0.5
            
            if self.mode == "third":
                self.angle_y = max(10, min(89, self.angle_y))
            else:
                self.angle_y = max(-89, min(89, self.angle_y)) # Allow full vertical range in FP
                
            self.last_mouse_x = x
            self.last_mouse_y = y

# --- WORLD ---
class World:
    def __init__(self):
        self.grid_size = 40
        self.grid_length = 50
        self.zone = "overworld"
    def draw(self):
        start_x = -(self.grid_size * self.grid_length) / 2
        start_y = -(self.grid_size * self.grid_length) / 2
        glBegin(GL_QUADS)
        for i in range(self.grid_size):
            for j in range(self.grid_size):
                if self.zone == "overworld": 
                    col = (0.1, 0.6, 0.1) if (i + j) % 2 == 0 else (0.2, 0.8, 0.2)
                else: 
                    # Nether Design: Black rock + Glowing Lava cracks
                    col = (0.1, 0.1, 0.1) if (i + j) % 2 == 0 else (0.8, 0.2, 0.0)
                glColor3f(*col)
                x, y, z = start_x + i * self.grid_length, start_y + j * self.grid_length, 0
                glVertex3f(x, y, z); glVertex3f(x + self.grid_length, y, z)
                glVertex3f(x + self.grid_length, y + self.grid_length, z); glVertex3f(x, y + self.grid_length, z)
        glEnd()

# --- OBSTACLE ---
class Obstacle:
    def __init__(self, x, y, o_type):
        self.pos = [x, y, 0]
        self.o_type = o_type
        self.size = lcg_randint(30, 60)
        self.height = lcg_randint(40, 100)
        if o_type == "spike": self.height = lcg_randint(80, 150); self.size = 20
        self.color = (0.5, 0.5, 0.5) if lcg_random() > 0.5 else (0.4, 0.4, 0.4)
        if o_type == "spike": self.color = (0.3, 0.0, 0.0) # Dark red spikes

    def draw(self):
        if self.o_type == "cube": draw_box(self.pos[0], self.pos[1], self.height/2, self.size, self.size, self.height, self.color)
        elif self.o_type == "cylinder": draw_cylinder_approx(self.pos[0], self.pos[1], 0, self.size/2, self.height, self.color)
        elif self.o_type == "spike": # Cone shape
             draw_cone_approx(self.pos[0], self.pos[1], 0, self.size, self.height, self.color)

    def get_aabb(self):
        r = self.size / 2
        return (self.pos[0]-r, self.pos[0]+r, self.pos[1]-r, self.pos[1]+r, 0, self.height)

def spawn_obstacles(count):
    obstacles.clear()
    global world
    for _ in range(count):
        while True:
            x = lcg_randint(-900, 900); y = lcg_randint(-900, 900)
            if math.sqrt(x*x + y*y) > 200:
                type_pool = ["cube", "cylinder"]
                if world.zone != "overworld": type_pool.append("spike"); type_pool.append("spike") # More spikes in Nether
                obstacles.append(Obstacle(x, y, type_pool[lcg_randint(0, len(type_pool)-1)]))
                break

# --- PORTAL ---
class Portal:
    def __init__(self, x, y):
        self.pos = [x, y, 0]; self.state = "inactive"; self.size = 60
    def update(self, player):
        global current_boss, world
        dist = math.sqrt((player.pos[0]-self.pos[0])**2 + (player.pos[1]-self.pos[1])**2)
        if self.state == "inactive":
             if dist < 80:
                 self.state = "ignited"
                 if not player.bosses_defeated.get('slime'): spawn_boss("slime")
                 else: spawn_boss("golem")
                 player.boss_active = True
        elif self.state == "ignited":
             if not player.boss_active: self.state = "open"
        elif self.state == "open":
            if dist < 50:
                player.pos = [0, 0, 0]
                self.state = "inactive"
                enemies.clear(); spawn_obstacles(20)
                if world.zone == "overworld": world.zone = "nether"
                return True
        return False
    def draw(self):
        c = (0.2, 0.2, 0.2)
        draw_box(self.pos[0]-35, self.pos[1], 50, 10, 10, 100, c)
        draw_box(self.pos[0]+35, self.pos[1], 50, 10, 10, 100, c)
        draw_box(self.pos[0], self.pos[1], 100, 80, 10, 10, c)
        color = (0.1, 0.1, 0.1)
        if self.state == "ignited": color = (1.0, 0.5, 0.0) 
        elif self.state == "open": color = (0.5, 0.0, 0.8)
        glBegin(GL_QUADS); glColor3f(*color)
        glVertex3f(self.pos[0]-30, self.pos[1], 0); glVertex3f(self.pos[0]+30, self.pos[1], 0)
        glVertex3f(self.pos[0]+30, self.pos[1], 95); glVertex3f(self.pos[0]-30, self.pos[1], 95)
        glEnd()

# --- PROJECTILE ---
class Projectile:
    def __init__(self, x, y, z, dir_x, dir_y, dir_z, p_type="fireball", owner="player"):
        self.pos = [x, y, z]; self.dir = [dir_x, dir_y, dir_z]; self.p_type = p_type; self.owner = owner; self.active = True
        if self.p_type == "fireball": self.speed, self.size, self.damage, self.color = 10, 5, 20, (1.0, 0.5, 0.0)
        elif self.p_type == "bullet" or self.p_type == "bullet_hell": self.speed, self.size, self.damage, self.color = 20, 2, 10, (1.0, 1.0, 0.0)
        elif self.p_type == "slime": self.speed, self.size, self.damage, self.color = 8, 8, 5, (0.0, 1.0, 0.0)
        elif self.p_type == "rock": self.speed, self.size, self.damage, self.color = 15, 12, 15, (0.6, 0.6, 0.6)
        elif self.p_type == "arrow": self.speed, self.size, self.damage, self.color = 25, 3, 5, (0.9, 0.9, 0.9)
        elif self.p_type == "lifesteal": self.speed, self.size, self.damage, self.color = 15, 4, 15, (0.8, 0.0, 0.0)
        elif self.p_type == "fire_step": self.speed, self.size, self.damage, self.color = 10, 4, 15, (1.0, 0.3, 0.0)
        else: self.speed, self.size, self.damage, self.color = 10, 5, 5, (1, 1, 1)

    def update(self):
        self.pos[0] += self.dir[0] * self.speed; self.pos[1] += self.dir[1] * self.speed; self.pos[2] += self.dir[2] * self.speed
        if abs(self.pos[0]) > 2000 or abs(self.pos[1]) > 2000: self.active = False
            
    def draw(self):
        if self.active: draw_box(self.pos[0], self.pos[1], self.pos[2], self.size*2, self.size*2, self.size*2, self.color)
    def get_aabb(self):
        r = self.size
        return (self.pos[0]-r, self.pos[0]+r, self.pos[1]-r, self.pos[1]+r, self.pos[2]-r, self.pos[2]+r)

# --- PLAYER ---
class Player:
    def __init__(self):
        self.pos = [0, 0, 0]; self.vel_knockback = [0, 0]; self.speed = 5; self.radius = 20; self.facing_angle = 0
        self.max_health = 200; self.health = 200; self.xp = 0; self.level = 1
        self.boss_active = False; self.bosses_defeated = {}; self.attack_cooldown = 0; self.attack_speed = 30; self.current_spell = "fireball"
        self.robe_color, self.skin_color, self.hat_color = (0.2, 0.0, 0.5), (1.0, 0.8, 0.6), (0.1, 0.0, 0.3)
        self.orbit_angle = 0; self.rocks = []

    def update_cooldown(self):
        if self.attack_cooldown > 0: self.attack_cooldown -= 1
        if self.current_spell == "rock_armour":
            self.orbit_angle += 2
            if len(self.rocks) == 0 and self.attack_cooldown <= 0: self.rocks = [True, True, True] 

    def shoot(self, target_pos=None):
        if self.attack_cooldown > 0: return None
        self.attack_cooldown = self.attack_speed
        if target_pos:
            dx, dy, dz = target_pos[0] - self.pos[0], target_pos[1] - self.pos[1], target_pos[2] - (self.pos[2] + 40)
            dist = math.sqrt(dx*dx + dy*dy + dz*dz)
            if dist == 0: dist = 1
            dir_vec = (dx/dist, dy/dist, dz/dist)
        else:
            rad = math.radians(self.facing_angle + 90)
            dir_vec = (math.cos(rad), math.sin(rad), 0)
        
        if self.current_spell == "rock_armour":
             if len(self.rocks) > 0:
                 self.rocks.pop()
                 return Projectile(self.pos[0], self.pos[1], self.pos[2] + 40, dir_vec[0], dir_vec[1], dir_vec[2], "rock", "player")
             return None
        return Projectile(self.pos[0], self.pos[1], self.pos[2] + 40, dir_vec[0], dir_vec[1], dir_vec[2], self.current_spell, "player")

    def take_damage(self, amount):
        self.health -= amount
        if self.health < 0: self.health = 0
    def apply_knockback(self, vx, vy): self.vel_knockback = [vx, vy]

    def update(self, keys_ref, cam_angle_x):
        self.pos[0] += self.vel_knockback[0]; self.pos[1] += self.vel_knockback[1]
        self.vel_knockback[0] *= 0.8; self.vel_knockback[1] *= 0.8
        move_x, move_y, moved = 0, 0, False
        if b'w' in keys_ref and keys_ref[b'w']: move_y += 1; moved = True
        if b's' in keys_ref and keys_ref[b's']: move_y -= 1; moved = True
        if b'a' in keys_ref and keys_ref[b'a']: move_x -= 1; moved = True
        if b'd' in keys_ref and keys_ref[b'd']: move_x += 1; moved = True
            
        if moved:
            rad = math.radians(cam_angle_x)
            fwd_x, fwd_y = -math.sin(rad), math.cos(rad)
            rt_x, rt_y = math.cos(rad), math.sin(rad)
            length = math.sqrt(move_x*move_x + move_y*move_y)
            if length > 0: move_x /= length; move_y /= length
            dx = (move_y * fwd_x + move_x * rt_x) * self.speed
            dy = (move_y * fwd_y + move_x * rt_y) * self.speed
            
            new_x, new_y = self.pos[0] + dx, self.pos[1] + dy
            player_aabb = (new_x-self.radius, new_x+self.radius, new_y-self.radius, new_y+self.radius, 0, 60)
            collided = False
            for o in obstacles:
                if check_aabb_collision(player_aabb, o.get_aabb()): collided = True; break
            if not collided: self.pos[0], self.pos[1] = new_x, new_y
            self.facing_angle = math.degrees(math.atan2(dy, dx)) - 90

    def draw(self):
        if camera.mode == "first": 
             if self.current_spell == "rock_armour":
                for i in range(len(self.rocks)):
                    angle = self.orbit_angle + i * (360/3)
                    rx = self.pos[0] + 50 * math.cos(math.radians(angle))
                    ry = self.pos[1] + 50 * math.sin(math.radians(angle))
                    draw_box(rx, ry, self.pos[2] + 30, 10, 10, 10, (0.5, 0.5, 0.5))
             return
        draw_box(self.pos[0], self.pos[1], self.pos[2] + 30, 20, 12, 40, self.robe_color, self.facing_angle)
        draw_box(self.pos[0], self.pos[1], self.pos[2] + 60, 15, 15, 15, self.skin_color, self.facing_angle)
        draw_box(self.pos[0], self.pos[1], self.pos[2] + 68, 25, 25, 4, self.hat_color, self.facing_angle)
        draw_box(self.pos[0], self.pos[1], self.pos[2] + 74, 12, 12, 12, self.hat_color, self.facing_angle)
        rad = math.radians(self.facing_angle)
        cx, cy = math.cos(rad), math.sin(rad)
        ax1, ay1 = self.pos[0] + 12 * cx, self.pos[1] + 12 * cy
        ax2, ay2 = self.pos[0] - 12 * cx, self.pos[1] - 12 * cy
        draw_box(ax1, ay1, self.pos[2] + 40, 8, 8, 20, self.robe_color, self.facing_angle)
        draw_box(ax2, ay2, self.pos[2] + 40, 8, 8, 20, self.robe_color, self.facing_angle)
        if self.current_spell == "rock_armour":
            for i in range(len(self.rocks)):
                angle = self.orbit_angle + i * (360/3)
                rx = self.pos[0] + 50 * math.cos(math.radians(angle))
                ry = self.pos[1] + 50 * math.sin(math.radians(angle))
                draw_box(rx, ry, self.pos[2] + 30, 10, 10, 10, (0.5, 0.5, 0.5))

    def get_aabb(self):
        return (self.pos[0] - self.radius, self.pos[0] + self.radius, self.pos[1] - self.radius, self.pos[1] + self.radius, 0, 60)

# --- ENEMIES ---
class Enemy:
    def __init__(self, x, y, z):
        self.pos = [x, y, z]; self.active = True; self.speed = 0.5; self.health = 30; self.e_type = "base"
        self.facing = 0; self.width, self.height, self.depth = 20, 20, 60; self.color_body = (1, 0, 0)
    def update(self, player_pos):
        if not self.active: return None
        dx, dy = player_pos[0] - self.pos[0], player_pos[1] - self.pos[1]
        dist = math.sqrt(dx*dx + dy*dy)
        if dist > 1: self.facing = math.degrees(math.atan2(dy, dx)) - 90
        if dist > 20: 
            self.pos[0] += (dx/dist) * self.speed; self.pos[1] += (dy/dist) * self.speed
        return None
    def draw(self): pass
    def take_damage(self, dmg):
        self.health -= dmg
        if self.health <= 0: self.active = False
    def get_aabb(self):
        w = self.width / 2
        return (self.pos[0]-w, self.pos[0]+w, self.pos[1]-w, self.pos[1]+w, self.pos[2], self.pos[2]+self.depth)

class Zombie(Enemy):
    def __init__(self, x, y):
        super().__init__(x, y, 0); self.speed = 0.6; self.health = 40; self.e_type = "zombie"
        self.color_skin = (0.2, 0.6, 0.2); self.color_shirt = (0, 0.5, 0.5); self.color_pants = (0.2, 0.2, 0.6)
    def draw(self):
        if not self.active: return
        f = self.facing; rad = math.radians(f); off_x, off_y = 5*math.cos(rad), 5*math.sin(rad)
        draw_box(self.pos[0]-off_x, self.pos[1]-off_y, 15, 8, 8, 30, self.color_pants, f)
        draw_box(self.pos[0]+off_x, self.pos[1]+off_y, 15, 8, 8, 30, self.color_pants, f)
        draw_box(self.pos[0], self.pos[1], 45, 20, 10, 30, self.color_shirt, f)
        draw_box(self.pos[0], self.pos[1], 68, 16, 16, 16, self.color_skin, f)

class Skeleton(Enemy):
    def __init__(self, x, y):
        super().__init__(x, y, 0); self.speed = 0.5; self.health = 30; self.e_type = "skeleton"; self.cooldown = 100; self.color_bone = (0.9, 0.9, 0.9)
    def update(self, player_pos):
        if not self.active: return None
        dx, dy = player_pos[0] - self.pos[0], player_pos[1] - self.pos[1]
        dist = math.sqrt(dx*dx + dy*dy)
        if dist > 1: self.facing = math.degrees(math.atan2(dy, dx)) - 90
        if dist > 200: self.pos[0] += (dx/dist) * self.speed; self.pos[1] += (dy/dist) * self.speed
        if self.cooldown > 0: self.cooldown -= 1
        else:
            if dist < 400:
                self.cooldown = 120; rad = math.radians(self.facing + 90)
                return Projectile(self.pos[0], self.pos[1], 50, math.cos(rad), math.sin(rad), 0, "arrow", "enemy")
        return None
    def draw(self):
        if not self.active: return
        f = self.facing
        draw_box(self.pos[0], self.pos[1], 30, 12, 12, 60, self.color_bone, f)
        draw_box(self.pos[0], self.pos[1], 68, 14, 14, 14, self.color_bone, f)

class Creeper(Enemy):
    def __init__(self, x, y):
        super().__init__(x, y, 0); self.speed = 0.8; self.health = 30; self.e_type = "creeper"; self.color, self.fuse, self.exploding, self.exploded = (0.0, 0.8, 0.0), 0, False, False
    def update(self, player_pos):
        if not self.active: return None
        dx, dy = player_pos[0] - self.pos[0], player_pos[1] - self.pos[1]
        dist = math.sqrt(dx*dx + dy*dy)
        if dist > 1: self.facing = math.degrees(math.atan2(dy, dx)) - 90
        if dist < 40 and not self.exploding: self.exploding = True
        if self.exploding:
            self.fuse += 1
            if self.fuse > 50: self.exploded = True; self.active = False
        else: self.pos[0] += (dx/dist) * self.speed; self.pos[1] += (dy/dist) * self.speed
        return None
    def draw(self):
        if not self.active: return
        c = self.color
        if self.exploding and (self.fuse // 5) % 2 == 0: c = (1, 1, 1)
        f = self.facing
        draw_box(self.pos[0], self.pos[1], 10, 10, 20, 20, c, f)
        draw_box(self.pos[0], self.pos[1], 35, 16, 10, 30, c, f)
        draw_box(self.pos[0], self.pos[1], 58, 16, 16, 16, c, f)

class GiantSlime(Enemy):
    def __init__(self, x, y):
        super().__init__(x, y, 0); self.speed = 0.6; self.health = 250; self.e_type = "boss_slime"; self.size, self.color = 60, (0.0, 0.0, 0.6)
    def draw(self):
        if not self.active: return
        scale = 1.0 + 0.1 * math.sin(frame * 0.1)
        draw_box(self.pos[0], self.pos[1], self.size/2*scale, self.size, self.size, self.size*scale, self.color, self.facing)
class GiantIronGolem(Enemy):
    def __init__(self, x, y):
        super().__init__(x, y, 0); self.speed = 0.5; self.health = 800; self.e_type = "boss_golem"; self.width, self.depth = 50, 90; self.state, self.cooldown, self.dash_timer = "chase", 0, 0
    def update(self, player_pos):
        if not self.active: return None
        dx, dy = player_pos[0] - self.pos[0], player_pos[1] - self.pos[1]
        dist = math.sqrt(dx*dx + dy*dy)
        self.facing = math.degrees(math.atan2(dy, dx)) - 90
        if self.cooldown > 0: self.cooldown -= 1
        if self.state == "dash":
            self.dash_timer += 1; self.speed = 10.0; self.pos[0] += (dx/dist) * self.speed; self.pos[1] += (dy/dist) * self.speed
            if self.dash_timer > 30: self.state = "chase"; self.cooldown = 60; self.speed = 1.0
            return None
        if dist > 400 and self.cooldown == 0:
            self.cooldown = 120; rad = math.radians(self.facing + 90)
            return Projectile(self.pos[0], self.pos[1], 80, math.cos(rad), math.sin(rad), 0, "rock", "enemy")
        elif dist < 200 and self.cooldown == 0: self.state = "dash"; self.dash_timer = 0
        else: self.pos[0] += (dx/dist) * self.speed; self.pos[1] += (dy/dist) * self.speed
        return None
    def draw(self):
        if not self.active: return
        f = self.facing; c = (0.7, 0.7, 0.7)
        draw_box(self.pos[0], self.pos[1], 75, 50, 30, 50, c, f)
        draw_box(self.pos[0], self.pos[1], 110, 20, 20, 20, c, f)

# --- INSTANTIATE ---
camera = Camera()
player = Player()
world = World()
portal = Portal(0, 400)

def spawn_wave(count):
    for i in range(count):
        while True:
            angle = lcg_uniform(0, 6.28); dist = lcg_uniform(600, 1000)
            ex, ey = player.pos[0] + math.cos(angle) * dist, player.pos[1] + math.sin(angle) * dist
            rtype = lcg_random()
            if rtype < 0.5: enemies.append(Zombie(ex, ey))
            elif rtype < 0.8: enemies.append(Skeleton(ex, ey))
            else: enemies.append(Creeper(ex, ey))
            break

def spawn_boss(b_type):
    global current_boss
    angle = lcg_uniform(0, 6.28); dist = 500
    ex, ey = player.pos[0] + math.cos(angle) * dist, player.pos[1] + math.sin(angle) * dist
    if b_type == "slime": current_boss = GiantSlime(ex, ey)
    elif b_type == "golem": current_boss = GiantIronGolem(ex, ey)
    enemies.append(current_boss)

# --- PARTICLES ---
class Particle:
    def __init__(self, x, y, z, color):
        self.pos = [x, y, z]
        self.vel = [lcg_uniform(-2, 2), lcg_uniform(-2, 2), lcg_uniform(2, 5)]
        self.color = color
        self.life = lcg_randint(20, 40)
        self.size = lcg_uniform(1, 3)

    def update(self):
        self.pos[0] += self.vel[0]
        self.pos[1] += self.vel[1]
        self.pos[2] += self.vel[2]
        self.vel[2] -= 0.2 # Gravity
        self.life -= 1

    def draw(self):
        draw_box(self.pos[0], self.pos[1], self.pos[2], self.size, self.size, self.size, self.color)

particles = []

def spawn_particles(x, y, z, count, color):
    for _ in range(count):
        particles.append(Particle(x, y, z, color))

def load_high_score():
    try:
        with open("highscore.txt", "r") as f:
            return int(f.read().strip())
    except:
        return 0

def save_high_score(score):
    try:
        with open("highscore.txt", "w") as f:
            f.write(str(score))
    except:
        pass

high_score = load_high_score()
difficulty_multiplier = 1.0

def restart_game():
    global enemies, projectiles, slime_trails, fire_trails, xp_orbs, particles
    global game_over, defeated_count, level_up_pending, bullet_hell_charges, bullet_hell_cooldown
    global portal, current_boss, game_won
    
    player.health, player.pos, player.level, player.xp = player.max_health, [0,0,0], 1, 0
    player.current_spell, player.boss_active, player.bosses_defeated = "fireball", False, {}
    enemies, projectiles, slime_trails, fire_trails, xp_orbs, particles = [], [], [], [], [], []
    game_over, defeated_count, level_up_pending, game_won = False, 0, False, False
    bullet_hell_charges, bullet_hell_cooldown, world.zone = 0, 0, "overworld"
    portal = Portal(0, 400)
    current_boss = None
    spawn_obstacles(20)

def draw_hud():
    glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity(); gluOrtho2D(0, 800, 0, 600); glMatrixMode(GL_MODELVIEW); glPushMatrix(); glLoadIdentity()
    glColor3f(1, 1, 1)
    if game_won:
        glRasterPos3f(300, 300, 0)
        for c in "VICTORY! YOU HAVE WON THE GAME!": glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(c))
        glRasterPos3f(280, 270, 0)
        for c in "Press R to Restart | Press C to Continue (Hard Mode)": glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(c))
    elif paused:
        glRasterPos3f(350, 300, 0)
        for c in "PAUSED": glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(c))
    elif game_over:
        glRasterPos3f(350, 300, 0)
        for c in "GAME OVER - Press R": glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(c))
    elif level_up_pending:
        glRasterPos3f(300, 400, 0)
        for c in "LEVEL UP! Choose 1, 2, or 3": glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(c))
        for i, s in enumerate(spell_choices):
            glRasterPos3f(300, 350 - i*30, 0)
            txt = f"{i+1}: {s}"
            for c in txt: glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(c))
    else:
        glRasterPos3f(10, 570, 0)
        for c in f"HP: {int(player.health)} | LVL: {player.level} | XP: {player.xp}/{player.level*100}": glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(c))
        glRasterPos3f(10, 550, 0)
        for c in f"Spell: {player.current_spell} | Kills: {defeated_count} | HI: {high_score}": glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(c))
        if player.boss_active and current_boss:
             glRasterPos3f(350, 550, 0)
             for c in f"BOSS: {int(current_boss.health)}": glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(c))
    glPopMatrix(); glMatrixMode(GL_PROJECTION); glPopMatrix(); glMatrixMode(GL_MODELVIEW)

def init():
    glClearColor(0.5, 0.7, 1.0, 1.0)
    glEnable(GL_DEPTH_TEST)

def display():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    camera.apply(); world.draw()
    if portal: portal.draw()
    for o in obstacles: o.draw()
    for t in slime_trails: draw_box(t['pos'][0], t['pos'][1], 1, 20, 20, 2, (0.0, 0.0, 0.8)) # Blue Trail
    for ft in fire_trails: draw_box(ft['pos'][0], ft['pos'][1], 2, 16, 16, 6, (1, 0.5, 0))
    for e in enemies: e.draw()
    for p in projectiles: p.draw()
    for part in particles: part.draw()
    for o in xp_orbs: draw_box(o['pos'][0], o['pos'][1], o['pos'][2], 10, 10, 10, (0, 1, 1), o['angle'])
    player.draw(); draw_hud(); glutSwapBuffers()

def idle():
    global frame, game_over, level_up_pending, bullet_hell_charges, bullet_hell_cooldown
    global enemies, projectiles, slime_trails, fire_trails, xp_orbs, defeated_count, spell_choices
    global paused, portal, current_boss, game_won, particles, high_score, difficulty_multiplier
    
    if paused: return
    frame += 1
    if game_won:
        if b'r' in keys and keys[b'r']: restart_game()
        if b'c' in keys and keys[b'c']:
             game_won = False
             difficulty_multiplier += 0.5
             portal = Portal(0, 400); player.pos = [0,0,0]; enemies.clear(); spawn_obstacles(20)
             if world.zone != "overworld": world.zone = "overworld" # Loop back
             player.bosses_defeated = {}; player.boss_active = False; current_boss = None
        glutPostRedisplay(); return
    if game_over:
        if defeated_count > high_score: 
            high_score = defeated_count
            save_high_score(high_score)
        if b'r' in keys and keys[b'r']: restart_game()
        glutPostRedisplay(); return
    if level_up_pending: glutPostRedisplay(); return

    player.update(keys, camera.angle_x); player.update_cooldown(); camera.update(player.pos)
    if portal:
        if portal.update(player): pass
    if player.current_spell == "fire_step":
        if frame % 10 == 0: fire_trails.append({'pos': list(player.pos), 'timer': 200, 'damage': 5})
    if bullet_hell_cooldown > 0: bullet_hell_cooldown -= 1
    
    nearest, min_d = None, 9999
    for e in enemies:
        d = math.sqrt((e.pos[0]-player.pos[0])**2 + (e.pos[1]-player.pos[1])**2)
        if d < min_d: min_d = d; nearest = e
    
    target_pos = nearest.pos if nearest and min_d < 600 else None
    if target_pos:
        if player.current_spell == "bullet_hell":
             if bullet_hell_cooldown <= 0 and player.attack_cooldown <= 0: bullet_hell_charges = 3; bullet_hell_cooldown = 90
        elif player.current_spell == "rock_armour": pass
        else:
             p = player.shoot(target_pos)
             if p: projectiles.append(p)

    if bullet_hell_charges > 0 and player.attack_cooldown <= 0:
        p = player.shoot(target_pos)
        if p: p.p_type = "bullet"; p.speed = 20; projectiles.append(p)
        bullet_hell_charges -= 1; player.attack_cooldown = 5

    for e in enemies:
        res = e.update(player.pos)
        if res: projectiles.append(res)
        if e.e_type == "boss_slime" and frame % 20 == 0: slime_trails.append({'pos': list(e.pos), 'timer': 300})
        
        if check_aabb_collision(e.get_aabb(), player.get_aabb()):
             if e.e_type == "creeper":
                 if e.exploded:
                     player.take_damage(30 * difficulty_multiplier)
                     dx, dy = player.pos[0] - e.pos[0], player.pos[1] - e.pos[1]
                     mag = math.sqrt(dx*dx + dy*dy)
                     if mag > 0: player.apply_knockback(dx/mag * 15, dy/mag * 15)
                     spawn_particles(e.pos[0], e.pos[1], e.pos[2], 20, (1, 0.5, 0))
             elif e.e_type == "boss_golem" and e.state == "dash":
                 player.take_damage(20 * difficulty_multiplier) 
                 dx, dy = player.pos[0] - e.pos[0], player.pos[1] - e.pos[1]
                 mag = math.sqrt(dx*dx + dy*dy)
                 if mag > 0: player.apply_knockback(dx/mag * 20, dy/mag * 20)
             else: player.take_damage(0.5 * difficulty_multiplier)

    if player.current_spell == "rock_armour":
        for i in range(len(player.rocks) -1, -1, -1):
            angle = player.orbit_angle + i * (360/3)
            rx = player.pos[0] + 50 * math.cos(math.radians(angle))
            ry = player.pos[1] + 50 * math.sin(math.radians(angle))
            r_box = (rx-10, rx+10, ry-10, ry+10, player.pos[2]+20, player.pos[2]+40)
            for e in enemies:
                if check_aabb_collision(r_box, e.get_aabb()): e.take_damage(25); player.rocks.pop(i); spawn_particles(e.pos[0], e.pos[1], e.pos[2], 5, (0.5, 0.5, 0.5)); break

    for p in projectiles:
        p.update()
        if p.owner == "player":
            p_box = p.get_aabb()
            for e in enemies:
                if check_aabb_collision(p_box, e.get_aabb()):
                    e.take_damage(p.damage); p.active = False
                    spawn_particles(p.pos[0], p.pos[1], p.pos[2], 5, p.color)
                    if player.current_spell == "lifesteal": player.health += 1
                    if not e.active:
                        defeated_count += 1
                        xp_orbs.append({'pos': list(e.pos), 'value': 20, 'angle': 0})
                        spawn_particles(e.pos[0], e.pos[1], e.pos[2], 15, (0, 1, 0) if "slime" in e.e_type else (1,0,0))
                        if "boss" in e.e_type:
                            player.boss_active = False
                            player.bosses_defeated[e.e_type.replace('boss_', '')] = True
                            spawn_particles(e.pos[0], e.pos[1], e.pos[2], 50, (1, 0, 1))
                            if e.e_type == "boss_slime": world.zone = "nether"
                            # WIN CONDITION CHECK
                            if player.bosses_defeated.get('slime') and player.bosses_defeated.get('golem'):
                                game_won = True
                    break
            for o in obstacles:
                 if check_aabb_collision(p.get_aabb(), o.get_aabb()): p.active = False; spawn_particles(p.pos[0], p.pos[1], p.pos[2], 3, (0.5, 0.5, 0.5))
        elif p.owner == "enemy":
             if check_aabb_collision(p.get_aabb(), player.get_aabb()): 
                 player.take_damage(p.damage * difficulty_multiplier); p.active = False
                 spawn_particles(player.pos[0], player.pos[1], player.pos[2], 5, (1, 0, 0))
             for o in obstacles:
                 if check_aabb_collision(p.get_aabb(), o.get_aabb()): p.active = False
    
    enemies = [e for e in enemies if e.active]
    projectiles = [p for p in projectiles if p.active]
    for part in particles: 
        part.update()
    particles = [p for p in particles if p.life > 0]
    
    player.speed = 5
    for t in slime_trails:
        t['timer'] -= 1
        dx, dy = player.pos[0] - t['pos'][0], player.pos[1] - t['pos'][1]
        if math.sqrt(dx*dx + dy*dy) < 20: player.speed = 2
    slime_trails = [t for t in slime_trails if t['timer'] > 0]
    
    for t in fire_trails:
        t['timer'] -= 1
        for e in enemies:
             dx, dy = e.pos[0] - t['pos'][0], e.pos[1] - t['pos'][1]
             if math.sqrt(dx*dx + dy*dy) < 20: e.take_damage(0.5)
    fire_trails = [t for t in fire_trails if t['timer'] > 0]
    
    for o in xp_orbs:
        o['angle'] += 5
        dx, dy = player.pos[0] - o['pos'][0], player.pos[1] - o['pos'][1]
        d = math.sqrt(dx*dx + dy*dy)
        if d < 80: o['pos'][0] += dx * 0.1; o['pos'][1] += dy * 0.1
        if d < 40: 
            player.xp += o['value']; o['value'] = 0 
            spawn_particles(player.pos[0], player.pos[1], player.pos[2], 8, (0, 1, 1))

    xp_orbs = [o for o in xp_orbs if o['value'] > 0]

    if player.xp >= player.level * 100:
        player.xp = 0; player.level += 1; player.health = player.max_health; level_up_pending = True; spell_choices = []
        pool = list(AVAILABLE_SPELLS)
        for _ in range(3):
            if not pool: break
            idx = lcg_randint(0, len(pool)-1); spell_choices.append(pool.pop(idx))

    if not player.boss_active and len(enemies) == 0 and (not portal or portal.state != "open"): 
        count = 5 + player.level
        if world.zone != "overworld": count *= 2 # Double enemies in Nether
        spawn_wave(count)
    if player.health <= 0: game_over = True
    glutPostRedisplay()

def keyboard_down(key, x, y):
    global level_up_pending, spell_choices, paused
    if key == b'p': paused = not paused
    if key == b'c' and game_won: pass # handled in idle
    if key == b'v': 
        if camera.mode == "third": 
            camera.mode = "first"
            camera.angle_y = 0  # Look straight forward
        else: 
            camera.mode = "third"
            camera.angle_y = 45 # Reset to default overhead view
    keys[key] = True
    if level_up_pending:
        idx = -1
        if key == b'1': idx = 0
        elif key == b'2': idx = 1
        elif key == b'3': idx = 2
        if idx != -1 and idx < len(spell_choices):
            player.current_spell = spell_choices[idx]
            level_up_pending = False

def keyboard_up(key, x, y): keys[key] = False
def mouse(button, state, x, y): camera.mouse_listener(button, state, x, y)
def motion(x, y): camera.mouse_motion(x, y)

def main():
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH) 
    glutInitWindowSize(800, 600)
    glutCreateWindow(b"Wizard Bonk 3D")
    init()
    spawn_obstacles(20)
    glutDisplayFunc(display); glutIdleFunc(idle)
    glutKeyboardFunc(keyboard_down); glutKeyboardUpFunc(keyboard_up)
    glutMouseFunc(mouse); glutMotionFunc(motion)
    glutMainLoop()

if __name__ == "__main__":
    main()