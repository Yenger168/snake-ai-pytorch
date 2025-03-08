import pygame
import random
from enum import Enum
from collections import namedtuple
import numpy as np
import math

pygame.init()
font = pygame.font.Font('arial.ttf', 25)
#font = pygame.font.SysFont('arial', 25)

class Direction(Enum):
    RIGHT = 1
    LEFT = 2
    UP = 3
    DOWN = 4

Point = namedtuple('Point', 'x, y')

# rgb colors
WHITE = (255, 255, 255)
RED = (200,0,0)
GREEN = (0,200,0)
YELLOW = (200, 200, 0)
ORANGE = (150, 150, 0)
BLUE1 = (0, 0, 255)
BLUE2 = (0, 100, 255)
BLACK = (0,0,0)

BLOCK_SIZE = 20
SPEED = 80000
class SnakeGameAI:

    def __init__(self, w=640, h=480):
        self.w = w
        self.h = h
        self.record = 0
        self.time_out_count = 0
        self.hit_bound_count = 0
        self.self_collision_count = 0
        self.turn_history = []
        self.history_positions = []
        self.time_out_score = 0
        self.hit_bound_score = 0
        self.self_collision_score = 0
        self.explored_points_set = set()

        # init display
        self.display = pygame.display.set_mode((self.w, self.h))
        pygame.display.set_caption('Snake')
        self.clock = pygame.time.Clock()
        self.reset()


    def reset(self):
        # init game state
        self.direction = Direction.RIGHT

        self.head = Point(self.w/2, self.h/2)
        self.snake = [self.head,
                      Point(self.head.x-BLOCK_SIZE, self.head.y),
                      Point(self.head.x-(2*BLOCK_SIZE), self.head.y)]

        self.score = 0
        self.food = None
        self.surrounding1 = None
        self.surrounding2 = None
        self.surrounding3 = None
        self._place_food()
        self.frame_iteration = 0


    def _place_food(self):
        x = random.randint(0, (self.w-BLOCK_SIZE )//BLOCK_SIZE )*BLOCK_SIZE
        y = random.randint(0, (self.h-BLOCK_SIZE )//BLOCK_SIZE )*BLOCK_SIZE
        self.food = Point(x, y)
        
        # surrounding1:
        self.surrounding1 = [Point(x + dx, y + dy) for dx in (-20, 20) for dy in (-20, 20) if not (dx == 0 and dy == 0)]

        # surrounding2:
        self.surrounding2 = [Point(x + dx, y + dy) for dx in (-40, -20, 20, 40) for dy in (-40, -20, 20, 40)
                            if abs(dx) == 40 or abs(dy) == 40]

        # surrounding3:
        self.surrounding3 = [Point(x + dx, y + dy) for dx in (-60, -40, -20, 20, 40, 60) 
                         for dy in (-60, -40, -20, 20, 40, 60) if abs(dx) == 60 or abs(dy) == 60]
        
        if self.food in self.snake:
            self._place_food()


    def play_step(self, action):
        self.frame_iteration += 1
        # 1. collect user input
        next_head_position = self.get_next_head_position(self.head, self.direction, action)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                quit()
        if next_head_position not in self.explored_points_set:
            reward = 5  
            self.explored_points_set.add(next_head_position)
        else:
            reward = 0
        
        # 2. move
        turn_penalty = self._move(action) # 
        avoidance_reward = self.check_self_avoidance(action)
        self.snake.insert(0, self.head)
        self.history_positions.append(self.head)
        if len(self.history_positions) > 50:  
            self.history_positions.pop(0)
        
        repeat_penalty = self.check_repeating_patterns()
        # 3. check if game over
        #reward = 0
        reward += turn_penalty
        reward += avoidance_reward
        reward += repeat_penalty
        game_over = False
        
        distance = self.distance(self.head, self.food)
        if distance != 0:
            reward += 10 / distance
        else:
            reward = 10  
        
        if self.frame_iteration > 100*len(self.snake):
            game_over = True
            self.time_out_count += 1
            self.time_out_score += self.score
            # time_out
            reward = -10
            return reward, game_over, self.score

        if self.is_collision(self.head): 
            game_over = True
            # hit wall
            if (self.head.x > self.w - BLOCK_SIZE or self.head.x < 0 or 
                self.head.y > self.h - BLOCK_SIZE or self.head.y < 0):
                self.hit_bound_count += 1
                self.hit_bound_score += self.score
                reward = -10  
            # hit self
            if self.head in self.snake[1:]:
                self.self_collision_count += 1
                self.self_collision_score += self.score
                reward = -10  
            return reward, game_over, self.score
        
        # 3.5 check if the snake is close to food
        # if self.head in self.surrounding1:
        #     reward += 7
        # elif self.head in self.surrounding2:
        #     reward += 5
        # elif self.head in self.surrounding3:
        #     reward += 3
        # #else:
        # #      reward = -1
            
        # 4. place new food or just move
        if self.head == self.food:
            self.score += 1
            if self.score % 5 == 0:
                reward += 5
            #reward = 10
            if self.score > self.record:
                self.record = self.score  #update record
                reward += 50
            self._place_food()
        else:
            self.snake.pop()
        
        if self.head != self.food:
            reward -= 0.1 
        reward += 0.5
        
        moving_towards_food = ((self.food.x - self.head.x) * (self.head.x - self.snake[1].x) > 0 or
                           (self.food.y - self.head.y) * (self.head.y - self.snake[1].y) > 0)
        if moving_towards_food:
            reward += 2
        else:
            reward -= 2
    
        # 5. update ui and clock
        self._update_ui()
        self.clock.tick(SPEED)
        # 6. return game over and score
        return reward, game_over, self.score

    def distance(self, p1, p2):
        return math.sqrt((p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2)

    def is_collision(self, pt=None):
        if pt is None:
            pt = self.head
        # hits boundary
        if pt.x > self.w - BLOCK_SIZE or pt.x < 0 or pt.y > self.h - BLOCK_SIZE or pt.y < 0:
            return True
        # hits itself
        if pt in self.snake[1:]:
            return True

        return False


    def _update_ui(self):
        self.display.fill(BLACK)

        # snake body
        for pt in self.snake[1:]:
            pygame.draw.rect(self.display, BLUE1, pygame.Rect(pt.x, pt.y, BLOCK_SIZE, BLOCK_SIZE))
            pygame.draw.rect(self.display, BLUE2, pygame.Rect(pt.x + 4, pt.y + 4, 12, 12))

        # snake head = white
        head = self.snake[0]
        pygame.draw.rect(self.display, WHITE, pygame.Rect(head.x, head.y, BLOCK_SIZE, BLOCK_SIZE))

        # food
        pygame.draw.rect(self.display, RED, pygame.Rect(self.food.x, self.food.y, BLOCK_SIZE, BLOCK_SIZE))
        
        
        # for dx in [-20, 0, 20]:
        #     for dy in [-20, 0, 20]:
        #         if dx == 0 and dy == 0:
        #             continue  
        #         pygame.draw.rect(self.display, GREEN, pygame.Rect(self.food.x + dx, self.food.y + dy, BLOCK_SIZE, BLOCK_SIZE))

        # # yellow
        # for dx in [-40, -20, 0, 20, 40]:
        #     for dy in [-40, -20, 0, 20, 40]:
        #         if abs(dx) != 40 and abs(dy) != 40:
        #             continue  
        #         pygame.draw.rect(self.display, YELLOW, pygame.Rect(self.food.x + dx, self.food.y + dy, BLOCK_SIZE, BLOCK_SIZE))
                
        # for dx in [-60, -40,-20, 0, 20, 40, 60]:
        #     for dy in [-60, -40,-20, 0, 20, 40, 60]:
        #         if abs(dx) == 60 or abs(dy) == 60:
        #             pygame.draw.rect(self.display, ORANGE, pygame.Rect(self.food.x + dx, self.food.y + dy, BLOCK_SIZE, BLOCK_SIZE))

        text = font.render("Score: " + str(self.score), True, WHITE)
        self.display.blit(text, [0, 0])
        pygame.display.flip()


    def _move(self, action):
        # [straight, right, left]

        clock_wise = [Direction.RIGHT, Direction.DOWN, Direction.LEFT, Direction.UP]
        idx = clock_wise.index(self.direction)
        turn_penalty = 0
        
        if np.array_equal(action, [1, 0, 0]):
            new_dir = clock_wise[idx] # no change
            self.turn_history.append('S')  # record straight
        elif np.array_equal(action, [0, 1, 0]):
            next_idx = (idx + 1) % 4
            new_dir = clock_wise[next_idx] # right turn r -> d -> l -> u
            self.turn_history.append('R')  # record right
        else: # [0, 0, 1]
            next_idx = (idx - 1) % 4
            new_dir = clock_wise[next_idx] # left turn r -> u -> l -> d
            self.turn_history.append('L')  # record left
        
        if len(self.turn_history) >= 3 and self.turn_history[-3:] in (['R', 'R', 'R'], ['L', 'L', 'L']):
            turn_penalty = -10  # punish for 3 turns
            self.turn_history = []
        elif len(self.turn_history) >= 4 and self.turn_history[-4:] in (['L', 'S', 'S', 'R'], ['R', 'S', 'S', 'L']):
            turn_penalty = 5  
            self.turn_history = []  
        
        self.direction = new_dir

        x = self.head.x
        y = self.head.y
        if self.direction == Direction.RIGHT:
            x += BLOCK_SIZE
        elif self.direction == Direction.LEFT:
            x -= BLOCK_SIZE
        elif self.direction == Direction.DOWN:
            y += BLOCK_SIZE
        elif self.direction == Direction.UP:
            y -= BLOCK_SIZE

        self.head = Point(x, y)
        return turn_penalty
    
    
    def get_next_head_position(self, current_position, current_direction, action):
        new_direction = self.get_new_direction(current_direction, action)
        x, y = current_position.x, current_position.y
        if new_direction == Direction.RIGHT:
            x += BLOCK_SIZE
        elif new_direction == Direction.LEFT:
            x -= BLOCK_SIZE
        elif new_direction == Direction.DOWN:
            y += BLOCK_SIZE
        elif new_direction == Direction.UP:
            y -= BLOCK_SIZE
        return Point(x, y)

    def get_new_direction(self, current_direction, action):
        clock_wise = [Direction.RIGHT, Direction.DOWN, Direction.LEFT, Direction.UP]
        idx = clock_wise.index(current_direction)
        if np.array_equal(action, [1, 0, 0]):
            # no change
            new_direction = clock_wise[idx]
        elif np.array_equal(action, [0, 1, 0]):
            # right turn
            next_idx = (idx + 1) % 4
            new_direction = clock_wise[next_idx]
        else: # [0, 0, 1]
            # left turn
            next_idx = (idx - 1) % 4
            new_direction = clock_wise[next_idx]
        return new_direction
    
    def check_self_avoidance(self, action):
        next_head_position = self.get_next_head_position(self.head, self.direction, action)
        for point in self.snake[1:]:
            if next_head_position == point:
                return -5  
        return 1 
    
    def check_repeating_patterns(self):
        if len(self.history_positions) < 25:
            return 0  
        recent_history = self.history_positions[-25:]
        if len(set(recent_history)) < 15:  
            return -20
        return 0