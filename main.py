import pygame
import math
import random
from enum import Enum
from typing import List, Tuple, Optional

# Initialize pygame
pygame.init()

# Screen dimensions and setup
WIDTH, HEIGHT = 1000, 800
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("City Rescue Simulation")
clock = pygame.time.Clock()

# Colors
WHITE = (255, 255, 255)
BLACK = (20, 20, 20)
RED = (231, 76, 60)
BLUE = (52, 152, 219)
GREEN = (46, 204, 113)
GRAY = (149, 165, 166)
YELLOW = (241, 196, 15)
PURPLE = (155, 89, 182)
BROWN = (139, 69, 19)

# City grid configuration
GRID_SIZE = 50
COLS = WIDTH // GRID_SIZE
ROWS = HEIGHT // GRID_SIZE

class RescueState(Enum):
    SEEKING_VICTIM = 1
    MOVING_TO_HOSPITAL = 2

class GameObject:
    def __init__(self, x: float, y: float, color: Tuple[int, int, int], radius: int = 10):
        self.position = pygame.Vector2(x, y)
        self.color = color
        self.radius = radius
        self.is_active = True

    def draw(self, screen):
        if self.is_active:
            pygame.draw.circle(screen, self.color, (int(self.position.x), int(self.position.y)), self.radius)

class Obstacle(GameObject):
    def __init__(self, x: float, y: float, width: int, height: int):
        super().__init__(x, y, BROWN)
        self.width = width
        self.height = height
        self.rect = pygame.Rect(x - width/2, y - height/2, width, height)

    def draw(self, screen):
        if self.is_active:
            pygame.draw.rect(screen, self.color, self.rect)
            
    def update_rect(self):
        self.rect = pygame.Rect(
            self.position.x - self.width/2, 
            self.position.y - self.height/2, 
            self.width, 
            self.height
        )

class Hospital(GameObject):
    def __init__(self, x: float, y: float):
        super().__init__(x, y, GREEN, 20)
        self.rect = pygame.Rect(x - 20, y - 20, 40, 40)

    def draw(self, screen):
        if self.is_active:
            pygame.draw.circle(screen, self.color, (int(self.position.x), int(self.position.y)), self.radius)
            # Add a cross to make the hospital more recognizable
            pygame.draw.line(screen, WHITE, 
                            (self.position.x - 10, self.position.y),
                            (self.position.x + 10, self.position.y), 3)
            pygame.draw.line(screen, WHITE, 
                            (self.position.x, self.position.y - 10),
                            (self.position.x, self.position.y + 10), 3)

class Victim(GameObject):
    def __init__(self, x: float, y: float):
        super().__init__(x, y, RED, 8)
        self.blink_timer = 0
        self.blink_rate = 30  # Frames between blinks
    
    def draw(self, screen):
        if self.is_active:
            # Make victims blink to attract attention
            self.blink_timer = (self.blink_timer + 1) % self.blink_rate
            if self.blink_timer < self.blink_rate * 0.8:
                pygame.draw.circle(screen, self.color, (int(self.position.x), int(self.position.y)), self.radius)
            else:
                pygame.draw.circle(screen, YELLOW, (int(self.position.x), int(self.position.y)), self.radius)

class Rescuer(GameObject):
    def __init__(self, x: float, y: float, color: Tuple[int, int, int], is_player: bool = False):
        super().__init__(x, y, color, 12)
        self.velocity = pygame.Vector2(0, 0)
        self.acceleration = pygame.Vector2(0, 0)
        self.max_speed = 4 if is_player else 3  # NPC slightly slower
        self.max_force = 0.5
        self.carried_victim: Optional[Victim] = None
        self.current_state = RescueState.SEEKING_VICTIM
        self.is_player = is_player
        self.target_victim: Optional[Victim] = None
        self.rect = pygame.Rect(x - 12, y - 12, 24, 24)
        self.path_timer = 0
        self.stuck_timer = 0
        self.last_positions = []

    def apply_force(self, force: pygame.Vector2):
        self.acceleration += force

    def seek(self, target: pygame.Vector2) -> None:
        desired = target - self.position
        if desired.length() > 0:
            desired = desired.normalize() * self.max_speed
            steer = desired - self.velocity
            if steer.length() > self.max_force:
                steer = steer.normalize() * self.max_force
            self.apply_force(steer)

    def avoid_obstacles(self, obstacles: List[Obstacle], look_ahead: float = 100) -> None:
        # Only apply obstacle avoidance if we're moving
        if self.velocity.length() < 0.1:
            return
            
        # Calculate the look-ahead position based on our current velocity
        velocity_dir = self.velocity.normalize()
        
        # Check for multiple angles to better detect obstacles
        angles = [0, 15, -15, 30, -30]
        for angle in angles:
            # Rotate velocity direction by this angle
            rads = math.radians(angle)
            rotated_dir = pygame.Vector2(
                velocity_dir.x * math.cos(rads) - velocity_dir.y * math.sin(rads),
                velocity_dir.x * math.sin(rads) + velocity_dir.y * math.cos(rads)
            )
            
            future_pos = self.position + rotated_dir * look_ahead
            
            # Check for potential collisions with obstacles
            for obstacle in obstacles:
                # Check if our look-ahead position is inside any obstacle
                if obstacle.rect.collidepoint(future_pos):
                    # Calculate avoidance vector (perpendicular to velocity)
                    # This creates a more natural steering around obstacles
                    perp_dir = pygame.Vector2(-velocity_dir.y, velocity_dir.x)
                    
                    # Determine which side to avoid to (left or right of obstacle)
                    to_obstacle = obstacle.position - self.position
                    side_dot = perp_dir.dot(to_obstacle)
                    if side_dot < 0:
                        perp_dir = -perp_dir
                        
                    # Apply stronger force when closer to obstacle
                    dist_factor = 1.0 - min(1.0, self.position.distance_to(obstacle.position) / (look_ahead * 1.5))
                    avoid_force = perp_dir * self.max_force * 3 * (dist_factor + 0.5)
                    self.apply_force(avoid_force)
                    return

    def update(self, victims: List[Victim], hospitals: List[Hospital], obstacles: List[Obstacle]) -> None:
        # Track position history to detect being stuck
        self.last_positions.append(pygame.Vector2(self.position))
        if len(self.last_positions) > 30:  # Track last 30 frames
            self.last_positions.pop(0)
        
        # Update position and movement
        self.velocity += self.acceleration
        if self.velocity.length() > self.max_speed:
            self.velocity = self.velocity.normalize() * self.max_speed
        
        # Store old position to check for collisions
        old_position = pygame.Vector2(self.position)
        
        # Update position
        self.position += self.velocity
        self.acceleration *= 0
        
        # Update rect for collision detection
        self.rect.center = (self.position.x, self.position.y)
        
        # Check for collisions with obstacles
        collision_occurred = False
        for obstacle in obstacles:
            if self.rect.colliderect(obstacle.rect):
                collision_occurred = True
                # Move back slightly and adjust direction
                self.position -= self.velocity * 2  # Move back slightly
                self.velocity *= -0.3  # Reduce velocity but don't stop completely
                
                # Find an alternative direction
                avoidance_force = pygame.Vector2(random.uniform(-1, 1), random.uniform(-1, 1)).normalize() * self.max_force * 2
                self.apply_force(avoidance_force)
                break
        
        # Keep within bounds
        self.position.x = max(self.radius, min(WIDTH - self.radius, self.position.x))
        self.position.y = max(self.radius, min(HEIGHT - self.radius, self.position.y))
        self.rect.center = (self.position.x, self.position.y)

        # Handle victim collection and hospital logic for player
        if self.is_player:
            self.update_player_mission(victims, hospitals)
        else:
            self.update_ai_behavior(victims, hospitals, obstacles)

        # Update carried victim position
        if self.carried_victim:
            self.carried_victim.position = self.position + pygame.Vector2(0, -20)
            
        # Check if NPC is stuck
        if not self.is_player and len(self.last_positions) >= 30:
            max_dist = max(self.last_positions[i].distance_to(self.last_positions[j]) 
                        for i in range(len(self.last_positions)) 
                        for j in range(i+1, len(self.last_positions)))

            if max_dist < 30:  # If NPC has not moved much
                self.stuck_timer += 1
                if self.stuck_timer > 60:  # Stuck for more than 1 second
                    unstuck_force = pygame.Vector2(random.uniform(-1, 1), random.uniform(-1, 1)).normalize() * self.max_force * 5
                    self.apply_force(unstuck_force)
                    self.stuck_timer = 0  # Reset timer
            else:
                self.stuck_timer = 0


    def update_player_mission(self, victims: List[Victim], hospitals: List[Hospital]) -> None:
        if self.current_state == RescueState.SEEKING_VICTIM:
            # Check if near any victim
            for victim in victims:
                if victim.is_active and self.position.distance_to(victim.position) < 20:
                    self.pick_up_victim(victim)
                    self.current_state = RescueState.MOVING_TO_HOSPITAL
                    break
        
        elif self.current_state == RescueState.MOVING_TO_HOSPITAL:
            # Check if near any hospital
            for hospital in hospitals:
                if self.position.distance_to(hospital.position) < 30:
                    self.drop_off_victim()
                    self.current_state = RescueState.SEEKING_VICTIM
                    break

    def update_ai_behavior(self, victims: List[Victim], hospitals: List[Hospital], obstacles: List[Obstacle]) -> None:
        # Apply obstacle avoidance
        self.avoid_obstacles(obstacles)
        
        # Update pathfinding timer
        self.path_timer += 1
        
        if self.current_state == RescueState.SEEKING_VICTIM:
            # Reconsider target victim periodically or if current target is gone
            if not self.target_victim or not self.target_victim.is_active or self.path_timer >= 120:
                self.choose_new_victim(victims)
                self.path_timer = 0
            
            if self.target_victim:
                # Apply stronger force to ensure movement
                target_dir = (self.target_victim.position - self.position)
                if target_dir.length() > 0:
                    target_dir = target_dir.normalize() * self.max_force * 2
                    self.apply_force(target_dir)
                
                # Check if reached victim
                if self.position.distance_to(self.target_victim.position) < 20:
                    self.pick_up_victim(self.target_victim)
                    self.current_state = RescueState.MOVING_TO_HOSPITAL
                    self.path_timer = 0
        
        elif self.current_state == RescueState.MOVING_TO_HOSPITAL:
            # Find nearest hospital
            if len(hospitals) > 0:
                nearest_hospital = min(hospitals, key=lambda h: self.position.distance_to(h.position))
                
                # Apply stronger force to ensure movement
                hospital_dir = (nearest_hospital.position - self.position)
                if hospital_dir.length() > 0:
                    hospital_dir = hospital_dir.normalize() * self.max_force * 2
                    self.apply_force(hospital_dir)
                
                # Check if reached hospital
                if self.position.distance_to(nearest_hospital.position) < 30:
                    self.drop_off_victim()
                    self.current_state = RescueState.SEEKING_VICTIM
                    self.path_timer = 0

    def choose_new_victim(self, victims: List[Victim]) -> None:
        active_victims = [v for v in victims if v.is_active]
        if active_victims:
            # Simple planning: choose the nearest victim
            self.target_victim = min(active_victims, key=lambda v: self.position.distance_to(v.position))
        else:
            self.target_victim = None

    def pick_up_victim(self, victim: Victim) -> None:
        self.carried_victim = victim
        victim.is_active = False  # Hide from world but keep tracking it with rescuer

    def drop_off_victim(self) -> None:
        if self.carried_victim:
            self.carried_victim.is_active = False  # Permanently deactivate
            self.carried_victim = None

    def draw(self, screen):
        if self.is_active:
            pygame.draw.circle(screen, self.color, (int(self.position.x), int(self.position.y)), self.radius)
            # Draw direction indicator
            if self.velocity.length() > 0:
                direction = self.velocity.normalize() * (self.radius + 5)
                pygame.draw.line(screen, WHITE, 
                                self.position, 
                                self.position + direction, 2)
            
            # Draw different state indicators
            if self.current_state == RescueState.SEEKING_VICTIM:
                # Draw a question mark above when seeking
                font = pygame.font.Font(None, 20)
                text = font.render("?", True, WHITE)
                text_rect = text.get_rect(center=(self.position.x, self.position.y - 25))
                screen.blit(text, text_rect)
            elif self.current_state == RescueState.MOVING_TO_HOSPITAL and self.carried_victim:
                # Draw a plus sign when carrying victim
                pygame.draw.line(screen, WHITE, 
                                (self.position.x, self.position.y - 30),
                                (self.position.x, self.position.y - 20), 2)
                pygame.draw.line(screen, WHITE, 
                                (self.position.x - 5, self.position.y - 25),
                                (self.position.x + 5, self.position.y - 25), 2)

class Game:
    def __init__(self):
        self.victims = []
        self.hospitals = []
        self.obstacles = []
        self.player = Rescuer(WIDTH//4, HEIGHT//4, BLUE, True)
        self.npc = Rescuer(WIDTH//2, HEIGHT//2, YELLOW, False)
        self.rescued_count = 0
        self.setup_world()
        self.font = pygame.font.Font(None, 36)

    def setup_world(self):
        # Create hospitals in fixed positions
        self.hospitals = [
            Hospital(WIDTH//4, HEIGHT//4),
            Hospital(3*WIDTH//4, 3*HEIGHT//4)
        ]

        # Create fixed obstacles (buildings, barricades, etc.)
        self.obstacles = [
            # Large buildings
            Obstacle(200, 150, 80, 100),   # Downtown area
            Obstacle(350, 200, 90, 80),    # Office building
            Obstacle(500, 350, 100, 90),   # Shopping mall
            Obstacle(700, 200, 85, 95),    # Apartment complex
            Obstacle(800, 500, 90, 100),   # Warehouse
            Obstacle(250, 600, 100, 80),   # Factory
            Obstacle(650, 650, 80, 70),    # Community center
            Obstacle(450, 750, 90, 60),    # School
            
            # Medium obstacles
            Obstacle(150, 400, 50, 60),    # Small shop
            Obstacle(300, 350, 55, 45),    # Convenience store
            Obstacle(650, 400, 40, 70),    # Bus station
            Obstacle(450, 550, 60, 50),    # Gas station
            Obstacle(850, 300, 45, 65),    # Pharmacy
            
            # Small obstacles/debris
            Obstacle(400, 100, 30, 30),    # Fallen tree
            Obstacle(550, 200, 25, 35),    # Debris pile
            Obstacle(250, 500, 35, 25),    # Damaged car
            Obstacle(600, 550, 30, 30),    # Road barricade
            Obstacle(750, 400, 25, 25),    # Small debris
            Obstacle(350, 650, 20, 40),    # Damaged pole
            Obstacle(500, 450, 30, 20)     # Small barrier
        ]
        
        # Ensure obstacles don't overlap with hospitals
        for obstacle in self.obstacles[:]:
            for hospital in self.hospitals:
                if obstacle.rect.colliderect(hospital.rect) or \
                   obstacle.position.distance_to(hospital.position) < 80:
                    # Instead of removing, adjust the position slightly
                    obstacle.position += pygame.Vector2(80, 0)
                    obstacle.update_rect()

        # Ensure player and NPC starting positions are clear
        for obstacle in self.obstacles[:]:
            if obstacle.rect.collidepoint(self.player.position.x, self.player.position.y) or \
               obstacle.rect.collidepoint(self.npc.position.x, self.npc.position.y) or \
               obstacle.position.distance_to(self.player.position) < 50 or \
               obstacle.position.distance_to(self.npc.position) < 50:
                # Instead of removing, adjust the position slightly
                obstacle.position += pygame.Vector2(0, 80)
                obstacle.update_rect()

        # Create victims in fixed positions (not inside obstacles)
        victim_positions = [
            (120, 200), (450, 150), (750, 150), (850, 350),
            (100, 650), (350, 550), (650, 100), (800, 700),
            (180, 340), (550, 600), (300, 750), (600, 300)
        ]
        
        self.victims = []
        for pos in victim_positions:
            x, y = pos
            position = pygame.Vector2(x, y)
            
            # Check it's not inside an obstacle
            if not any(obstacle.rect.collidepoint(x, y) for obstacle in self.obstacles):
                self.victims.append(Victim(x, y))
            else:
                # Find a nearby safe position
                for offset_x in range(-100, 100, 20):
                    for offset_y in range(-100, 100, 20):
                        new_x, new_y = x + offset_x, y + offset_y
                        if (0 < new_x < WIDTH and 0 < new_y < HEIGHT and
                            not any(obstacle.rect.collidepoint(new_x, new_y) for obstacle in self.obstacles)):
                            self.victims.append(Victim(new_x, new_y))
                            break
                    else:
                        continue
                    break

    def handle_player_input(self):
        keys = pygame.key.get_pressed()
        move_dir = pygame.Vector2(0, 0)
        
        if keys[pygame.K_LEFT]:
            move_dir.x = -1
        if keys[pygame.K_RIGHT]:
            move_dir.x = 1
        if keys[pygame.K_UP]:
            move_dir.y = -1
        if keys[pygame.K_DOWN]:
            move_dir.y = 1
            
        if move_dir.length() > 0:
            move_dir = move_dir.normalize() * self.player.max_force * 2  # Increased force for better control
            self.player.apply_force(move_dir)

    def update(self):
        self.handle_player_input()
        self.player.update(self.victims, self.hospitals, self.obstacles)
        self.npc.update(self.victims, self.hospitals, self.obstacles)
        
        # Count rescued victims
        active_victims = sum(1 for v in self.victims if v.is_active or v == self.player.carried_victim or v == self.npc.carried_victim)
        total_victims = len(self.victims)
        self.rescued_count = total_victims - active_victims

    def draw(self):
        # Clear screen
        screen.fill(BLACK)
        
        # Draw city grid
        for x in range(0, WIDTH, GRID_SIZE):
            pygame.draw.line(screen, GRAY, (x, 0), (x, HEIGHT), 1)
        for y in range(0, HEIGHT, GRID_SIZE):
            pygame.draw.line(screen, GRAY, (0, y), (WIDTH, y), 1)

        # Draw game objects
        for obstacle in self.obstacles:
            obstacle.draw(screen)
        for hospital in self.hospitals:
            hospital.draw(screen)
        for victim in self.victims:
            victim.draw(screen)
        self.npc.draw(screen)
        self.player.draw(screen)

        # Draw game status
        active_victims = sum(1 for v in self.victims if v.is_active)
        rescuing_victims = (1 if self.player.carried_victim else 0) + (1 if self.npc.carried_victim else 0)
        remaining = active_victims + rescuing_victims
        
        # Status text
        text = self.font.render(f'Remaining Victims: {remaining}', True, WHITE)
        screen.blit(text, (10, 10))
        
        text = self.font.render(f'Rescued: {self.rescued_count}', True, GREEN)
        screen.blit(text, (10, 50))
        
        # Player status
        if self.player.current_state == RescueState.SEEKING_VICTIM:
            status = "Mission: Find victims"
        else:
            status = "Mission: Take victim to hospital"
        text = self.font.render(status, True, BLUE)
        screen.blit(text, (WIDTH - 350, 10))
        
        # Check win condition
        if remaining == 0:
            win_text = self.font.render('All victims rescued! Mission complete!', True, GREEN)
            win_rect = win_text.get_rect(center=(WIDTH//2, HEIGHT//2))
            pygame.draw.rect(screen, BLACK, win_rect.inflate(20, 20))
            pygame.draw.rect(screen, GREEN, win_rect.inflate(20, 20), 2)
            screen.blit(win_text, win_rect)

    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

            self.update()
            self.draw()
            pygame.display.flip()
            clock.tick(60)

if __name__ == "__main__":
    game = Game()
    game.run()