# =================================================================================================
# Contributing Authors:	    <Anyone who touched the code>
# Email Addresses:          <Your uky.edu email addresses>
# Date:                     <The date the file was last edited>
# Purpose:                  <How this file contributes to the project>
# Misc:                     <Not Required.  Anything else you might want to include>
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

def receive_updates(client):
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

def send_update(client, paddle_y, ball_x, ball_y, ball_dx, ball_dy, score1, score2, sync):
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

# This is the main game loop.  For the most part, you will not need to modify this.  The sections
# where you should add to the code are marked.  Feel free to change any part of this project
# to suit your needs.
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

        # =========================================================================================
        # Your code here to send an update to the server on your paddle's information,
        # where the ball is and the current score.
        # Feel free to change when the score is updated to suit your needs/requirements
        
        
        # =========================================================================================

        # Update the player paddle and opponent paddle's location on the screen
        #for paddle in [playerPaddleObj, opponentPaddleObj]:
        #    if paddle.moving == "down":
        #        if paddle.rect.bottomleft[1] < screenHeight-10:
        #            paddle.rect.y += paddle.speed
        #   elif paddle.moving == "up":
        #       if paddle.rect.topleft[1] > 10:
        #           paddle.rect.y -= paddle.speed

        # Update the player paddle location
        

        if playerPaddleObj.moving == "down":
            if playerPaddleObj.rect.bottomLeft[1] < screenHeight-10:
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

                # If server is ahead or equal in sync, use server's ball position
                if received_state.get("sync", 0) >= sync:
                    ball.rect.x = received_state.get("ball_x", ball.rect.x)
                    ball.rect.y = received_state.get("ball_y", ball.rect.y)
                    ball.dx = received_state.get("ball_dx", ball.dx)
                    ball.dy = received_state.get("ball_dy", ball.dy)
                    lScore = received_state.get("score1", lScore)
                    rScore = received_state.get("score2", rScore)
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
        
        # This number should be synchronized between you and your opponent.  If your number is larger
        # then you are ahead of them in time, if theirs is larger, they are ahead of you, and you need to
        # catch up (use their info)
        sync += 1
        # =========================================================================================
        # Send your server update here at the end of the game loop to sync your game with your
        # opponent's game
        send_update(
            client,
            playerPaddleObj.rect.y,
            ball.rect.y,
            ball.dx,
            ball.dy,
            lScore,
            rScore,
            sync
        )
        # =========================================================================================




# This is where you will connect to the server to get the info required to call the game loop.  Mainly
# the screen width, height and player paddle (either "left" or "right")
# If you want to hard code the screen's dimensions into the code, that's fine, but you will need to know
# which client is which
def joinServer(ip:str, port:str, errorLabel:tk.Label, app:tk.Tk) -> None:
    # Purpose:      This method is fired when the join button is clicked
    # Arguments:
    # ip            A string holding the IP address of the server
    # port          A string holding the port the server is using
    # errorLabel    A tk label widget, modify it's text to display messages to the user (example below)
    # app           The tk window object, needed to kill the window
    
    # Create a socket and connect to the server
    # You don't have to use SOCK_STREAM, use what you think is best
    # client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Get the required information from your server (screen width, height & player paddle, "left or "right)


    # If you have messages you'd like to show the user use the errorLabel widget like so
    #errorLabel.config(text=f"Some update text. You input: IP: {ip}, Port: {port}")
    # You may or may not need to call this, depending on how many times you update the label
    #errorLabel.update()     

    # Close this window and start the game with the info passed to you from the server
    #app.withdraw()     # Hides the window (we'll kill it later)
    #playGame(screenWidth, screenHeight, ("left"|"right"), client)  # User will be either left or right paddle
    #app.quit()         # Kills the window
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
def startScreen():
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
    
    # Uncomment the line below if you want to play the game without a server to see how it should work
    # the startScreen() function should call playGame with the arguments given to it by the server this is
    # here for demo purposes only
    #playGame(640, 480,"left",socket.socket(socket.AF_INET, socket.SOCK_STREAM))