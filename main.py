import pygame
from enum import Enum

# Constants
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
GRID_SIZE = 40  # Increased grid size for easier control
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)     # Victims
GREEN = (0, 255, 0)   # Player
BLUE = (0, 0, 255)    # NPC
YELLOW = (255, 255, 0)  # Hospitals
GRAY = (128, 128, 128)  # Buildings

def normalize(vector):
    """Normalize a vector (make it length 1)"""
    if vector.length() > 0:
         return vector.normalize()
    return vector

class EntityType(Enum):
    EMPTY = 0
    BUILDING = 1
    VICTIM = 2
    HOSPITAL = 3
    PLAYER = 4
    NPC = 5

class EntityState(Enum):
    IDLE = 0
    GOING_TO_VICTIM = 1
    CARRYING_VICTIM = 2
    GOING_TO_HOSPITAL = 3

class Entity:
    def __init__(self, x, y, entity_type, color):
        self.x = x
        self.y = y
        self.type = entity_type
        self.color = color
        self.carrying_victim = False
        self.state = EntityState.IDLE
        self.path = []
        self.target = None
        self.position = pygame.Vector2(x * GRID_SIZE + GRID_SIZE//2, y * GRID_SIZE + GRID_SIZE//2)
        self.velocity = pygame.Vector2(0, 0)
        self.max_speed = 5.0  # Adjust as needed
        self.max_force = 0.5  # Adjust as needed
    
    def seek(self, target):
        """Apply seek steering behavior towards target position"""
        # Convert grid target to pixel position
        target_position = pygame.Vector2(target[0] * GRID_SIZE + GRID_SIZE//2, 
                                        target[1] * GRID_SIZE + GRID_SIZE//2)
        
        desired = target_position - self.position
        
        # If we're very close, slow down (arrival behavior)
        distance = desired.length()
        if distance < GRID_SIZE:
            # Scale by distance for smoother arrival
            desired = normalize(desired) * self.max_speed * (distance / GRID_SIZE)
        else:
            desired = normalize(desired) * self.max_speed
        
        steering = desired - self.velocity  # Compute steering force
        steering = normalize(steering) * min(self.max_force, steering.length())  # Limit force
        
        self.apply_force(steering)

    def apply_force(self, force):
        """Apply a force to the entity, updating its velocity"""
        self.velocity += force
        if self.velocity.length() > self.max_speed:
            self.velocity = normalize(self.velocity) * self.max_speed

    def update_position(self):
        """Update entity position based on velocity"""
        self.position += self.velocity
        
        # Update grid position based on pixel position
        new_grid_x = int(self.position.x // GRID_SIZE)
        new_grid_y = int(self.position.y // GRID_SIZE)
        
        # Return the new grid coordinates if they've changed
        if new_grid_x != self.x or new_grid_y != self.y:
            return new_grid_x, new_grid_y
        return None

    def draw(self, screen):
        pygame.draw.rect(screen, self.color, 
                         (self.x * GRID_SIZE, self.y * GRID_SIZE, 
                          GRID_SIZE, GRID_SIZE))
        
        # Draw a smaller rect if carrying a victim
        if self.carrying_victim:
            victim_color = RED
            pygame.draw.rect(screen, victim_color, 
                            (self.x * GRID_SIZE + GRID_SIZE//4, 
                             self.y * GRID_SIZE + GRID_SIZE//4, 
                             GRID_SIZE//2, GRID_SIZE//2))

class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Simple Rescue Mission")
        self.clock = pygame.time.Clock()
        self.grid_width = SCREEN_WIDTH // GRID_SIZE
        self.grid_height = SCREEN_HEIGHT // GRID_SIZE
        
        # Initialize grid
        self.grid = [[EntityType.EMPTY for _ in range(self.grid_height)] 
                    for _ in range(self.grid_width)]
        
        # Entity lists
        self.buildings = []
        self.victims = []
        self.hospitals = []
        self.player = None
        self.npc = None
        
        self.running = True
        self.rescued_count = 0
        self.total_victims = 0
        
        # Set up fixed layout
        self.setup_fixed_layout()
    
    def setup_fixed_layout(self):
        # Define fixed positions for buildings in a simple maze-like pattern
        building_positions = [
            # Horizontal walls
            (2, 2), (3, 2), (4, 2), (5, 2), (6, 2),
            (10, 2), (11, 2), (12, 2), (13, 2), (14, 2),
            (2, 7), (3, 7), (4, 7), (5, 7), (6, 7),
            (10, 7), (11, 7), (12, 7), (13, 7), (14, 7),
            (2, 12), (3, 12), (4, 12), (5, 12), (6, 12),
            # Vertical walls
            (8, 1), (8, 2), (8, 3), (8, 4), (8, 5),
            (8, 9), (8, 10), (8, 11), (8, 12), (8, 13)
        ]
        
        # Create buildings at fixed positions
        for x, y in building_positions:
            if 0 <= x < self.grid_width and 0 <= y < self.grid_height:
                self.grid[x][y] = EntityType.BUILDING
                building = Entity(x, y, EntityType.BUILDING, GRAY)
                self.buildings.append(building)
        
        # Define fixed positions for victims
        victim_positions = [
        (3, 4), (12, 4), (3, 10), (12, 10),  # Original victims
        # Add more victims:
        (14, 5), (5, 5)
    
    ]
        self.total_victims = len(victim_positions)
        
        # Create victims at fixed positions
        for x, y in victim_positions:
            if 0 <= x < self.grid_width and 0 <= y < self.grid_height:
                self.grid[x][y] = EntityType.VICTIM
                victim = Entity(x, y, EntityType.VICTIM, RED)
                self.victims.append(victim)
        
        # Define fixed positions for hospitals
        hospital_positions = [(1, 1), (17, 1), (1, 13), (17, 13)]
        
        # Create hospitals at fixed positions
        for x, y in hospital_positions:
            if 0 <= x < self.grid_width and 0 <= y < self.grid_height:
                self.grid[x][y] = EntityType.HOSPITAL
                hospital = Entity(x, y, EntityType.HOSPITAL, YELLOW)
                self.hospitals.append(hospital)
        
        # Fixed position for player and NPC
        player_pos = (2, 5)
        npc_pos = (13, 5)
        
        # Create player
        self.grid[player_pos[0]][player_pos[1]] = EntityType.PLAYER
        self.player = Entity(player_pos[0], player_pos[1], EntityType.PLAYER, GREEN)
        
        # Create NPC
        self.grid[npc_pos[0]][npc_pos[1]] = EntityType.NPC
        self.npc = Entity(npc_pos[0], npc_pos[1], EntityType.NPC, BLUE)
        # Set initial state for NPC
        self.npc.state = EntityState.GOING_TO_VICTIM

    def get_nearest_victim(self, entity):
        if not self.victims:
            return None
        
        nearest_victim = None
        nearest_distance = float('inf')
        
        for victim in self.victims:
            distance = abs(entity.x - victim.x) + abs(entity.y - victim.y)  # Manhattan distance
            if distance < nearest_distance:
                nearest_distance = distance
                nearest_victim = victim
        
        return nearest_victim
    
    def get_nearest_hospital(self, entity):
        nearest_hospital = None
        nearest_distance = float('inf')
        
        for hospital in self.hospitals:
            distance = abs(entity.x - hospital.x) + abs(entity.y - hospital.y)  # Manhattan distance
            if distance < nearest_distance:
                nearest_distance = distance
                nearest_hospital = hospital
        
        return nearest_hospital

    
    def bfs_pathfinding(self, start_x, start_y, target_x, target_y):
        """
        Breadth-First Search pathfinding algorithm to find shortest path
        Returns a list of (x, y) tuples representing the path from start to target
        """
        # Queue of positions to check, starting with the initial position
        queue = [(start_x, start_y)]
        # Dictionary to keep track of visited positions and their parents
        visited = {(start_x, start_y): None}
        
        # Possible movement directions: up, right, down, left
        directions = [(0, -1), (1, 0), (0, 1), (-1, 0)]
        
        while queue:
            current_x, current_y = queue.pop(0)
            
            # If we've reached the target, reconstruct and return the path
            if current_x == target_x and current_y == target_y:
                path = []
                current_pos = (current_x, current_y)
                
                # Reconstruct path from target to start
                while current_pos != (start_x, start_y):
                    path.append(current_pos)
                    current_pos = visited[current_pos]
                    
                # Reverse to get path from start to target
                path.reverse()
                return path
            
            # Check all four adjacent cells
            for dx, dy in directions:
                next_x, next_y = current_x + dx, current_y + dy
                
                # Check if the next position is valid and not visited
                if (0 <= next_x < self.grid_width and 
                    0 <= next_y < self.grid_height and 
                    self.grid[next_x][next_y] != EntityType.BUILDING and
                    (next_x, next_y) not in visited):
                    
                    # Add to queue and mark as visited with parent reference
                    queue.append((next_x, next_y))
                    visited[(next_x, next_y)] = (current_x, current_y)
        
        # If no path is found, return empty list
        return []

    def update_npc(self):
        npc = self.npc
        
        # If NPC is carrying a victim, go to nearest hospital
        if npc.carrying_victim:
            npc.state = EntityState.GOING_TO_HOSPITAL
            nearest_hospital = self.get_nearest_hospital(npc)
            
            if nearest_hospital:
                # If path is empty or we need a new path, calculate it
                if not npc.path or npc.target != (nearest_hospital.x, nearest_hospital.y):
                    npc.target = (nearest_hospital.x, nearest_hospital.y)
                    npc.path = self.bfs_pathfinding(npc.x, npc.y, nearest_hospital.x, nearest_hospital.y)
                
                # If we have a path, follow it using seek behavior
                if npc.path:
                    # Get the next waypoint
                    next_waypoint = npc.path[0]
                    
                    # Apply seek behavior
                    npc.seek(next_waypoint)
                    
                    # Update position based on velocity
                    new_pos = npc.update_position()
                    if new_pos:
                        new_x, new_y = new_pos
                        
                        # Check if the move is valid (not a building or player)
                        if (0 <= new_x < self.grid_width and 
                            0 <= new_y < self.grid_height and 
                            self.grid[new_x][new_y] != EntityType.BUILDING and
                            self.grid[new_x][new_y] != EntityType.PLAYER):
                            
                            # Remember if current position is a hospital before moving
                            is_current_hospital = False
                            for hospital in self.hospitals:
                                if hospital.x == npc.x and hospital.y == npc.y:
                                    is_current_hospital = True
                                    break
                            
                            # Update grid - clear old position or restore hospital
                            if is_current_hospital:
                                self.grid[npc.x][npc.y] = EntityType.HOSPITAL
                            else:
                                self.grid[npc.x][npc.y] = EntityType.EMPTY
                            
                            # Update NPC position
                            npc.x, npc.y = new_x, new_y
                            
                            # If we've reached the next waypoint, remove it from the path
                            if npc.x == npc.path[0][0] and npc.y == npc.path[0][1]:
                                npc.path.pop(0)
                            
                            # Check if reached hospital - ONLY do this check once
                            is_at_hospital = False
                            for hospital in self.hospitals:
                                if hospital.x == npc.x and hospital.y == npc.y:
                                    is_at_hospital = True
                                    break
                            
                            if is_at_hospital and npc.carrying_victim:
                                npc.carrying_victim = False
                                self.rescued_count += 1
                                npc.path = []  # Clear the path
                                npc.state = EntityState.GOING_TO_VICTIM
                            
                            # Update grid with new NPC position
                            self.grid[npc.x][npc.y] = EntityType.NPC
        else:
            # Set state to looking for victims
            npc.state = EntityState.GOING_TO_VICTIM
            
            # Find nearest victim and move towards it
            nearest_victim = self.get_nearest_victim(npc)
            
            if nearest_victim:
                # If path is empty or we need a new path, calculate it
                if not npc.path or npc.target != (nearest_victim.x, nearest_victim.y):
                    npc.target = (nearest_victim.x, nearest_victim.y)
                    npc.path = self.bfs_pathfinding(npc.x, npc.y, nearest_victim.x, nearest_victim.y)
                
                # If we have a path, follow it using seek behavior
                if npc.path:
                    # Get the next waypoint
                    next_waypoint = npc.path[0]
                    
                    # Apply seek behavior
                    npc.seek(next_waypoint)
                    
                    # Update physical position in grid
                    new_pos = npc.update_position()
                    if new_pos:
                        new_x, new_y = new_pos
                        
                        # Check if the move is valid (not a building or player)
                        if (0 <= new_x < self.grid_width and 
                            0 <= new_y < self.grid_height and 
                            self.grid[new_x][new_y] != EntityType.BUILDING and
                            self.grid[new_x][new_y] != EntityType.PLAYER):
                            
                            # Update grid
                            self.grid[npc.x][npc.y] = EntityType.EMPTY
                            npc.x, npc.y = new_x, new_y
                            
                            # If we've reached the next waypoint, remove it from the path
                            if npc.x == npc.path[0][0] and npc.y == npc.path[0][1]:
                                npc.path.pop(0)
                            
                            # Check if reached victim
                            if not npc.carrying_victim:
                                for i, victim in enumerate(self.victims):
                                    if victim.x == npc.x and victim.y == npc.y:
                                        npc.carrying_victim = True
                                        self.victims.pop(i)
                                        npc.path = []  # Clear the path
                                        npc.state = EntityState.GOING_TO_HOSPITAL
                                        break
                            
                            self.grid[npc.x][npc.y] = EntityType.NPC
        
    def move_player(self, dx, dy):
        # Calculate new position
        new_x = self.player.x + dx
        new_y = self.player.y + dy
        
        # Check if the new position is valid
        if (0 <= new_x < self.grid_width and 0 <= new_y < self.grid_height and
            self.grid[new_x][new_y] != EntityType.BUILDING and
            self.grid[new_x][new_y] != EntityType.NPC):
            
            # Check if destination is a hospital - use the hospitals list for consistency
            is_destination_hospital = False
            for hospital in self.hospitals:
                if hospital.x == new_x and hospital.y == new_y:
                    is_destination_hospital = True
                    break
            
            # Check if current position is a hospital
            is_current_hospital = False
            for hospital in self.hospitals:
                if hospital.x == self.player.x and hospital.y == self.player.y:
                    is_current_hospital = True
                    break
            
            # Update grid - restore hospital if player is leaving one
            if is_current_hospital:
                self.grid[self.player.x][self.player.y] = EntityType.HOSPITAL
            else:
                self.grid[self.player.x][self.player.y] = EntityType.EMPTY
            
            # Update player position
            self.player.x, self.player.y = new_x, new_y
            
            # Check if player reached a victim
            if not self.player.carrying_victim:
                for i, victim in enumerate(self.victims):
                    if victim.x == self.player.x and victim.y == self.player.y:
                        self.player.carrying_victim = True
                        self.victims.pop(i)
                        break
            
            # Check if player reached a hospital with a victim
            if self.player.carrying_victim and is_destination_hospital:
                self.player.carrying_victim = False
                self.rescued_count += 1
            
            # Update grid with new player position
            self.grid[self.player.x][self.player.y] = EntityType.PLAYER
    
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            
            # Keyboard control for player
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    self.move_player(0, -1)
                elif event.key == pygame.K_DOWN:
                    self.move_player(0, 1)
                elif event.key == pygame.K_LEFT:
                    self.move_player(-1, 0)
                elif event.key == pygame.K_RIGHT:
                    self.move_player(1, 0)
    
    def update(self):
        # Update NPC
        self.update_npc()
        
        # Check if game is over (all victims rescued)
        if self.rescued_count == self.total_victims:
            print("All victims rescued! Game over.")
            self.running = False
    
    def draw(self):
        # Fill screen with black
        self.screen.fill(BLACK)
        
        # Draw grid lines
        for x in range(0, SCREEN_WIDTH, GRID_SIZE):
            pygame.draw.line(self.screen, (50, 50, 50), (x, 0), (x, SCREEN_HEIGHT))
        for y in range(0, SCREEN_HEIGHT, GRID_SIZE):
            pygame.draw.line(self.screen, (50, 50, 50), (0, y), (SCREEN_WIDTH, y))
        
        # Draw buildings
        for building in self.buildings:
            building.draw(self.screen)
        
        # Draw hospitals
        for hospital in self.hospitals:
            hospital.draw(self.screen)
        
        # Draw victims
        for victim in self.victims:
            victim.draw(self.screen)
        if self.npc.path:
            path_color = (100, 200, 255)  # Light blue color for path
            
            # Draw lines connecting path points
            start_x, start_y = self.npc.x, self.npc.y
            
            # Draw all path segments
            for point in self.npc.path:
                end_x, end_y = point
                
                # Draw path point (small circle)
                pygame.draw.circle(
                    self.screen, 
                    path_color,
                    (end_x * GRID_SIZE + GRID_SIZE//2, end_y * GRID_SIZE + GRID_SIZE//2),
                    5
                )
                
                # Draw line from previous point to this point
                pygame.draw.line(
                    self.screen,
                    path_color,
                    (start_x * GRID_SIZE + GRID_SIZE//2, start_y * GRID_SIZE + GRID_SIZE//2),
                    (end_x * GRID_SIZE + GRID_SIZE//2, end_y * GRID_SIZE + GRID_SIZE//2),
                    2
                )
                
                # Update start for next segment
                start_x, start_y = end_x, end_y
        # Draw NPC
        self.npc.draw(self.screen)
        
        # Draw player
        self.player.draw(self.screen)
        
        # Display rescue counter
        font = pygame.font.SysFont(None, 30)
        text = font.render(f"Rescued: {self.rescued_count}/{self.total_victims}", True, WHITE)
        self.screen.blit(text, (10, 10))
        
        # Update display
        pygame.display.flip()
    
    def run(self):
        while self.running:
            self.clock.tick(8)  # Reduced FPS for easier control
            self.handle_events()
            self.update()
            self.draw()
        
        # Show game over message
        if self.rescued_count == self.total_victims:
            self.screen.fill(BLACK)
            font = pygame.font.SysFont(None, 48)
            game_over_text = font.render("All Victims Rescued!", True, WHITE)
            text_rect = game_over_text.get_rect(center=(SCREEN_WIDTH/2, SCREEN_HEIGHT/2))
            self.screen.blit(game_over_text, text_rect)
            
            pygame.display.flip()
            # Wait for a few seconds before quitting
            pygame.time.wait(3000)
        
        pygame.quit()

# Main function
def main():
    game = Game()
    game.run()

if __name__ == "__main__":
    main()