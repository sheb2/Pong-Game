# Pong-Game
Contact Info
============

Group Members & Email Addresses:

    Shelby Scoville, snsc235@uky.edu
    Laura King, leki231@uky.edu

Versioning
==========

Github Link: https://github.com/sheb2/Pong-Game

General Info
============
This is a multiplayer implementation of Pong using Python sockets.
- The server handles connections and relays game state.
- Player 1 (left paddle) acts as the "Host" for ball physics to ensure synchronization.
- Player 2 (right paddle) connects as a client. 
- The game will start as soon as just 1 client connects so it is better to connect both clients at the same time.

How to Run:
1. Install dependencies: see install instructions
2. Start the Server: `python pongServer.py`
3. Start Player 1: `python pongClient.py` (Connect to IP of Server, you can use `ipconfig/all` to find the IP on the Server computer)
4. Start Player 2: `python pongClient.py` (Connect using same IP as Player 1)

Install Instructions
====================

Run the following line to install the required libraries for this project:

`pip3 install -r requirements.txt`

Known Bugs
==========
- No known Bugs


