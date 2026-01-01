import os
# Force GLX platform for Linux/X11
os.environ['PYOPENGL_PLATFORM'] = 'glx'

from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import sys
import math
import random

# --- HELPER FUNCTIONS ---

def draw_cube(x, y, z, sx, sy, sz, color):
    glColor3f(*color)
    glPushMatrix()
    glTranslatef(x, y, z)
    glScalef(sx, sy, sz)
    glutSolidCube(1) 
    glPopMatrix()

# --- CAMERA CLASS ---

class Camera:
    def __init__(self):
        self.distance = 500
        self.angle_x = 0  # Rotation around vertical axis
        self.angle_y = 30 # Up/Down angle
        self.target = [0, 0, 0]
        
        self.last_mouse_x = 0
        self.last_mouse_y = 0
        self.mouse_dragging = False

    def update(self, player_pos):
        self.target = player_pos

    def setup_camera(self):
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(60, 1.25, 1, 2000) # Fov, Aspect, Near, Far
        
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        
        # Calculate camera position based on orbit
        rad_x = math.radians(self.angle_x)
        rad_y = math.radians(self.angle_y)
        
        cam_x = self.target[0] + self.distance * math.sin(rad_x) * math.cos(rad_y)
        cam_z = self.target[2] + self.distance * math.sin(rad_y)
        cam_y = self.target[1] - self.distance * math.cos(rad_x) * math.cos(rad_y)
        
        # Look at target
        gluLookAt(cam_x, cam_y, cam_z,
                  self.target[0], self.target[1], self.target[2] + 50, # Aim lightly above player feet
                  0, 0, 1)

    def mouse_listener(self, button, state, x, y):
        if button == GLUT_RIGHT_BUTTON: # Right click to rotate camera
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
            
            # Clamp vertical angle
            self.angle_y = max(10, min(89, self.angle_y))
            
            self.last_mouse_x = x
            self.last_mouse_y = y

# --- WORLD CLASS ---

class World:
    def __init__(self):
        self.grid_size = 20
        self.grid_length = 50 # Size of each tile
        self.zone = "overworld" # or "nether"

    def draw(self):
        self.draw_floor()

    def draw_floor(self):
        # Center the grid
        start_x = -(self.grid_size * self.grid_length) / 2
        start_y = -(self.grid_size * self.grid_length) / 2
        
        glBegin(GL_QUADS)
        for i in range(self.grid_size):
            for j in range(self.grid_size):
                if self.zone == "overworld":
                    if (i + j) % 2 == 0:
                        glColor3f(0.1, 0.6, 0.1) # Dark green
                    else:
                        glColor3f(0.2, 0.8, 0.2) # Light green
                elif self.zone == "nether":
                    if (i + j) % 2 == 0:
                        glColor3f(0.4, 0.0, 0.0) # Dark red
                    else:
                        glColor3f(0.8, 0.2, 0.0) # Lava/Red
                
                x = start_x + i * self.grid_length
                y = start_y + j * self.grid_length
                
                glVertex3f(x, y, 0)
                glVertex3f(x + self.grid_length, y, 0)
                glVertex3f(x + self.grid_length, y + self.grid_length, 0)
                glVertex3f(x, y + self.grid_length, 0)
        glEnd()

# --- PROJECTILE CLASS ---

class Projectile:
    def __init__(self, x, y, z, dir_x, dir_y, dir_z, p_type="fireball", owner="player"):
        self.pos = [x, y, z]
        self.dir = [dir_x, dir_y, dir_z]
        self.p_type = p_type # "fireball", "bullet", "rock", "slime"
        self.owner = owner # "player" or "enemy"
        self.active = True
        
        # Stats
        if self.p_type == "fireball":
            self.speed = 10
            self.size = 5
            self.color = (1.0, 0.5, 0.0) # Orange
            self.damage = 1
        elif self.p_type == "bullet":
            self.speed = 20
            self.size = 2
            self.color = (1.0, 1.0, 0.0) # Yellow
            self.damage = 1
        elif self.p_type == "slime":
            self.speed = 8
            self.size = 8
            self.color = (0.0, 1.0, 0.0) # Green
            self.damage = 2
        elif self.p_type == "rock":
            self.speed = 15
            self.size = 12
            self.color = (0.6, 0.6, 0.6) # Gray
            self.damage = 15
        elif self.p_type == "arrow":
            self.speed = 25
            self.size = 3
            self.color = (0.9, 0.9, 0.9) # White/Bone
            self.damage = 5
        else:
            self.speed = 10
            self.size = 5
            self.color = (1, 1, 1)
            self.damage = 1

    def update(self):
        self.pos[0] += self.dir[0] * self.speed
        self.pos[1] += self.dir[1] * self.speed
        self.pos[2] += self.dir[2] * self.speed
        
        # Deactivate if too far
        if abs(self.pos[0]) > 2000 or abs(self.pos[1]) > 2000:
            self.active = False

    def draw(self):
        if not self.active: return
        
        glPushMatrix()
        glTranslatef(self.pos[0], self.pos[1], self.pos[2])
        glColor3f(*self.color)
        # Replacing glutSolidSphere with gluSphere for compliance
        gluSphere(get_quadric(), self.size, 10, 10)
        glPopMatrix()

    def get_aabb(self):
        r = self.size
        return (self.pos[0]-r, self.pos[0]+r, 
                self.pos[1]-r, self.pos[1]+r,
                self.pos[2]-r, self.pos[2]+r)

# --- PLAYER CLASS ---

class Player:
    def __init__(self):
        self.pos = [0, 0, 0] # x, y, z
        self.speed = 5
        self.radius = 20 # Collision radius/size
        self.facing_angle = 0 # Rotation
        
        # Stats
        self.max_health = 100
        self.health = 100
        self.xp = 0
        self.level = 1
        
        # Boss Tracking
        self.boss_active = False
        self.bosses_defeated = {} # {level: bool}
        
        # Combat
        self.attack_cooldown = 0
        self.attack_speed = 30 # Frames
        self.current_spell = "fireball" # fireball, fire_step, bullet_hell, etc.
        
        # Design colors (Wizard)
        self.robe_color = (0.2, 0.0, 0.5) # Purple
        self.skin_color = (1.0, 0.8, 0.6)
        self.hat_color = (0.1, 0.0, 0.3)

    def tick_cooldown(self):
        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1

    def shoot(self, target_pos=None):
        if self.attack_cooldown > 0:
            return None
        
        self.attack_cooldown = self.attack_speed
        
        # Calculate direction
        if target_pos:
            dx = target_pos[0] - self.pos[0]
            dy = target_pos[1] - self.pos[1]
            dz = target_pos[2] - (self.pos[2] + 40) # Aim from chest
            dist = math.sqrt(dx*dx + dy*dy + dz*dz)
            if dist == 0: dist = 1
            dir_vec = (dx/dist, dy/dist, dz/dist)
        else:
            rad = math.radians(self.facing_angle + 90)
            dir_vec = (math.cos(rad), math.sin(rad), 0)
        
        return Projectile(self.pos[0], self.pos[1], self.pos[2] + 40,
                          dir_vec[0], dir_vec[1], dir_vec[2],
                          self.current_spell, "player")

    def take_damage(self, amount):
        self.health -= amount
        print(f"Player Hit! Health: {self.health}")
        if self.health < 0: self.health = 0

    def gain_xp(self, amount):
        self.xp += amount
        if self.xp >= self.level * 100:
            self.xp = 0
            self.level += 1
            self.health = self.max_health
            print(f"Level Up! Level {self.level}")

    def update(self, keys, camera_angle_x):
        move_x = 0
        move_y = 0
        moved = False
        
        if b'w' in keys and keys[b'w']:
            move_y += 1
            moved = True
        if b's' in keys and keys[b's']:
            move_y -= 1
            moved = True
        if b'a' in keys and keys[b'a']:
            move_x -= 1
            moved = True
        if b'd' in keys and keys[b'd']:
            move_x += 1
            moved = True
            
        if moved:
            rad = math.radians(camera_angle_x)
            forward_x = -math.sin(rad)
            forward_y = math.cos(rad)
            right_x = math.cos(rad)
            right_y = math.sin(rad)
            
            # Normalize input
            length = math.sqrt(move_x*move_x + move_y*move_y)
            if length > 0:
                move_x /= length
                move_y /= length
            
            dx = (move_y * forward_x + move_x * right_x) * self.speed
            dy = (move_y * forward_y + move_x * right_y) * self.speed
            
            self.pos[0] += dx
            self.pos[1] += dy
            self.facing_angle = math.degrees(math.atan2(dy, dx)) - 90

    def draw(self):
        glPushMatrix()
        glTranslatef(self.pos[0], self.pos[1], self.pos[2])
        glRotatef(self.facing_angle, 0, 0, 1)
        
        # 1. Body (Robe)
        glColor3f(*self.robe_color)
        glPushMatrix()
        glTranslatef(0, 0, 30)
        glScalef(1, 0.6, 2)
        glutSolidCube(20)
        glPopMatrix()
        
        # 2. Head
        glColor3f(*self.skin_color)
        glPushMatrix()
        glTranslatef(0, 0, 60)
        glutSolidCube(15)
        glPopMatrix()
        
        # 3. Hat
        glColor3f(*self.hat_color)
        glPushMatrix()
        glTranslatef(0, 0, 68)
        gluCylinder(get_quadric(), 12, 0, 25, 10, 2) 
        glPopMatrix()
        
        # 4. Arms
        glColor3f(*self.robe_color)
        glPushMatrix()
        glTranslatef(-12, 0, 40)
        glRotatef(-20, 0, 1, 0)
        glScalef(0.5, 0.5, 1.5)
        glutSolidCube(15)
        glPopMatrix()
        glPushMatrix()
        glTranslatef(12, 0, 40)
        glRotatef(20, 0, 1, 0)
        glScalef(0.5, 0.5, 1.5)
        glutSolidCube(15)
        glPopMatrix()
        
        glPopMatrix()

    def get_aabb(self):
        return (self.pos[0] - self.radius, self.pos[0] + self.radius,
                self.pos[1] - self.radius, self.pos[1] + self.radius,
                0, 60)

# --- ENEMY CLASSES ---

class Enemy:
    def __init__(self, x, y, z):
        self.pos = [x, y, z]
        self.active = True
        self.speed = 1
        self.health = 3
        self.e_type = "base"
        self.facing = 0
        self.width = 20
        self.height = 20
        self.depth = 60
        
    def update(self, player_pos):
        if not self.active: return None
        dx = player_pos[0] - self.pos[0]
        dy = player_pos[1] - self.pos[1]
        dist = math.sqrt(dx*dx + dy*dy)
        if dist > 1:
            self.facing = math.degrees(math.atan2(dy, dx)) - 90
        return None

    def draw(self):
        pass

    def take_damage(self, dmg):
        self.health -= dmg
        if self.health <= 0:
            self.active = False

    def get_aabb(self):
        w = self.width / 2
        d = self.depth 
        return (self.pos[0]-w, self.pos[0]+w,
                self.pos[1]-w, self.pos[1]+w,
                self.pos[2], self.pos[2]+d)

class Zombie(Enemy):
    def __init__(self, x, y):
        super().__init__(x, y, 0)
        self.speed = 1.2
        self.health = 4
        self.e_type = "zombie"
        self.color_skin = (0.2, 0.6, 0.2)
        self.color_shirt = (0, 0.5, 0.5)
        self.color_pants = (0.2, 0.2, 0.6)

    def update(self, player_pos):
        if not self.active: return None
        dx = player_pos[0] - self.pos[0]
        dy = player_pos[1] - self.pos[1]
        dist = math.sqrt(dx*dx + dy*dy)
        if dist > 20: 
            self.pos[0] += (dx/dist) * self.speed
            self.pos[1] += (dy/dist) * self.speed
            self.facing = math.degrees(math.atan2(dy, dx)) - 90
        return None

    def draw(self):
        if not self.active: return
        glPushMatrix()
        glTranslatef(self.pos[0], self.pos[1], self.pos[2])
        glRotatef(self.facing, 0, 0, 1)
        draw_cube(-5, 0, 15, 10, 10, 30, self.color_pants)
        draw_cube( 5, 0, 15, 10, 10, 30, self.color_pants)
        draw_cube(0, 0, 45, 20, 10, 30, self.color_shirt)
        draw_cube(-15, 10, 50, 10, 25, 10, self.color_shirt)
        draw_cube( 15, 10, 50, 10, 25, 10, self.color_shirt)
        draw_cube(0, 0, 68, 16, 16, 16, self.color_skin)
        glPopMatrix()

class Skeleton(Enemy):
    def __init__(self, x, y):
        super().__init__(x, y, 0)
        self.speed = 1.0
        self.health = 3
        self.e_type = "skeleton"
        self.cooldown = 100
        self.color_bone = (0.9, 0.9, 0.9)

    def update(self, player_pos):
        if not self.active: return None
        dx = player_pos[0] - self.pos[0]
        dy = player_pos[1] - self.pos[1]
        dist = math.sqrt(dx*dx + dy*dy)
        if dist > 1:
            self.facing = math.degrees(math.atan2(dy, dx)) - 90
        if dist > 200:
            self.pos[0] += (dx/dist) * self.speed
            self.pos[1] += (dy/dist) * self.speed
        if self.cooldown > 0:
            self.cooldown -= 1
        else:
            if dist < 400:
                self.cooldown = 120
                rad = math.radians(self.facing + 90)
                return Projectile(self.pos[0], self.pos[1], 50,
                                  math.cos(rad), math.sin(rad), 0,
                                  "arrow", "enemy")
        return None

    def draw(self):
        if not self.active: return
        glPushMatrix()
        glTranslatef(self.pos[0], self.pos[1], self.pos[2])
        glRotatef(self.facing, 0, 0, 1)
        draw_cube(-4, 0, 15, 6, 6, 30, self.color_bone)
        draw_cube( 4, 0, 15, 6, 6, 30, self.color_bone)
        draw_cube(0, 0, 45, 15, 8, 30, self.color_bone)
        draw_cube(-12, 5, 50, 6, 20, 6, self.color_bone)
        draw_cube( 12, 0, 50, 6, 6, 25, self.color_bone)
        draw_cube(0, 0, 68, 14, 14, 14, self.color_bone)
        glPopMatrix()

class Creeper(Enemy):
    def __init__(self, x, y):
        super().__init__(x, y, 0)
        self.speed = 1.5
        self.health = 3
        self.e_type = "creeper"
        self.color = (0.0, 0.8, 0.0)
        self.fuse = 0
        self.exploding = False
        self.exploded = False

    def update(self, player_pos):
        if not self.active: return None
        dx = player_pos[0] - self.pos[0]
        dy = player_pos[1] - self.pos[1]
        dist = math.sqrt(dx*dx + dy*dy)
        if dist > 1:
            self.facing = math.degrees(math.atan2(dy, dx)) - 90
        if dist < 40 and not self.exploding:
            self.exploding = True
        if self.exploding:
            self.fuse += 1
            if self.fuse > 50:
                self.exploded = True
                self.active = False
        else:
            self.pos[0] += (dx/dist) * self.speed
            self.pos[1] += (dy/dist) * self.speed
        return None

    def draw(self):
        if not self.active: return
        glPushMatrix()
        glTranslatef(self.pos[0], self.pos[1], self.pos[2])
        glRotatef(self.facing, 0, 0, 1)
        c = self.color
        if self.exploding and (self.fuse // 5) % 2 == 0:
            c = (1, 1, 1)
        draw_cube(-6, -6, 10, 8, 8, 20, c)
        draw_cube( 6, -6, 10, 8, 8, 20, c)
        draw_cube(-6,  6, 10, 8, 8, 20, c)
        draw_cube( 6,  6, 10, 8, 8, 20, c)
        draw_cube(0, 0, 35, 16, 10, 30, c)
        draw_cube(0, 0, 58, 16, 16, 16, c)
        glPopMatrix()

class GiantSlime(Enemy):
    def __init__(self, x, y):
        super().__init__(x, y, 0)
        self.speed = 0.8
        self.health = 40
        self.e_type = "boss_slime"
        self.size = 60
        self.width = 60
        self.depth = 60
        self.color = (0.2, 0.9, 0.2)

    def update(self, player_pos):
        if not self.active: return None
        dx = player_pos[0] - self.pos[0]
        dy = player_pos[1] - self.pos[1]
        dist = math.sqrt(dx*dx + dy*dy)
        if dist > 30:
            self.pos[0] += (dx/dist) * self.speed
            self.pos[1] += (dy/dist) * self.speed
            self.facing = math.degrees(math.atan2(dy, dx)) - 90
        return None 

    def draw(self):
        if not self.active: return
        scale = 1.0 + 0.1 * math.sin(glutGet(GLUT_ELAPSED_TIME) / 200.0)
        glPushMatrix()
        glTranslatef(self.pos[0], self.pos[1], self.size/2 * scale)
        glRotatef(self.facing, 0, 0, 1)
        draw_cube(0, 0, 0, self.size, self.size, self.size, self.color)
        draw_cube(-15, 25, 10, 10, 5, 10, (0, 0, 0))
        draw_cube( 15, 25, 10, 10, 5, 10, (0, 0, 0))
        glPopMatrix()

    def get_aabb(self):
         w = self.size / 2
         return (self.pos[0]-w, self.pos[0]+w,
                 self.pos[1]-w, self.pos[1]+w,
                 0, self.size)

class GiantIronGolem(Enemy):
    def __init__(self, x, y):
        super().__init__(x, y, 0)
        self.speed = 1.0
        self.health = 80
        self.e_type = "boss_golem"
        self.width = 50
        self.depth = 90
        self.state = "chase"
        self.cooldown = 0
        self.dash_timer = 0

    def update(self, player_pos):
        if not self.active: return None
        dx = player_pos[0] - self.pos[0]
        dy = player_pos[1] - self.pos[1]
        dist = math.sqrt(dx*dx + dy*dy)
        self.facing = math.degrees(math.atan2(dy, dx)) - 90
        if self.cooldown > 0: self.cooldown -= 1
        if self.state == "dash":
            self.dash_timer += 1
            self.speed = 6.0
            self.pos[0] += (dx/dist) * self.speed
            self.pos[1] += (dy/dist) * self.speed
            if self.dash_timer > 30:
                self.state = "chase"
                self.cooldown = 60
                self.speed = 1.0
            return None
        if dist > 400 and self.cooldown == 0:
            self.cooldown = 120
            rad = math.radians(self.facing + 90)
            return Projectile(self.pos[0], self.pos[1], 80,
                                math.cos(rad), math.sin(rad), 0,
                                "rock", "enemy")
        elif dist < 150 and self.cooldown == 0:
            self.state = "dash"
            self.dash_timer = 0
        else:
            self.pos[0] += (dx/dist) * self.speed
            self.pos[1] += (dy/dist) * self.speed
        return None

    def draw(self):
        if not self.active: return
        glPushMatrix()
        glTranslatef(self.pos[0], self.pos[1], self.pos[2])
        glRotatef(self.facing, 0, 0, 1)
        c_body = (0.7, 0.7, 0.7)
        draw_cube(-15, 0, 25, 20, 20, 50, c_body)
        draw_cube( 15, 0, 25, 20, 20, 50, c_body)
        draw_cube(0, 0, 75, 50, 30, 50, c_body)
        draw_cube(-40, 0, 60, 20, 20, 70, c_body)
        draw_cube( 40, 0, 60, 20, 20, 70, c_body)
        draw_cube(0, 0, 110, 20, 20, 20, c_body)
        draw_cube(0, 12, 110, 5, 5, 8, (0.6, 0.1, 0.1)) # Nose
        glPopMatrix()

# --- GLOBAL GAME STATE & MAIN LOGIC ---

# Global State
window = None
keys = {} 
camera = Camera()
player = Player()
world = World()

enemies = []
projectiles = []
slime_trails = [] # List of {'pos': [x,y], 'timer': 100}
fire_trails = []  # List of {'pos': [x,y,z], 'timer': 200, 'damage': 5}
xp_orbs = []      # List of {'pos': [x,y,z], 'value': 10, 'angle': 0}
defeated_count = 0
spawn_timer = 0
game_over = False

# Spell System
AVAILABLE_SPELLS = ["fireball", "fire_step", "bullet_hell", "lifesteal"]
level_up_pending = False
spell_choices = []  # 3 random spells to choose from

# Bullet Hell State
bullet_hell_charges = 0
bullet_hell_cooldown = 0

# Quadric for gluSphere/gluCylinder
_quadric = None

def get_quadric():
    global _quadric
    if _quadric is None:
        _quadric = gluNewQuadric()
    return _quadric

def check_aabb_collision(box1, box2):
    return (box1[0] <= box2[1] and box1[1] >= box2[0] and
            box1[2] <= box2[3] and box1[3] >= box2[2] and
            box1[4] <= box2[5] and box1[5] >= box2[4])

def draw_text(x, y, text):
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, 800, 0, 600)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    glColor3f(1, 1, 1)
    glRasterPos3f(x, y, 0.9)
    for ch in text:
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(ch))
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

def init():
    glClearColor(0.5, 0.7, 1.0, 1.0)
    glEnable(GL_DEPTH_TEST)

def draw_level_up_screen():
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, 800, 0, 600)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    
    glColor3f(0.1, 0.1, 0.2)
    glBegin(GL_QUADS)
    glVertex3f(150, 150, -0.5)
    glVertex3f(650, 150, -0.5)
    glVertex3f(650, 450, -0.5)
    glVertex3f(150, 450, -0.5)
    glEnd()
    
    glColor3f(1, 1, 0)
    glRasterPos3f(320, 400, 0.5)
    for ch in "LEVEL UP!":
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(ch))
    
    glColor3f(1, 1, 1)
    glRasterPos3f(280, 370, 0.5)
    for ch in "Choose a spell (1, 2, or 3):":
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(ch))
    
    spell_names = {
        "fireball": "Fire Projectile - Cast a ball of fire",
        "fire_step": "Fire Step - Leave damaging fire trails",
        "bullet_hell": "Bullet Hell - Fire 3 bullets quickly",
        "lifesteal": "Lifesteal - Heal when hitting enemies"
    }
    
    for i, spell in enumerate(spell_choices):
        y_pos = 320 - i * 50
        glColor3f(0.3, 0.3, 0.5)
        glBegin(GL_QUADS)
        glVertex3f(180, y_pos - 15, 0.0)
        glVertex3f(620, y_pos - 15, 0.0)
        glVertex3f(620, y_pos + 25, 0.0)
        glVertex3f(180, y_pos + 25, 0.0)
        glEnd()
        
        glColor3f(1, 1, 1)
        glRasterPos3f(190, y_pos, 0.5)
        text = f"{i+1}. {spell_names.get(spell, spell)}"
        for ch in text:
            glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(ch))
    
    glColor3f(0.8, 0.8, 0.8)
    glRasterPos3f(200, 180, 0.5)
    current_text = f"Current Spell: {player.current_spell.upper()}"
    for ch in current_text:
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(ch))
    
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

def display():
    global game_over, level_up_pending
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    
    if game_over:
        draw_text(350, 300, "GAME OVER")
        draw_text(300, 270, "Press R to Restart")
        glutSwapBuffers()
        return
    
    if level_up_pending:
        draw_level_up_screen()
        glutSwapBuffers()
        return

    camera.update(player.pos)
    camera.setup_camera()
    world.draw()
    player.draw()
    for e in enemies:
        e.draw()
    for p in projectiles:
        p.draw()
        
    glColor3f(0, 1, 0)
    for t in slime_trails:
        glPushMatrix()
        glTranslatef(t['pos'][0], t['pos'][1], 1)
        glScalef(10, 10, 2)
        glutSolidCube(1)
        glPopMatrix()
    
    for ft in fire_trails:
        glPushMatrix()
        glTranslatef(ft['pos'][0], ft['pos'][1], ft['pos'][2])
        intensity = 0.5 + 0.5 * math.sin(ft['timer'] * 0.3)
        glColor3f(1.0, 0.3 * intensity, 0.0)
        glScalef(8, 8, 3)
        glutSolidCube(1)
        glPopMatrix()
    
    for orb in xp_orbs:
        glPushMatrix()
        glTranslatef(orb['pos'][0], orb['pos'][1], orb['pos'][2] + math.sin(orb['angle'] * 0.1) * 3)
        glRotatef(orb['angle'], 0, 0, 1)
        glColor3f(0.0, 1.0, 1.0)
        glScalef(5, 5, 5)
        glutSolidCube(1)
        glPopMatrix()
        
    draw_text(10, 570, f"Health: {int(player.health)} | Level: {player.level} | XP: {player.xp}/{player.level * 100} | Defeated: {defeated_count}")
    draw_text(10, 545, f"Spell: {player.current_spell.upper()}")
    if player.current_spell == "bullet_hell" and bullet_hell_cooldown > 0:
        draw_text(10, 520, f"Reloading... {bullet_hell_cooldown // 10}")
    
    glutSwapBuffers()

def find_nearest_enemy():
    nearest = None
    min_dist = 99999
    for e in enemies:
        dist = math.sqrt((e.pos[0]-player.pos[0])**2 + (e.pos[1]-player.pos[1])**2)
        if dist < min_dist:
            min_dist = dist
            nearest = e
    return nearest

def idle():
    global spawn_timer, game_over, enemies, projectiles, slime_trails, fire_trails, xp_orbs
    global defeated_count, level_up_pending, spell_choices
    global bullet_hell_charges, bullet_hell_cooldown
    
    if game_over:
        if b'r' in keys and keys[b'r']:
            restart_game()
        glutPostRedisplay()
        return
    if level_up_pending:
        glutPostRedisplay()
        return

    player.update(keys, camera.angle_x)
    player.tick_cooldown()
    
    if player.current_spell == "fire_step":
        if b'w' in keys and keys[b'w'] or b'a' in keys and keys[b'a'] or b's' in keys and keys[b's'] or b'd' in keys and keys[b'd']:
            if len(fire_trails) == 0 or math.sqrt(
                (fire_trails[-1]['pos'][0] - player.pos[0])**2 + 
                (fire_trails[-1]['pos'][1] - player.pos[1])**2) > 30:
                fire_trails.append({'pos': [player.pos[0], player.pos[1], 2], 'timer': 200, 'damage': 5})
    
    if bullet_hell_cooldown > 0:
        bullet_hell_cooldown -= 1
    
    nearest = find_nearest_enemy()
    target_pos = nearest.pos if nearest else None
    
    if nearest and math.sqrt((nearest.pos[0]-player.pos[0])**2 + (nearest.pos[1]-player.pos[1])**2) < 400:
        if player.current_spell == "bullet_hell":
            if bullet_hell_cooldown <= 0 and player.attack_cooldown <= 0:
                bullet_hell_charges = 3
                bullet_hell_cooldown = 90
        else:
            proj = player.shoot(target_pos)
            if proj: projectiles.append(proj)
        
        if bullet_hell_charges > 0 and player.attack_cooldown <= 0:
            proj = player.shoot(target_pos)
            if proj:
                proj.p_type = "bullet"
                proj.speed = 20
                proj.size = 3
                proj.color = (1.0, 1.0, 0.0)
                projectiles.append(proj)
            bullet_hell_charges -= 1
            player.attack_cooldown = 5
    
    if not player.boss_active:
        if defeated_count >= 50 and not player.bosses_defeated.get('slime'):
             spawn_boss("slime")
        elif defeated_count >= 100 and not player.bosses_defeated.get('golem'):
             spawn_boss("golem")
        elif len(enemies) == 0:
            spawn_wave(10)
    
    player.speed = 5
    active_slime_trails = []
    for t in slime_trails:
        t['timer'] -= 1
        if t['timer'] > 0:
            active_slime_trails.append(t)
            dx, dy = player.pos[0] - t['pos'][0], player.pos[1] - t['pos'][1]
            if math.sqrt(dx*dx + dy*dy) < 15: player.speed = 2
    slime_trails = active_slime_trails
    
    active_fire_trails = []
    for ft in fire_trails:
        ft['timer'] -= 1
        if ft['timer'] > 0:
            active_fire_trails.append(ft)
            for e in enemies:
                dx, dy = e.pos[0] - ft['pos'][0], e.pos[1] - ft['pos'][1]
                if math.sqrt(dx*dx + dy*dy) < 15: e.take_damage(0.2)
    fire_trails = active_fire_trails
    
    active_orbs = []
    for orb in xp_orbs:
        orb['angle'] += 5
        dx, dy = player.pos[0] - orb['pos'][0], player.pos[1] - orb['pos'][1]
        dist = math.sqrt(dx*dx + dy*dy)
        if dist < 80:
            orb['pos'][0] += dx * 0.08
            orb['pos'][1] += dy * 0.08
        if dist < 40:
            player.xp += orb['value']
            if player.xp >= player.level * 100:
                player.xp -= player.level * 100
                player.level += 1
                player.health = player.max_health
                level_up_pending = True
                new_choices, pool = [], list(AVAILABLE_SPELLS)
                for _ in range(3):
                    if not pool: break
                    idx = random.randint(0, len(pool)-1)
                    new_choices.append(pool.pop(idx))
                spell_choices = new_choices
        else:
            active_orbs.append(orb)
    xp_orbs = active_orbs

    for e in enemies:
        result = e.update(player.pos)
        if e.e_type == "boss_slime" and random.random() < 0.1:
             slime_trails.append({'pos': list(e.pos), 'timer': 300})
        if result and isinstance(result, Projectile):
            projectiles.append(result)
        if e.e_type == "creeper" and getattr(e, "exploded", False):
            if math.sqrt((e.pos[0]-player.pos[0])**2 + (e.pos[1]-player.pos[1])**2) < 100:
                player.take_damage(30)
        if check_aabb_collision(e.get_aabb(), player.get_aabb()):
            if e.e_type != "creeper": player.take_damage(0.5) 
    
    for p in projectiles:
        p.update()
        if p.owner == "player":
            p_aabb = p.get_aabb()
            for e in enemies:
                if check_aabb_collision(p_aabb, e.get_aabb()):
                    e.take_damage(p.damage)
                    p.active = False
                    if player.current_spell == "lifesteal":
                        player.health = min(player.max_health, player.health + p.damage * 0.5)
                    if not e.active:
                        if "boss" not in e.e_type:
                            xp_orbs.append({'pos': [e.pos[0], e.pos[1], 10], 'value': 15, 'angle': 0})
                            defeated_count += 1
                        else:
                            player.boss_active = False
                            xp_orbs.append({'pos': [e.pos[0], e.pos[1], 10], 'value': 100, 'angle': 0})
                            if e.e_type == "boss_slime":
                                player.bosses_defeated['slime'] = True
                                world.zone = "nether"
                            elif e.e_type == "boss_golem":
                                player.bosses_defeated['golem'] = True
                    break
        elif p.owner == "enemy":
            if check_aabb_collision(p.get_aabb(), player.get_aabb()):
                player.take_damage(p.damage)
                p.active = False
    
    enemies = [e for e in enemies if e.active]
    projectiles = [p for p in projectiles if p.active]
    if player.health <= 0: game_over = True
    glutPostRedisplay()

def spawn_wave(count):
    for i in range(count):
        angle, dist = random.uniform(0, 6.28), 600
        ex, ey = player.pos[0] + math.cos(angle) * dist, player.pos[1] + math.sin(angle) * dist
        rtype = random.random()
        if rtype < 0.5: enemies.append(Zombie(ex, ey))
        elif rtype < 0.8: enemies.append(Skeleton(ex, ey))
        else: enemies.append(Creeper(ex, ey))

def spawn_boss(b_type):
    player.boss_active = True
    angle, dist = random.uniform(0, 6.28), 500
    ex, ey = player.pos[0] + math.cos(angle) * dist, player.pos[1] + math.sin(angle) * dist
    if b_type == "slime": enemies.append(GiantSlime(ex, ey))
    elif b_type == "golem": enemies.append(GiantIronGolem(ex, ey))

def restart_game():
    global enemies, projectiles, slime_trails, fire_trails, xp_orbs
    global game_over, defeated_count, level_up_pending, bullet_hell_charges, bullet_hell_cooldown
    player.health, player.pos, player.level, player.xp = player.max_health, [0,0,0], 1, 0
    player.current_spell, player.boss_active, player.bosses_defeated = "fireball", False, {}
    enemies, projectiles, slime_trails, fire_trails, xp_orbs = [], [], [], [], []
    game_over, defeated_count, level_up_pending = False, 0, False
    bullet_hell_charges, bullet_hell_cooldown, world.zone = 0, 0, "overworld"

def keyboard_down(key, x, y):
    global level_up_pending, spell_choices
    keys[key] = True
    if level_up_pending:
        idx = -1
        if key == b'1': idx = 0
        elif key == b'2': idx = 1
        elif key == b'3': idx = 2
        if idx != -1 and idx < len(spell_choices):
            player.current_spell = spell_choices[idx]
            level_up_pending = False

def keyboard_up(key, x, y):
    keys[key] = False

def mouse(button, state, x, y):
    camera.mouse_listener(button, state, x, y)

def motion(x, y):
    camera.mouse_motion(x, y)

def main():
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(800, 600)
    glutInitWindowPosition(0, 0)
    glutCreateWindow(b"Wizard Bonk 3D")
    init()
    glutDisplayFunc(display)
    glutIdleFunc(idle)
    glutKeyboardFunc(keyboard_down)
    glutKeyboardUpFunc(keyboard_up)
    glutMouseFunc(mouse)
    glutMotionFunc(motion)
    glutMainLoop()

if __name__ == "__main__":
    main()