# =================================================================================================
# Contributing Authors:	    Shelby Scoville
# Email Addresses:          snsc235@uky.edu
# Date:                     11/25/2025
# Purpose:                  Server Logic for Pong Game                     
# =================================================================================================

import socket
import threading
import json

class Server:
    # Author:   Shelby Scoville
    # Purpose:  Initialize the server socket and game state
    # Pre:      Port is available
    # Post:     Server is listening for connections
    def __init__(self, host: str ='127.0.0.1', port: int =55555) -> None:
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

    # Author:   Shelby Scoville
    # Purpose:  Sends JSON data to a specific client
    # Pre:      Client socket is open
    # Post:     Data is sent encoded as bytes
    def send_data(self, client: socket.socket, data: dict) -> bool:
        try:
            message = json.dumps(data) + '\n'
            client.sendall(message.encode('utf-8'))
            return True
        except:
            return False

    # Author:   Shelby Scoville
    # Purpose:  Handles communication loop for a single client (Receives updates, sends state)
    # Pre:      Client is connected and identified by player_id
    # Post:     Client loop ends upon disconnection
    def handle_client(self, client: socket.socket, player_id: int) -> None:
        buffer = "" 
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
    
    # Author:   Shelby Scoville
    # Purpose:  Main server loop to accept incoming connections
    # Pre:      Server socket is listening
    # Post:     Accepts 2 clients and starts their threads
    def run(self) -> None:
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