import pygame
import asyncio

# --- Game States ---
GAME_STATE_START = "start"
GAME_STATE_PLAYING = "playing"
GAME_STATE_GAME_OVER = "game_over"

# --- Pygame Initialization (Moved outside main async loop) ---
# Initialize Pygame modules once before the asyncio event loop starts.
pygame.init()
screen = pygame.display.set_mode((1280, 720))
screen_rect = screen.get_rect()
pygame.display.set_caption("Doors of Perception")
clock = pygame.time.Clock()
pygame.font.init()
my_font = pygame.font.SysFont("arial", 30)

# --- Global Game Object Variables ---
# These variables will hold our sprite groups and scoreboard instance.
# They are accessed and modified by functions like initialise_game_objects and main.
scoreboard = None
player_group = None
portals_group = None
monsters_group = None
coins_group = None
walls_group = None
game_over_reason_message = "" # To store the reason for the game ending

# --- Define classes for visual elements ---
# These classes inherit from Pygame's built-in sprite class.
# The sprite class allows for simpler and more efficient collision detection.

class Wall(pygame.sprite.Sprite):
    def __init__(self, start_x: int, start_y: int, width: int, height):
        pygame.sprite.Sprite.__init__(self)
        # Use pygame.Rect for collision detection
        self.rect = pygame.Rect(start_x, start_y, width, height)

    def draw(self):
        # Draw directly using self.rect
        pygame.draw.rect(
            screen,
            "darkorange4",
            self.rect,
            10,
        )

class Monster(pygame.sprite.Sprite):
    def __init__(self, image: str, position: tuple, speed: float, direction: str):
        pygame.sprite.Sprite.__init__(self)
        # Load image once outside the class or handle loading errors if they occur later
        self.image = pygame.image.load(image)
        self.rect = self.image.get_rect(center=position)
        self.speed = speed
        self.direction = direction
        # Store original speed/direction for potential reset if needed (not used in this version, but good practice)
        # self._original_speed = speed
        # self._original_direction = direction


    # Update method now takes the state setter function and handles axis-by-axis wall collision
    def update(self, player: pygame.sprite.GroupSingle, walls: pygame.sprite.Group, portals: pygame.sprite.Group, current_game_state_setter):

        # --- Collision with Player (Check first as it can end game) ---
        # Check collision against the single player sprite. dokill=False means player sprite isn't removed yet.
        if pygame.sprite.spritecollide(player.sprite, pygame.sprite.GroupSingle(self), False):
            self.speed = 0 # Stop the monster movement immediately
            # Signal game over state change
            current_game_state_setter(GAME_STATE_GAME_OVER, "You were discombobulated by a ghost!")
            return # Stop further updates for this monster in this frame if game over

        # If game is not over, proceed with movement and wall collision checks

        # --- Movement and Wall Collision (Handle X and Y separately to prevent tunneling) ---
        # Store original position before attempting movement
        original_x = self.rect.x
        original_y = self.rect.y

        # Attempt horizontal movement
        if self.direction == "horizontal":
            self.rect.x += self.speed

            # Check horizontal collision with walls after moving X
            if pygame.sprite.spritecollideany(self, walls):
                self.rect.x = original_x # Revert X movement if collided
                self.speed = -self.speed # Reverse horizontal direction

        # Attempt vertical movement
        elif self.direction == "vertical":
            self.rect.y += self.speed

             # Check vertical collision with walls after moving Y
            if pygame.sprite.spritecollideany(self, walls):
                self.rect.y = original_y # Revert Y movement if collided
                self.speed = -self.speed # Reverse vertical direction

        # --- Collision with Portals ---
        # Check collision with portals (kills monster if true). dokill=True removes portal sprite.
        # Note: Only the monster dies here based on original logic. If portal should die, add self.kill() in Portal.update
        # This check happens *after* movement, so the monster moves into the portal in the frame it hits.
        if pygame.sprite.spritecollide(self, portals, True):
            global scoreboard
            if scoreboard: # Ensure scoreboard exists before accessing
                scoreboard.ghost_busted()
            self.kill() # Remove the monster sprite


class Player(pygame.sprite.Sprite):
    def __init__(self, image: str, position: tuple, speed: int):
        pygame.sprite.Sprite.__init__(self)
        # Load image once outside the class or handle loading errors if they occur later
        self.image = pygame.image.load(image)
        self.rect = self.image.get_rect(center=position)
        self.speed = speed
        self.original_position = position # Store initial position for restart


    # Update method now takes the state setter function and handles axis-by-axis wall collision
    def update(self, keys, walls: pygame.sprite.Group, coins: pygame.sprite.Group, current_game_state_setter):

        # --- Check for Exit (Can end game) ---
        # Check if the player's right edge has crossed the exit line
        if self.rect.right > 1050:
            # Signal game over state change
            current_game_state_setter(GAME_STATE_GAME_OVER, "You made it out alive!")
            return # Stop further updates if game over

        # If game is not over, proceed with movement and collision checks

        # --- Movement and Wall Collision (Handle X and Y separately to prevent tunneling) ---
        # Store original position before attempting movement
        original_x = self.rect.x
        original_y = self.rect.y

        # Attempt horizontal movement based on input
        if keys[pygame.K_LEFT]:
            self.rect.x -= self.speed
        elif keys[pygame.K_RIGHT]:
            self.rect.x += self.speed

        # Check horizontal collision with walls after moving X
        if pygame.sprite.spritecollideany(self, walls):
             self.rect.x = original_x # Revert X movement if collided

        # Attempt vertical movement based on input
        if keys[pygame.K_UP]:
            self.rect.y -= self.speed
        elif keys[pygame.K_DOWN]:
            self.rect.y += self.speed

         # Check vertical collision with walls after moving Y
        if pygame.sprite.spritecollideany(self, walls):
             self.rect.y = original_y # Revert Y movement if collided


        # --- Collision with Coins ---
        # Check collision with coins (kills coin if true). dokill=True removes coin sprite.
        if pygame.sprite.spritecollide(self, coins, True):
            global scoreboard
            if scoreboard: # Ensure scoreboard exists before accessing
                scoreboard.coin_collected()


class Coin(pygame.sprite.Sprite):
    def __init__(self, image: str, position: tuple, speed: int = 0): # Set default speed to 0 as it's unused
        pygame.sprite.Sprite.__init__(self)
        # Load image once outside the class or handle loading errors if they occur later
        self.image = pygame.image.load(image)
        self.rect = self.image.get_rect(center=position)
        # self.speed = speed # Speed parameter seems unused in Coin class


    # Coin update method is not strictly needed if it only handles collection via Player's update.
    # Can keep an empty update or remove if unused.
    # def update(self, player):
    #    pass


# Portal class interacts with monsters and scoreboard.
# It needs access to the scoreboard instance.
class Portal(pygame.sprite.Sprite):
    def __init__(self, image: str, position: tuple, speed: int = 0): # Set default speed to 0 as it's unused
        pygame.sprite.Sprite.__init__(self)
        # Load image once outside the class or handle loading errors if they occur later
        self.image = pygame.image.load(image)
        self.rect = self.image.get_rect(center=position)
        # self.speed = speed # Speed parameter seems unused in Portal class

        global scoreboard
        if scoreboard: # Ensure scoreboard exists before accessing
            scoreboard.new_portal() # Decrement portal count when a portal is created

    # Portal update method checks collision with monsters
    def update(self, monsters: pygame.sprite.Group):
        # Check collision with monsters (kills monster if true). dokill=True removes monster sprite.
        # This check happens *after* monster movement in the game loop.
        if pygame.sprite.spritecollide(self, monsters, True):
            global scoreboard
            if scoreboard: # Ensure scoreboard exists before accessing
                scoreboard.ghost_busted()
            # The portal itself is NOT killed here based on your original code.
            # If you want portals to disappear after a monster goes through, add self.kill() here.


# Scoreboard class holds counters (coins collected, time left etc) and methods to update them.
# Also checks time remaining and uses the state setter to signal game over.
class Scoreboard:
    def __init__(self):
        self.coins_collected = 0
        self.time_left = 100.00 # Starting time
        self.ghosts_busted = 0
        self.portals_remaining = 5 # Starting portals
        self.points = 0
        # Scoreboard text will be generated in draw, not stored permanently


    def new_portal(self):
        self.portals_remaining -= 1

    def ghost_busted(self):
        self.ghosts_busted += 1

    def coin_collected(self):
        self.coins_collected += 1

    # Check if time is up
    def is_time_up(self):
        return self.time_left <= 0

    # Update method now takes the state setter function to signal game over on time out
    def update(self, current_game_state_setter):
        # Decrease time left by the fraction of a second per frame (1/60th at 60 FPS)
        self.time_left -= 1 / 60
        # Recalculate points
        self.points = self.coins_collected * 100 + self.ghosts_busted * 50

        # Check if time is up and signal game over state change
        if self.is_time_up():
            current_game_state_setter(GAME_STATE_GAME_OVER, "You ran out of time!")
            return # Stop update if game over


    # Draw method renders the scoreboard text and exit marker
    def draw(self):
        # Generate text strings in draw, using current scoreboard stats
        scoreboard_text_lines = [
            (my_font.render(f"Coins: {self.coins_collected}", 1, (0, 0, 0))),
            (my_font.render(f"Time: {max(0, self.time_left):.0f}", 1, (0, 0, 0))), # Display time, not less than 0
            (my_font.render(f"Exorcised: {self.ghosts_busted}", 1, (0, 0, 0))),
            (my_font.render(f"Portals: {self.portals_remaining}", 1, (0, 0, 0))),
            (my_font.render(f"Score: {self.points}", 1, (0, 0, 0))),
        ]
        text_y_position = 100
        keys_text=f"<Q> Quit     <R> Restart     <ARROW KEYS> Move     <SPACEBAR> Portal" # Instructions

        # Draw scoreboard lines
        for line in scoreboard_text_lines:
            screen.blit(line, (1060, text_y_position))
            text_y_position += 50

        # Draw exit marker
        screen.blit((my_font.render(f"EXIT---->", 1, (255, 0, 0))), (980, 630))
        # Draw instructions
        screen.blit((my_font.render(keys_text,1,(0, 0, 0),)),(25, 10),)


# --- Initialisation function ---
# This function resets all game objects and variables to their starting state.
def initialise_game_objects():
    """Resets all game objects and variables for a new game."""
    global scoreboard, player_group, portals_group, monsters_group, coins_group, walls_group
    global game_over_reason_message # Reset game over message

    scoreboard = Scoreboard() # Create a new scoreboard instance

    # Create a new player sprite and add to a GroupSingle
    player_sprite = Player("robot.png", (100, 200), 3)
    player_group = pygame.sprite.GroupSingle(player_sprite)

    # Create an empty group for portals (player adds them during gameplay)
    portals_group = pygame.sprite.Group()

    # Create and populate the monsters group
    monsters_group = pygame.sprite.Group(
        *[
            Monster("monster.png", (220, 100), 2.3, "horizontal"),
            Monster("monster.png", (200, 400), 2.1, "vertical"),
            Monster("monster.png", (300, 450), 1.9, "horizontal"),
            Monster("monster.png", (400, 225), 2, "vertical"),
            Monster("monster.png", (490, 650), 2.2, "horizontal"),
            Monster("monster.png", (500, 200), 2, "vertical"),
            Monster("monster.png", (630, 550), 2.4, "horizontal"),
            Monster("monster.png", (600, 450), 2.1, "vertical"),
            Monster("monster.png", (700, 450), 1.9, "horizontal"),
            Monster("monster.png", (800, 200), 1.9, "horizontal"),
            Monster("monster.png", (900, 300), 2.1, "horizontal"),
            Monster("monster.png", (1000, 625), 2, "vertical"),
        ]
    )

    # Create and populate the coins group
    coins_group = pygame.sprite.Group(
        *[
            Coin("coin.png", (100, 100)), # Using default speed=0
            Coin("coin.png", (100, 535)),
            Coin("coin.png", (100, 625)),
            Coin("coin.png", (200, 200)),
            Coin("coin.png", (200, 505)),
            Coin("coin.png", (200, 625)),
            Coin("coin.png", (300, 100)),
            Coin("coin.png", (300, 200)),
            Coin("coin.png", (300, 415)),
            Coin("coin.png", (300, 625)),
            Coin("coin.png", (400, 335)),
            Coin("coin.png", (400, 425)),
            Coin("coin.png", (500, 200)),
            Coin("coin.png", (500, 100)),
            Coin("coin.png", (500, 425)),
            Coin("coin.png", (500, 625)),
            Coin("coin.png", (600, 415)),
            Coin("coin.png", (600, 525)),
            Coin("coin.png", (700, 200)),
            Coin("coin.png", (800, 200)),
            Coin("coin.png", (800, 425)),
            Coin("coin.png", (800, 535)),
            Coin("coin.png", (900, 325)),
            Coin("coin.png", (900, 425)),
            Coin("coin.png", (900, 625)),
            Coin("coin.png", (1000, 100)),
            Coin("coin.png", (1000, 200)),
            Coin("coin.png", (1000, 425)),
        ]
    )

    # Create and populate the walls group
    walls_group = pygame.sprite.Group(
        *[
            Wall(50, 50, 1000, 5),
            Wall(1050, 50, 5, 550),
            Wall(50, 700, 1000, 5),
            Wall(50, 50, 5, 650),
            Wall(150, 150, 5, 550),
            Wall(250, 150, 700, 5),
            Wall(250, 150, 5, 250),
            Wall(250, 500, 5, 100),
            Wall(250, 600, 100, 5),
            Wall(350, 500, 5, 100),
            Wall(350, 250, 5, 150),
            Wall(450, 150, 5, 450),
            Wall(450, 600, 300, 5),
            Wall(550, 500, 300, 5),
            Wall(850, 500, 5, 200),
            Wall(550, 150, 5, 250),
            Wall(650, 250, 5, 250),
            Wall(750, 150, 5, 250),
            Wall(850, 250, 5, 150),
            Wall(850, 250, 200, 5),
            Wall(950, 400, 5, 200),
        ]
    )

    game_over_reason_message = "" # Clear any previous game over message


# --- Drawing functions for different states ---
# These functions are called from the main loop based on the current game state.

def draw_start_screen():
    """Draws the start screen content."""
    strings = [
        my_font.render(f'Welcome to "The Doors Of Perception"!', 1, (0, 0, 0)),
        my_font.render(f"You have foolishly become trapped in a dangerous dungeon.", 1, (0, 0, 0)),
        my_font.render(f"These damned monsters are out to get you.", 1, (0, 0, 0)),
        my_font.render(f"Thankfully you have a few Pocket-Portals(TM) to get you out of any tight corners!", 1, (0, 0, 0)),
        my_font.render(f"If a monster stumbles into a portal, it will be immediately exorcised.", 1, (0, 0, 0)),
        my_font.render(f"Who knows... you might find a bit of treasure lying around down here.", 1, (0, 0, 0)),
        my_font.render(f"It might be a worthwhile trip after all!", 1, (0, 0, 0)),
        my_font.render(f"Remember though, you only have so long before the dank air runs out...", 1, (0, 0, 0)),
        my_font.render(f"", 1, (0, 0, 0)),
        my_font.render(f'Press "Q" to quit or "R" to restart at any time.', 1, (0, 0, 0)),
        my_font.render(f"<ARROW KEYS> move you around, <SPACEBAR> to drop a Pocket-Portal!", 1, (0, 0, 0)),
        my_font.render(f"<SPACEBAR> to begin game.", 1, (0, 0, 0)),
    ]
    string_y = 100
    screen.fill("burlywood") # Fill background
    for string in strings:
        string_x = screen.get_width() / 2 - string.get_width() / 2
        screen.blit(string, (string_x, string_y))
        string_y += 50
    pygame.display.flip() # Update the display


def draw_game_over_screen(reason: str):
    """Draws the game over screen content."""
    # Load images here or load them once globally at the start if preferred
    game_over_monster_img = pygame.image.load("monster.png")
    game_over_player_img = pygame.image.load("robot.png")

    global scoreboard # Need global scoreboard to display final stats
    strings = [
        my_font.render(f"{reason}", 1, (0, 0, 0)),
        my_font.render(f" ", 1, (0, 0, 0)),
        my_font.render(f"Ghosts exorcised: {scoreboard.ghosts_busted}", 1, (0, 0, 0)),
        my_font.render(f"Fortune amassed: {scoreboard.coins_collected}", 1, (0, 0, 0)),
        my_font.render(f" ", 1, (0, 0, 0)),
        my_font.render(f"You reached a high score of: {scoreboard.points}", 1, (0, 0, 0)),
        my_font.render(f" ", 1, (0, 0, 0)),
        my_font.render(f'Press "R" to restart or "Q" to quit.', 1, (0, 0, 0)),
    ]
    string_y = 100
    screen.fill("burlywood") # Fill background
    for string in strings:
        string_x = screen.get_width() / 2 - string.get_width() / 2
        screen.blit(string, (string_x, string_y))
        string_y += 50

    # Draw static sprites on the game over screen
    screen.blit(game_over_monster_img, (150, 300))
    screen.blit(game_over_player_img, (1130, 300))

    pygame.display.flip() # Update the display


# --- Main game loop (Asynchronous for Pygbag compatibility) ---
async def main():
    """The main asynchronous game loop."""
    global scoreboard, player_group, portals_group, monsters_group, coins_group, walls_group
    global game_over_reason_message

    # Set initial game state
    current_game_state = GAME_STATE_START

    # Initialize game objects for the first time
    initialise_game_objects()

    # Helper function to change game state and store the reason (especially for game over)
    def set_game_state(new_state, reason=""):
        nonlocal current_game_state # Allows modification of current_game_state variable in main's scope
        global game_over_reason_message # Allows modification of global game_over_reason_message
        print(f"Changing state from {current_game_state} to {new_state}") # Debugging print statement
        current_game_state = new_state
        if new_state == GAME_STATE_GAME_OVER:
            game_over_reason_message = reason # Store the reason when game over is triggered


    running = True
    while running:
        # --- Event Handling ---
        # Process all events in the queue once per frame
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False # Set flag to exit the main loop cleanly

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q:
                    running = False # Set flag to exit the main loop cleanly

                # Handle input based on the current game state
                if current_game_state == GAME_STATE_START:
                    if event.key == pygame.K_SPACE or event.key == pygame.K_r: # Start or Restart from start screen
                        initialise_game_objects() # Re-initialize all game elements for a new game
                        set_game_state(GAME_STATE_PLAYING) # Transition to playing state

                elif current_game_state == GAME_STATE_PLAYING:
                    if event.key == pygame.K_r: # Restart during gameplay
                        initialise_game_objects() # Re-initialize
                        set_game_state(GAME_STATE_PLAYING) # Transition to playing state (or GAME_STATE_START if preferred)
                    if event.key == pygame.K_SPACE:
                        # Player attempts to place a portal
                        if scoreboard.portals_remaining > 0 and player_group.sprite: # Check if player sprite exists
                             # Create portal at player's current center position
                            new_portal = Portal(
                                "door.png",
                                (player_group.sprite.rect.centerx, player_group.sprite.rect.centery),
                                0, # Speed parameter is unused in Portal class
                            )
                            portals_group.add(new_portal)
                            # Note: scoreboard.new_portal() is called inside Portal.__init__()

                elif current_game_state == GAME_STATE_GAME_OVER:
                     if event.key == pygame.K_r: # Restart from game over screen
                        initialise_game_objects() # Re-initialize
                        set_game_state(GAME_STATE_PLAYING) # Transition to playing state (or GAME_STATE_START if preferred)


        # --- Game State Logic (Update and Draw based on state) ---

        if current_game_state == GAME_STATE_START:
            # Only draw the start screen
            draw_start_screen()
            # No game object updates or physics in the start state

        elif current_game_state == GAME_STATE_PLAYING:
            # --- Update objects ---
            # Get the state of all keyboard buttons once per frame
            keys = pygame.key.get_pressed()

            # Update player sprite, passing walls, coins, and the state setter
            player_group.update(keys, walls_group, coins_group, set_game_state)

            # IMPORTANT: Check if the game state changed after updating the player.
            # If the player reached the exit, the state was set to GAME_STATE_GAME_OVER.
            # We should now skip the rest of the updates and drawing for this frame
            # to avoid errors (e.g., updating monster vs a player that is conceptually 'gone').
            if current_game_state == GAME_STATE_PLAYING:
                 # Update monsters, passing player (group), walls, portals, and state setter
                 monsters_group.update(player_group, walls_group, portals_group, set_game_state)

                 # Check game state again after updating monsters
                 if current_game_state == GAME_STATE_PLAYING:
                    # Update coins (assuming coin update doesn't change state or require setters)
                    coins_group.update()
                    # Update portals (pass monsters group for collision check)
                    portals_group.update(monsters_group)
                    # Update scoreboard, passing the state setter (for time out)
                    scoreboard.update(set_game_state)

                    # Check game state one last time after updating scoreboard
                    if current_game_state == GAME_STATE_PLAYING:
                        # --- Render Screen (Only draw if still in playing state) ---
                        screen.fill("burlywood") # Fill background

                        # Draw walls (using custom draw method)
                        for wall in walls_group:
                            wall.draw()

                        # Draw scoreboard
                        scoreboard.draw()

                        # Draw sprite groups (using their built-in draw methods)
                        player_group.draw(screen)
                        coins_group.draw(screen)
                        monsters_group.draw(screen)
                        portals_group.draw(screen)

                        # Update the full display surface
                        pygame.display.flip()

        elif current_game_state == GAME_STATE_GAME_OVER:
            # Only draw the game over screen, using the stored reason message
            draw_game_over_screen(game_over_reason_message)
            # No game object updates or physics in the game over state,
            # input handling is only for restart/quit via the event loop.


        # --- Pygbag/Asyncio Compatibility ---
        # This line is crucial for yielding control back to the browser's event loop.
        # It allows Pygbag to handle browser tasks and keep the application responsive.
        await asyncio.sleep(0)

        # --- Frame Rate Control ---
        # Limit the frame rate to 60 frames per second
        clock.tick(60)

    # --- Game Loop Ends ---
    # Clean up Pygame resources when the main loop finishes
    pygame.quit()
    # In a Pygbag context, asyncio.run will finish after pygame.quit()
    # Do not use exit() here as it can interfere with the web environment.


# --- Entry point for the script ---
# This block runs when the script is executed.
if __name__ == "__main__":
    # Pygame initialization happens here before asyncio.run starts the asynchronous loop.
    # The main asynchronous function is started by asyncio.run().
    asyncio.run(main())