# =================================================================================================
# Contributing Authors:	    Shelby Scoville
# Email Addresses:          snsc235@uky.edu
# Date:                     11/25/25
# Purpose:                  Client Logic for Pong Game
# =================================================================================================

import pygame
import tkinter as tk
import sys
import socket
import json
import threading

from assets.code.helperCode import *

# Global variable to store received game state
received_state = None
state_lock = threading.Lock()

# Author:   Shelby Scoville
# Purpose:  Continuously receives data from the server and updates the global state
# Pre:      Client socket is connected
# Post:     Global 'received_state' is updated with latest server data
def receive_updates(client: socket.socket) -> None:
    global received_state
    buffer = ""
    while True:
        try: 
            chunk = client.recv(1024).decode('utf-8')
            if not chunk: 
                break

            buffer += chunk

            # process all complete messages in buffer
            while '\n' in buffer:
                message, buffer = buffer.split('\n', 1)
                try:
                    data = json.loads(message)
                    with state_lock:
                        received_state = data
                except json.JSONDecodeError:
                    continue
        except Exception as e:
            print(f"Error receiving data: {e}")
            break

# Author:   Shelby Scoville
# Purpose:  Sends the current client's game state to the server
# Pre:      Client socket is connected, game variables are initialized
# Post:     JSON data is sent over the socket
def send_update(client: socket.socket, paddle_y: int, ball_x: int, ball_y: int, ball_dx: int, ball_dy: int, score1: int, score2: int, sync: int) -> bool:
    try:
        data = {
            "paddle_y": paddle_y,
            "ball_x": ball_x,
            "ball_y": ball_y,
            "ball_dx": ball_dx,
            "ball_dy": ball_dy,
            "score1": score1,
            "score2": score2,
            "sync": sync
        }
        message = json.dumps(data) + '\n'
        client.sendall(message.encode('utf-8'))
        return True
    except Exception as e:
        print(f"Error sending data: {e}")
        return False

# Author:   Shelby Scoville
# Purpose:  Main game loop handling inputs, rendering, and logic
# Pre:      Pygame is initialized, connection to server established
# Post:     Game runs until window is closed or error occurs
def playGame(screenWidth:int, screenHeight:int, playerPaddle:str, client:socket.socket) -> None:
    global received_state

    # Start backgroung thread to receive updates
    receive_thread = threading.Thread(target=receive_updates, args=(client,), daemon=True)
    receive_thread.start()
    
    # Pygame inits
    pygame.mixer.pre_init(44100, -16, 2, 2048)
    pygame.init()

    # Constants
    WHITE = (255,255,255)
    clock = pygame.time.Clock()
    scoreFont = pygame.font.Font("./assets/fonts/pong-score.ttf", 32)
    winFont = pygame.font.Font("./assets/fonts/visitor.ttf", 48)
    pointSound = pygame.mixer.Sound("./assets/sounds/point.wav")
    bounceSound = pygame.mixer.Sound("./assets/sounds/bounce.wav")

    # Display objects
    screen = pygame.display.set_mode((screenWidth, screenHeight))
    winMessage = pygame.Rect(0,0,0,0)
    topWall = pygame.Rect(-10,0,screenWidth+20, 10)
    bottomWall = pygame.Rect(-10, screenHeight-10, screenWidth+20, 10)
    centerLine = []
    for i in range(0, screenHeight, 10):
        centerLine.append(pygame.Rect((screenWidth/2)-5,i,5,5))

    # Paddle properties and init
    paddleHeight = 50
    paddleWidth = 10
    paddleStartPosY = (screenHeight/2)-(paddleHeight/2)
    leftPaddle = Paddle(pygame.Rect(10,paddleStartPosY, paddleWidth, paddleHeight))
    rightPaddle = Paddle(pygame.Rect(screenWidth-20, paddleStartPosY, paddleWidth, paddleHeight))

    ball = Ball(pygame.Rect(screenWidth/2, screenHeight/2, 5, 5), -5, 0)

    if playerPaddle == "left":
        opponentPaddleObj = rightPaddle
        playerPaddleObj = leftPaddle
    else:
        opponentPaddleObj = leftPaddle
        playerPaddleObj = rightPaddle

    lScore = 0
    rScore = 0

    sync = 0
   
    while True:
        # Wiping the screen
        screen.fill((0,0,0))

        # Getting keypress events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_DOWN:
                    playerPaddleObj.moving = "down"

                elif event.key == pygame.K_UP:
                    playerPaddleObj.moving = "up"

            elif event.type == pygame.KEYUP:
                playerPaddleObj.moving = ""

        # Update the player paddle location
        if playerPaddleObj.moving == "down":
            if playerPaddleObj.rect.bottomleft[1] < screenHeight-10:
                  playerPaddleObj.rect.y += playerPaddleObj.speed
        elif playerPaddleObj.moving == "up":
            if playerPaddleObj.rect.topleft[1] > 10:
                playerPaddleObj.rect.y -= playerPaddleObj.speed
        
        # Receive updates from server and apply them
        with state_lock:
            if received_state is not None:
                # Update opponent paddle position
                if playerPaddle == "left":
                    opponentPaddleObj.rect.y = received_state.get("p2_y", opponentPaddleObj.rect.y)
                else:
                    opponentPaddleObj.rect.y = received_state.get("p1_y", opponentPaddleObj.rect.y)

                # Sync Logic:
                # Left player is the host. They calculate ball physics and score
                # Right player is the client. They must accept the host's ball/score data
                if playerPaddle == "right":
                    # Always update ball and score from server to stay in sync
                    ball.rect.x = received_state.get("ball_x", ball.rect.x)
                    ball.rect.y = received_state.get("ball_y", ball.rect.y)
                    ball.xVel = received_state.get("ball_dx", ball.xVel) 
                    ball.yVel = received_state.get("ball_dy", ball.yVel)
                    lScore = received_state.get("score1", lScore)
                    rScore = received_state.get("score2", rScore)
                    
                    # Snap our sync clock to the server's clock
                    sync = received_state.get("sync", sync)

        # If the game is over, display the win message
        if lScore > 4 or rScore > 4:
            winText = "Player 1 Wins! " if lScore > 4 else "Player 2 Wins! "
            textSurface = winFont.render(winText, False, WHITE, (0,0,0))
            textRect = textSurface.get_rect()
            textRect.center = ((screenWidth/2), screenHeight/2)
            winMessage = screen.blit(textSurface, textRect)

        else:

            # ==== Ball Logic =====================================================================
            ball.updatePos()

            # If the ball makes it past the edge of the screen, update score, etc.
            if playerPaddle == "left":
                if ball.rect.x > screenWidth:
                    lScore += 1
                    pointSound.play()
                    ball.reset(nowGoing="left")
                elif ball.rect.x < 0:
                    rScore += 1
                    pointSound.play()
                    ball.reset(nowGoing="right")
                
                # If the ball hits a paddle
                if ball.rect.colliderect(playerPaddleObj.rect):
                    bounceSound.play()
                    ball.hitPaddle(playerPaddleObj.rect.center[1])
                elif ball.rect.colliderect(opponentPaddleObj.rect):
                    bounceSound.play()
                    ball.hitPaddle(opponentPaddleObj.rect.center[1])
                
                # If the ball hits a wall
                if ball.rect.colliderect(topWall) or ball.rect.colliderect(bottomWall):
                    bounceSound.play()
                    ball.hitWall()
            
            pygame.draw.rect(screen, WHITE, ball)
            # ==== End Ball Logic =================================================================

        # Drawing the dotted line in the center
        for i in centerLine:
            pygame.draw.rect(screen, WHITE, i)
        
        # Drawing the player's new location
        for paddle in [playerPaddleObj, opponentPaddleObj]:
            pygame.draw.rect(screen, WHITE, paddle)

        pygame.draw.rect(screen, WHITE, topWall)
        pygame.draw.rect(screen, WHITE, bottomWall)
        scoreRect = updateScore(lScore, rScore, screen, WHITE, scoreFont)
        pygame.display.update()
        clock.tick(60)

        sync += 1
        
        # Send server update
        send_update(
            client,
            playerPaddleObj.rect.y,
            ball.rect.x,
            ball.rect.y,
            ball.xVel,
            ball.yVel,
            lScore,
            rScore,
            sync
        )


# Author:   Shelby Scoville
# Purpose:  Connects to server and initiates the game
# Pre:      User input IP and Port are valid
# Post:     Connection established and playGame called, or error displayed
def joinServer(ip:str, port:str, errorLabel:tk.Label, app:tk.Tk) -> None:
    try:
        # Validate inputs
        if not ip or not port:
            errorLabel.config(text="Please enter both IP and Port")
            errorLabel.update()
            return
        
        # Create socket and connect
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.settimeout(5)

        errorLabel.config(text=f"Connecting to {ip}:{port}...")
        errorLabel.update()

        client.connect((ip, int(port)))

        errorLabel.config(text="Connected! Waiting for game info...")
        errorLabel.update()

        # Receive initial game configuration from server
        buffer = ""
        while '\n' not in buffer:
            chunk = client.recv(1024).decode('utf-8')
            if not chunk:
                raise Exception("Connection closed by server")
            buffer += chunk
        
        message = buffer.split('\n')[0]
        init_data = json.loads(message)
        screenWidth = init_data['screen_width']
        screenHeight = init_data['screen_height']
        paddle = init_data['paddle']

        errorLabel.config(text=f"Starting game as {paddle} paddle...")
        errorLabel.update()

        # Remoce timeout for game
        client.settimeout(None)

        # Close the join window and start game
        app.withdraw()
        playGame(screenWidth, screenHeight, paddle, client)
        app.quit()
    except ValueError:
        errorLabel.config(text="Port must be a number")
        errorLabel.update()
    except socket.timeout:
        errorLabel.config(text="Connectiong timeout - check IP/Port")
        errorLabel.update()
    except ConnectionRefusedError:
        errorLabel.config(text="Connection refused - is server running?")
        errorLabel.update()
    except Exception as e:
        errorLabel.config(text=f"Error: {str(e)}")
        errorLabel.update()

# This displays the opening screen, you don't need to edit this (but may if you like)
def startScreen() -> None:
    app = tk.Tk()
    app.title("Server Info")

    image = tk.PhotoImage(file="./assets/images/logo.png")

    titleLabel = tk.Label(image=image)
    titleLabel.grid(column=0, row=0, columnspan=2)

    ipLabel = tk.Label(text="Server IP:")
    ipLabel.grid(column=0, row=1, sticky="W", padx=8)

    ipEntry = tk.Entry(app)
    ipEntry.insert(0, "127.0.0.1") # Default localhost
    ipEntry.grid(column=1, row=1)

    portLabel = tk.Label(text="Server Port:")
    portLabel.grid(column=0, row=2, sticky="W", padx=8)

    portEntry = tk.Entry(app)
    portEntry.insert(0, "55555") # Default port
    portEntry.grid(column=1, row=2)

    errorLabel = tk.Label(text="")
    errorLabel.grid(column=0, row=4, columnspan=2)

    joinButton = tk.Button(text="Join", command=lambda: joinServer(ipEntry.get(), portEntry.get(), errorLabel, app))
    joinButton.grid(column=0, row=3, columnspan=2)

    app.mainloop()

if __name__ == "__main__":
    startScreen()