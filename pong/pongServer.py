# =================================================================================================
# Contributing Authors:	    Shelby Scoville
# Email Addresses:          snsc235@uky.edu
# Date:                     11/19/2025
# Purpose:                  Server Logic for Pong Game
# Misc:                     
# =================================================================================================

import socket
import threading
import json
import time

class Server:
    def __init__(self, host='127.0.0.1', port=55555):
        self.host = host
        self.port = port
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((self.host, self.port))
        self.server.listen()

        self.clients = []
        self.state_lock = threading.Lock()
        self.game_state = {
            "ball_x": 320,
            "ball_y": 240,
            "ball_dx": -5,
            "ball_dy": 0,
            "p1_y": 215,
            "p2_y": 215,
            "score1": 0,
            "score2": 0,
            "sync" : 0
        }
    def send_data(self, client, data):
        try:
            message = json.dumps(data) + '\n'
            client.sendall(message.encode('utf-8'))
            return True
        except:
            return False
               
    def handle_client(self, client, player_id):
        buffer = "" # Initialize buffer once per client so it persists
        while True:
            try:
                # 1. Receive Data
                chunk = client.recv(1024).decode('utf-8')
                if not chunk:
                    break
                
                buffer += chunk

                # 2. Process ALL complete messages currently in the buffer
                while '\n' in buffer:
                    message, buffer = buffer.split('\n', 1)
                    
                    try:
                        data = json.loads(message)
                    except json.JSONDecodeError:
                        # If a message is corrupted, just skip it and keep going
                        continue

                    # 3. Update Game State
                    with self.state_lock:
                        if player_id == 1:
                            self.game_state["p1_y"] = data.get("paddle_y", self.game_state["p1_y"])
                        else:
                            self.game_state["p2_y"] = data.get("paddle_y", self.game_state["p2_y"])

                        # Sync logic: Only update ball/score if the client is "newer"
                        if data.get("sync", 0) >= self.game_state["sync"]:
                            self.game_state["ball_x"] = data.get("ball_x", self.game_state["ball_x"])
                            self.game_state["ball_y"] = data.get("ball_y", self.game_state["ball_y"])
                            self.game_state["ball_dx"] = data.get("ball_dx", self.game_state["ball_dx"])
                            self.game_state["ball_dy"] = data.get("ball_dy", self.game_state["ball_dy"])
                            self.game_state["score1"] = data.get("score1", self.game_state["score1"])
                            self.game_state["score2"] = data.get("score2", self.game_state["score2"])
                            self.game_state["sync"] = data["sync"]
                
                # 4. Send the updated state back to the client
                response = self.game_state.copy()
                if not self.send_data(client, response):
                    break   

            except Exception as e:
                print(f"Error with player {player_id}: {e}")
                break
        
        print(f"Player {player_id} disconnected")
        client.close()      

    def run(self):
        print(f"Server started on {self.host}:{self.port}")
        print("Waiting for 2 players...")
        while len(self.clients) < 2:
            c, addr = self.server.accept()
            player_id = len(self.clients) + 1
            self.clients.append(c)
            
            paddle = "left" if player_id == 1 else "right"
            init_data = {
                'screen_width': 640,
                'screen_height': 480,
                'paddle': paddle
            }
            self.send_data(c, init_data)

            print(f"Player {player_id} connected from {addr} as {paddle} paddle")

        threading.Thread(target=self.handle_client, args=(self.clients[0], 1), daemon=True).start()
        threading.Thread(target=self.handle_client, args=(self.clients[1], 2), daemon=True).start()

        print("Both players connected! Game starting...")

        try: 
            while True:
                pass
        except KeyboardInterrupt:
            print("\nServer shutting down...")
            self.server.close()

if __name__ == "__main__":
    Server().run()

# Use this file to write your server logic
# You will need to support at least two clients
# You will need to keep track of where on the screen (x,y coordinates) each paddle is, the score 
# for each player and where the ball is, and relay that to each client
# I suggest you use the sync variable in pongClient.py to determine how out of sync your two
# clients are and take actions to resync the games