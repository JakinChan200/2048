import time
import tkinter as tk
from tkinter import *
import random
import copy
import threading

from botLib import botLib, to_c_board, from_c_board
# import ctypes
# botLib = ctypes.CDLL('C:/Users/Jakin/TeamName/bin/2048.dll')


botLib.myprint()
print(botLib.add(5, 3))

# print(bar())
# from PIL import Image, ImageTk
# from pynput import keyboard
# from pynput.keyboard import Key

bgColor = "#AADB1E"

data = [["", "", "", ""], ["", "", "", ""], ["", "", "", ""], ["", "", "", ""]]
color = [["", "#aa7dfa"], ["2", "#eee4da"], ["4", "#eee1c9"], ["8", "#f3b27a"], ["16", "#f69664"], ["32", "#f77c5f"], ["64", "#f75f3b"], ["128", "#edd073"], ["256", "#edcc62"], ["512", "#edc950"], ["1024", "#edc53f"], ["2048", "#edc12e"]]
player_score = 0 #every time tiles combine, add it to the current score
max_player_score = 0
#data = [["4", "4", "2", "4"], ["2", "8", "", ""], ["2", "4", "4", "2"], ["2", "16", "4", "4"]]
# data = [["4", "4", "4", "4"], ["4", "4", "4", "4"], ["4", "4", "4", "4"], ["4", "4", "4", "4"]]

def display_board():
    screen = tk.Tk() #Initialize Screen
    screen.title("2048") #Title for Screen
    screen_width, screen_height = screen.winfo_screenwidth(), screen.winfo_screenheight() #Get screen width and height
    screen.geometry('%dx%d+%d+%d' % (800, 800, (screen_width/2) - (800/2), (screen_height/2) - (800/2))) #Set screen width and height depending on monitor's screen's width and height
    screen.resizable(False,False) #Make it so you can't shrink the window size

    screen.bind('<Left>', lambda event: on_left_key(event,screen)) #Bind arrow keys and read inputs
    screen.bind('<Right>', lambda event: on_right_key(event,screen))
    screen.bind('<Up>', lambda event: on_up_key(event,screen))
    screen.bind('<Down>', lambda event: on_down_key(event,screen))
    
    Grid.rowconfigure(screen,2,weight = 1) #Weights for the 6 by 4 grid so they are all equal weights except for first 2 rows which are text and buttons
    Grid.rowconfigure(screen,3,weight = 1)
    Grid.rowconfigure(screen,4,weight = 1)
    Grid.rowconfigure(screen,5,weight = 1)
    Grid.rowconfigure(screen,6,weight = 1)
    Grid.columnconfigure(screen,0,weight = 1)
    Grid.columnconfigure(screen,1,weight = 1)
    Grid.columnconfigure(screen,2,weight = 1)
    Grid.columnconfigure(screen,3,weight = 1)
    Grid.columnconfigure(screen,4,weight = 1)

    screen.configure(bg=bgColor)

    create_Start_State() #Create two starting tiles randomly each with 2 or 4

    create_text_and_buttons(screen) #Create text and buttons (New Game, Bot Plays, You Play)
    create_grid(screen) #Create the 4 by 4 grid

    screen.mainloop() #Display's the screen 

def create_text_and_buttons(screen):
    header_label = tk.Label(screen, text = "2048", font = ("Monospace", 50), fg = "#1b1c1e", bg = bgColor) #2048 Text located at 0,0
    header_label.grid(row = 0, column = 0, pady = (30,10), padx = 20, columnspan = 2)

    play_yourself_button = tk.Button(screen, text = "You Play", bg = "#d342f8") #Play Yourself button located at 0,2
    play_yourself_button.grid(row = 0, column = 2, sticky = "ew", pady=(0,3))
    play_yourself_button.bind("<Button-1>", lambda event: change_color(play_yourself_button,event, screen))
    play_yourself_button.bind("<ButtonRelease-1>", lambda event: change_back_color(play_yourself_button,event))

    play_bot_button = tk.Button(screen, text = "AI Play", bg = "#d342f8") #AI Play button located at 1,2
    play_bot_button.grid(row = 1, column = 2, sticky = "ew", pady = (0,30))
    play_bot_button.bind("<Button-1>", lambda event: change_color(play_bot_button, event, screen, True))
    play_bot_button.bind("<ButtonRelease-1>", lambda event: change_back_color(play_bot_button,event))

    score_text = tk.Label(screen,text = "Current Score: 0", bg = bgColor, font = ("Monospace",11))
    score_text.grid(row = 0, column = 3)

    max_score_text = tk.Label(screen,text = "Max Player Score: 0", bg = bgColor, font = ("Monospace",11))
    max_score_text.grid(row = 1, column = 3, pady = (0,30))
    
def create_grid(screen):
    global data
    global color
    color_map = {k[0]:k[1] for k in color} #Create color map for more efficient color setting

    for children in screen.winfo_children():        #cleaning page 
        info = children.grid_info()
        if info['row'] >= 2 and info['row'] <= 6:
            children.destroy()

    for i in range(4): #Create 4 by 4 grid
        for j in range(4):
            backgroundColor = "#3d3a32"
            dij = data[i][j]
            if dij in color_map:
                backgroundColor = color_map[dij]
            label = tk.Label(screen, text= dij, relief = "solid", borderwidth = 2, width = 30, height = 30, bg = backgroundColor, font = ("Arial", 35)) #Create the labels for each grid space
            label.grid(row = i+2,column = j) #Set the grid starting from 2,0

def update_score(add_amount,screen):
    global player_score
    player_score += add_amount

    screen.grid_slaves(row = 0, column = 3)[0].destroy()
    score_text = tk.Label(screen,text = "Current Score: {}".format(player_score), bg = bgColor, font = ("Monospace",11))
    score_text.grid(row = 0, column = 3)

def change_color(button, event, screen, isBot = False):
    button.configure(bg = "#594d58")
    reset_game(screen) #Reset the game when either "You play" or "AI play" button is pressed
    if isBot:
        bot_plays(event, screen)
    button["state"] = "disabled"

def change_back_color(button, event):
    button.configure(bg = "#d342f8")
    button["state"] = "normal"

def reset_game(screen):
    global data
    global player_score
    global max_player_score
    data = [["", "", "", ""], ["", "", "", ""], ["", "", "", ""], ["", "", "", ""]] #Reset all tiles to empty
    create_Start_State() #Generate 2 random tiles
    create_grid(screen) #Populate the board
    if player_score > max_player_score: #Set Max score
        max_player_score = player_score
    player_score = 0 #Reset current score
    screen.grid_slaves(row = 0, column = 3)[0].destroy() #Remove previous current score widget to prevent overlap
    score_text = tk.Label(screen,text = "Current Score: {}".format(player_score), bg = bgColor, font = ("Monospace",11)) #Display Score
    score_text.grid(row = 0, column = 3)

    screen.grid_slaves(row = 1, column = 3)[0].destroy() #Remove previous max score widget to prevent overlap
    max_score_text = tk.Label(screen,text = "Max Player Score: {}".format(max_player_score), bg = bgColor, font = ("Monospace",11)) #Display Max Score
    max_score_text.grid(row = 1, column = 3, pady = (0,30))

def create_Start_State():
    global data
    piece_one_x = random.randint(0,3) #Random X Starting Position
    piece_one_y = random.randint(0,3) #Random Y Starting Positionnotiis
    piece_two_x = random.randint(0,3)
    piece_two_y = random.randint(0,3)
    piece_one_value = random.choice([2,4])  
    piece_two_value = random.choice([2,4])
    
    while piece_one_x == piece_two_x and piece_one_y == piece_two_y: #Make sure the 2 pieces aren't on the same spot
        piece_two_x = random.randint(0,3)
        piece_two_y = random.randint(0,3)
        
    data[piece_one_x][piece_one_y] = str(piece_one_value)
    data[piece_two_x][piece_two_y] = str(piece_two_value)

def create_random_tile():
    global data
    openSpots = list()
    for i in range(4):
        for j in range(4):
            if data[i][j] == "":
                openSpots.append([i, j])
    if len(openSpots) != 0:
        open_spot_index = random.randint(0, len(openSpots)-1)
        data[openSpots[open_spot_index][0]][openSpots[open_spot_index][1]] = "2" if random.random() < 0.9 else "4"
    
def check_if_end():
    global data
    for i in range(4):
        for j in range(4):
            dij = data[i][j]
            if dij == "":
                return False
            
            if i != 0 and dij == data[i-1][j]:
                return False
                
            if i != 3 and dij == data[i+1][j]:
                return False
            
            if j != 0 and dij == data[i][j-1]:
                return False
                
            if j != 3 and dij == data[i][j+1]:
                return False
    return True

def updateBoard(new_tile_flag, screen, player_score, max_player_score):
    if new_tile_flag:
        create_random_tile()
        if check_if_end():
            if player_score > max_player_score:
                max_player_score = player_score
                screen.grid_slaves(row = 1, column = 3)[0].destroy()
                max_score_text = tk.Label(screen,text = "Max Player Score: {}".format(max_player_score), bg = bgColor, font = ("Monospace", 11))
                max_score_text.grid(row = 1, column = 3, pady = (0,30))
            create_grid(screen)
            display_end_screen(screen)
        create_grid(screen)

def on_left_key(event, screen):
    global player_score
    global max_player_score
    new_tile_flag = False
    for i in range(4):          #rows
        for j in range(4):      #columns
            for k in range(j):  #0 to j
                if data[i][j] == "":
                    continue
                if k == j-1:                                #case where you are looking at the position directly to the left of j in row i
                    dij = data[i][j]
                    dik = data[i][k]
                    if dik == dij:
                        data[i][k] = str(int(dik)*2)
                        update_score(int(data[i][k]),screen)#update_score needs int
                        data[i][j] = ""
                        new_tile_flag = True
                if data[i][k] == "":                        #case where there is a blank at data[i][k]
                    dik_minus_one = data[i][k-1]
                    dij = data[i][j]
                    if k != 0 and dik_minus_one == dij:     #case where k is not the leftmost pos and value in data[i][k-1] is the same as the value in data[i][j]
                        #add data[i][k-1] and data[i][j] and then move it to data[i][k-1]
                        data[i][k-1] = str(int(dik_minus_one)*2)
                        update_score(int(data[i][k-1]), screen)
                        data[i][j] = ""
                        new_tile_flag = True
                    else:                                   #case where k is the leftmost pos or value in data[i][k-1] is not the same as the value in data[i][j]
                        #move data[i][j] to data[i][k]
                        data[i][k] = dij
                        data[i][j] = ""
                        new_tile_flag = True
    updateBoard(new_tile_flag, screen, player_score, max_player_score)

def on_right_key(event, screen):
    global player_score
    global max_player_score
    new_tile_flag = False
    for i in range(4):
        for j in range(3, -1, -1):
            for k in range(3, j-1, -1):
                if data[i][j] == "":
                    continue
                if j != 3 and k == j+1: #case where the two numbers are next to each other
                    if data[i][k] == data[i][j]:
                        data[i][k] = str(int(data[i][k])*2)
                        update_score(int(data[i][k]),screen)
                        data[i][j] = ""
                        new_tile_flag = True
                if data[i][k] == "": #case where there is a blank in between
                    if k != 3 and data[i][k+1] == data[i][j]: # case where the last one we looked at is the one 
                        data[i][k+1] = str(int(data[i][k+1])*2)
                        update_score(int(data[i][k+1]),screen)
                        data[i][j] = ""
                        new_tile_flag = True
                    else:
                        data[i][k] = data[i][j]
                        data[i][j] = ""
                        new_tile_flag = True
    updateBoard(new_tile_flag, screen, player_score, max_player_score)


def on_up_key(event, screen):
    global player_score
    global max_player_score
    new_tile_flag = False
    for j in range(4):                 #iterating through columns
        for i in range(4):              #iterating through rows
            for k in range(i):          #iterating through column up to j
                if data[i][j] == "":    #nothing there
                    continue
                if k == i - 1:                            #If they are next to each other
                    if data[i][j] == data[k][j]:            #If values are the same
                        data[k][j] = str(int(data[k][j])*2) #Combine them
                        update_score(int(data[k][j]),screen)
                        data[i][j] = ""
                        new_tile_flag = True
                if data[k][j] == "":    #if there is at least one tile empty above it
                    if k != 0 and data[k-1][j] == data[i][j]:
                        data[k-1][j] = str(int(data[k-1][j])*2)
                        update_score(int(data[k-1][j]),screen)
                        data[i][j] = ""
                        new_tile_flag = True
                    else:
                        data[k][j] = data[i][j] 
                        data[i][j] = ""
                        new_tile_flag = True
    updateBoard(new_tile_flag, screen, player_score, max_player_score)

def on_down_key(event, screen):
    global player_score
    global max_player_score
    new_tile_flag = False
    for j in range(4):                          #iterating through columns
        for i in range(3, -1, -1):              #iterating through rows
            for k in range(3, i-1, -1):         #iterating through column up to j
                if data[i][j] == "":            #nothing there
                    continue
                if k == i + 1:                            #If they are next to each other
                    if data[i][j] == data[k][j]:            #If values are the same
                        data[k][j] = str(int(data[k][j])*2) #Combine them
                        update_score(int(data[k][j]),screen)
                        data[i][j] = ""
                        new_tile_flag = True
                if data[k][j] == "":    #if there is at least one tile empty above it
                    if k != 3 and data[k+1][j] == data[i][j]:
                        data[k+1][j] = str(int(data[k+1][j])*2)
                        update_score(int(data[k+1][j]),screen)
                        data[i][j] = ""
                        new_tile_flag = True
                    else:
                        data[k][j] = data[i][j] 
                        data[i][j] = ""
                        new_tile_flag = True
    updateBoard(new_tile_flag, screen, player_score, max_player_score)


def display_end_screen(screen): #GAME OVER screen
    global player_score
    end_screen = tk.Tk()
    end_screen.title("Game Over")
    screen_width, screen_height = end_screen.winfo_screenwidth(), end_screen.winfo_screenheight()               #Get screen width and height
    end_screen.geometry('%dx%d+%d+%d' % (400, 400, (screen_width/2) - (400/2), (screen_height/2) - (400/2)))    #Set screen width and height depending on monitor's screen's width and height
    end_screen.resizable(False,False)                                                                           #Make it so you can't shrink the window size

    background_canvas = tk.Canvas(end_screen, width = 400, height = 400)
    background_canvas.pack()

    background_photo = tk.PhotoImage(master = end_screen, file="endGameBGImage.png") #Background image for game over screen
    background_canvas.create_image(0,0,anchor = "nw", image = background_photo)

    background_canvas.create_text(200,100,font = "monospace 35 bold", fill = "black", text = "Game Over!") #Game Over Text
    background_canvas.create_text(200,200,font = "monospace 25", fill = "black", text = "Your Score: {}".format(player_score)) #Current Score TExt

    reset_button = tk.Button(end_screen, text = "Reset Game", bg = "white", width = 10, height = 1, font = ("Monospace",12), command=lambda: game_over_reset(end_screen, screen))
    reset_button.place(relx = 0.5, rely = 0.8, anchor = "center")
                        
    end_screen.mainloop()
    
def game_over_reset(end_screen, screen): #Closes Game Over Screen and resets the board
    end_screen.destroy()
    reset_game(screen)

LARGE_TILE_THRESHOLD = 128
def evaluation(board): #Evaluate the state of the board (data)
    # Give points for empty tiles
    
    # emptyTilesWeight = 270
    # mergeWeight = 700
    # sumWeight = 11
    # monotonicityWeight = 47
    
    # monotonicityPower = 4
    # monotonicityLeft = 0
    # monotonicityRight = 0
    
    # empty = 0
    # points = 0
    # sum = 0
    # merges = 0
    # temp = 0
    
    # for i in range(4):
    #     temp = 0
    #     for k in range(4):
    #         if board[i][k] == "":   #counting empty spots (this and next line)
    #             empty += 1
    #         else:
    #             currTile = int(board[i][k])
    #             sum += currTile
    #             if temp == 0:      #checking how many merges we can do (this line and the next 4)
    #                 temp = currTile
    #             else:
    #                 if currTile == temp: 
    #                     merges += 1
    #                 if currTile > temp:     #monotonicity
    #                     monotonicityRight += abs(pow(currTile, monotonicityPower) - pow(temp, monotonicityPower))
    #                 else:
    #                     monotonicityLeft += abs(pow(temp, monotonicityPower) - pow(currTile, monotonicityPower))
    #                 temp = currTile
                    
    # points = 200000 - (sum * sumWeight) + (empty * emptyTilesWeight) + (merges * mergeWeight) - (monotonicityWeight * min(monotonicityLeft, monotonicityRight))

    points = 0
    for i in range(4):
        for k in range(4):
            if board[i][k] == "":
                points += 16
            '''
            if left of curr is either twice or half of curr
            if (board[i-i][k] == (2 * board[i][k])) or (board[i-1][k] == (board[i][k] / 2))
            '''
            
            # Give penalties if big difference between adjacent tiles
            if board[i][k] != "":
                curr_tile_value = board[i][k] 
                #Check Right Tile (If exists)
                if (k < 3) and (board[i][k+1] != ""):
                    right_tile_value = board[i][k+1]
                    minOfTwo = min(right_tile_value, curr_tile_value)
                    points -= abs(int(curr_tile_value) - int(right_tile_value)) / int(minOfTwo) #avg
                #Check Down Tile (If exists) 
                if (i < 3) and (board[i + 1][k] != ""):
                    down_tile_value = board[i + 1][k]
                    minOfTwo = min(down_tile_value,curr_tile_value)
                    points -= abs(int(curr_tile_value) - int(down_tile_value)) / int(minOfTwo)
                #Check Left Tile (If exists)
                if (k > 0) and (board[i][k-1] != ""):
                    left_tile_value = board[i][k - 1]
                    minOfTwo = min(left_tile_value,curr_tile_value)
                    points -= abs(int(curr_tile_value) - int(left_tile_value)) / int(minOfTwo)
                #Check Up Tile (If exists)
                if (i > 0) and (board[i - 1][k] != ""):
                    up_tile_value = board[i-1][k]
                    minOfTwo = min(up_tile_value,curr_tile_value)
                    points -= abs(int(curr_tile_value) - int(up_tile_value)) / int(minOfTwo)

            #Add penalties if the tile value is at least as large as LARGE_TILE_THRESHOLD
            if(i == 0 and (board[i][k] != "")):
                if int(board[i][k]) >= LARGE_TILE_THRESHOLD: #If the tile value is larger enough (than we specify)
                    points += int(board[i][k])
            if(i == 3 and (board[i][k] != "")):
                if int(board[i][k]) >= LARGE_TILE_THRESHOLD: #If the tile value is larger enough (than we specify)
                    points += int(board[i][k])
            if(k == 0 and (board[i][k] != "")):
                if int(board[i][k]) >= LARGE_TILE_THRESHOLD: #If the tile value is larger enough (than we specify)
                    points += int(board[i][k])
            if(k == 3 and (board[i][k] != "")):
                if int(board[i][k]) >= LARGE_TILE_THRESHOLD: #If the tile value is larger enough (than we specify)
                    points += int(board[i][k])    
            # # Give bonuses for large values on the edge
            # if ((i == 0) or (i == 3) or (k == 0) or (k == 3)) and (board[i][k] != ""): #If tile is on the edge
            #     if int(board[i][k]) >= LARGE_TILE_THRESHOLD: #If the tile value is larger enough (than we specify)
            #         points += int(board[i][k])                  #PROBLEM: point values are very large so we need to "normalize somehow"
    return points

def create_random_tile_local(board):
    '''
    adds 2 and then 4 in each open spot, one by one
    possibility #1: return list of boards
        con: the function that calls it has to deal with the list
    possibility #2: yield instead of return

    Currently outputs list of boards
    '''
    all_boards = list()
    openSpots = list()
    for i in range(4):
        for j in range(4):
            if board[i][j] == "":
                openSpots.append([i, j])
    if len(openSpots) != 0:
        for spot in openSpots:  #spot is a list of x,y coordinates
            board[spot[0]][spot[1]] = "2" #This empty spot has a 2
            all_boards.append(copy.deepcopy(board)) #Track this position
            board[spot[0]][spot[1]] = "4" #Set the 2 to a 4 spot
            all_boards.append(copy.deepcopy(board)) #Track this position
            board[spot[0]][spot[1]] = "" #Undo the 2 to a blank spot and loop to the other open spots 
    return all_boards

def check_if_end_local(local_board):
    for i in range(4):
        for j in range(4):
            dij = local_board[i][j]
            if dij == "":
                return False
            
            if i != 0 and dij == local_board[i-1][j]:
                return False
                
            if i != 3 and dij == local_board[i+1][j]:
                return False
            
            if j != 0 and dij == local_board[i][j-1]:
                return False
                
            if j != 3 and dij == local_board[i][j+1]:
                return False
    return True

def move_right_local(boards):
    board = copy.deepcopy(boards)
    #Move the board array to the right
    #Return new_board (array of array)
    for i in range(4):
        for j in range(3, -1, -1):
            for k in range(3, j-1, -1):
                if board[i][j] == "":
                    continue
                if j != 3 and k == j+1:                         #case where the two numbers are next to each other
                    if board[i][k] == board[i][j]:
                        board[i][k] = str(int(board[i][k])*2)
                        board[i][j] = ""
                if board[i][k] == "":                           #case where there is a blank in between
                    if k != 3 and board[i][k+1] == board[i][j]: #case where the last one we looked at is the one 
                        board[i][k+1] = str(int(board[i][k+1])*2)
                        board[i][j] = ""
                    else:
                        board[i][k] = board[i][j]
                        board[i][j] = ""
    return board

def move_down_local(boards):
    board = copy.deepcopy(boards)
    #Move the board array to the right
    #Return new_board (array of array)
    for j in range(4):                          #iterating through columns
        for i in range(3, -1, -1):              #iterating through rows
            for k in range(3, i-1, -1):         #iterating through column up to j
                if board[i][j] == "":            #nothing there
                    continue
                if k == i + 1:                            #If they are next to each other
                    if board[i][j] == board[k][j]:            #If values are the same
                        board[k][j] = str(int(board[k][j])*2) #Combine them
                        board[i][j] = ""
                if data[k][j] == "":    #if there is at least one tile empty above it
                    if k != 3 and board[k+1][j] == board[i][j]:
                        board[k+1][j] = str(int(board[k+1][j])*2)
                        board[i][j] = ""
                    else:
                        board[k][j] = board[i][j] 
                        board[i][j] = ""
    return board

def move_up_local(boards):
    board = copy.deepcopy(boards)
    #Move the board array to the right
    #Return board (array of array)
    for j in range(4):                 #iterating through columns
        for i in range(4):              #iterating through rows
            for k in range(i):          #iterating through column up to j
                if board[i][j] == "":    #nothing there
                    continue
                if k == i - 1:                            #If they are next to each other
                    if board[i][j] == board[k][j]:            #If values are the same
                        board[k][j] = str(int(board[k][j])*2) #Combine them
                        board[i][j] = ""
                if board[k][j] == "":    #if there is at least one tile empty above it
                    if k != 0 and board[k-1][j] == board[i][j]:
                        board[k-1][j] = str(int(board[k-1][j])*2)
                        board[i][j] = ""
                    else:
                        board[k][j] = board[i][j] 
                        board[i][j] = ""
    return board

def move_left_local(boards):
    board = copy.deepcopy(boards)
    #Move the board array to the right
    #Return board (array of array)
    for i in range(4):          #rows
        for j in range(4):      #columns
            for k in range(j):  #0 to j
                if board[i][j] == "":
                    continue
                if k == j-1:                                #case where you are looking at the position directly to the left of j in row i
                    dij = board[i][j]
                    dik = board[i][k]
                    if dik == dij:
                        board[i][k] = str(int(dik)*2)
                        board[i][j] = ""
                if board[i][k] == "":                        #case where there is a blank at data[i][k]
                    dik_minus_one = board[i][k-1]
                    dij = board[i][j]
                    if k != 0 and dik_minus_one == dij:     #case where k is not the leftmost pos and value in data[i][k-1] is the same as the value in data[i][j]
                        board[i][k-1] = str(int(dik_minus_one)*2)
                        board[i][j] = ""
                    else:                                   #case where k is the leftmost pos or value in data[i][k-1] is not the same as the value in data[i][j]
                        board[i][k] = dij
                        board[i][j] = ""
    return board

#need to know who all calls minimax?? who calls minimax first? is board always local or does it start as global and then be local?
#board is current state it is checking 

MAX_DEPTH = 4

def minimax(board, depth, is_max):
    if (depth == MAX_DEPTH) or check_if_end_local(board):
        return evaluation(board)
    
    if is_max: #maximizing player
        curr_val = -100000
        
        new_board = move_right_local(board)
        val_right = minimax(new_board, depth + 1, False) #Evaluate position from moving right
        
        new_board = move_left_local(board)
        val_left = minimax(new_board, depth + 1, False)

        new_board = move_up_local(board)
        val_up = minimax(new_board, depth + 1, False)
        
        new_board = move_down_local(board)
        val_down = minimax(new_board, depth + 1, False)

        curr_val = max(val_down, val_right, val_left, val_up, curr_val) #Get max value (is maximizing)
        return curr_val
    else:   #random 'player'
        #everytime there is a move from the AI, consider all possible combinations with each empty tile taking on either a 2 or a 4.
        #assume the randomizer gives the worst possibility and continue the game from there. worst is leads to game over.
        curr_val = 100000
        all_boards = create_random_tile_local(board)
        for single_board in all_boards:
            single_board_val = minimax(single_board, depth + 1, True)
            curr_val = min(curr_val, single_board_val)
        return curr_val

def getBestMove(x):
    board = to_c_board(x);
    move = botLib.find_best_move(board)
    return move

def bot_plays(event, screen): #When you press AI plays button, will make the moves
    #curr_board = data.copy()
    
    while True:
        curr_board = copy.deepcopy(data)
        move = getBestMove(curr_board)
            
        if move == 0:
            on_up_key(event, screen)
        elif move == 1:
            on_down_key(event,screen)
        elif move == 2:
            on_left_key(event, screen)
        elif move == 3:
            on_right_key(event,screen)
        else:
            KeyError
        screen.update()
            
    # while True:
    #     curr_board = copy.deepcopy(data)
    #     screen.update()
    #     all_moves = {}
    #     lock = threading.Lock()

    #     #Move = Call Minimax for the move
    #     #Simulates the move Right
    #     def move_right_local2(curr_board):
    #         board_after_right_move = move_right_local(curr_board)
    #         right_move_score = minimax(board_after_right_move, 0 ,True)
    #         if (board_after_right_move != curr_board):
    #             with lock:
    #                 all_moves['r'] = right_move_score
    #     t1 = threading.Thread(target=move_right_local2, args=(curr_board,))
    #     #board_after_right_move = move_right_local(curr_board)
    #     #right_move_score = minimax(board_after_right_move, 0 ,True)
    #     #if (board_after_right_move != curr_board):
    #     #    all_moves['r'] = right_move_score

    #     #Simulates the move Left
    #     def move_left_local2(curr_board):
    #         board_after_left_move = move_left_local(curr_board)
    #         left_move_score = minimax(board_after_left_move, 0 ,True)   #Calls Minimax and holds the value EX: (left, 2.0)
    #         if (board_after_left_move != curr_board):
    #             with lock:
    #                 all_moves['l'] = left_move_score
    #     t2 = threading.Thread(target=move_left_local2, args=(curr_board,))
    #     #board_after_left_move = move_left_local(curr_board)
    #     #left_move_score = minimax(board_after_left_move, 0 ,True)   #Calls Minimax and holds the value EX: (left, 2.0)
    #     #if (board_after_left_move != curr_board):
    #     #    all_moves['l'] = left_move_score

    #     #Simulates the move Up
    #     def move_up_local2(curr_board):  
    #         board_after_up_move = move_up_local(curr_board)
    #         up_move_score = minimax(board_after_up_move, 0 ,True)
    #         if (board_after_up_move != curr_board):
    #             with lock:
    #                 all_moves['u'] = up_move_score
    #     t3 = threading.Thread(target=move_up_local2, args=(curr_board,))
    #     #board_after_up_move = move_up_local(curr_board)
    #     #up_move_score = minimax(board_after_up_move, 0 ,True)
    #     #Calls Minimax and holds the value EX: (up, 15.0)
    #     #if (board_after_up_move != curr_board):
    #     #    all_moves['u'] = up_move_score

    #     #Simulates the move Down
    #     def move_down_local2(curr_board):
    #         board_after_down_move = move_down_local(curr_board)
    #         down_move_score = minimax(board_after_down_move, 0 ,True)
    #         if (board_after_down_move != curr_board):
    #             with lock:
    #                 all_moves['d'] = down_move_score
    #     t4 = threading.Thread(target=move_down_local2, args=(curr_board,))
    #     #board_after_down_move = move_down_local(curr_board)
    #     #down_move_score = minimax(board_after_down_move, 0 ,True)
    #     #Calls Minimax and holds the value EX: (down, 20.0)
    #     #if (board_after_down_move != curr_board):
    #     #    all_moves['d'] = down_move_score

    #     t1.start()
    #     t2.start()
    #     t3.start()
    #     t4.start()

    #     #threads join here
    #     t1.join()
    #     t2.join()
    #     t3.join()
    #     t4.join()
            
    #     #Picks AND choose the move with highest value EX: Picks down and then does it
    #     #use existing functions to make moves
    #     bot_move = max(all_moves, key=all_moves.get) #key
    #     if bot_move == 'r':
    #         on_right_key(event, screen)
    #         #time.sleep(1)
    #     elif bot_move == 'l':
    #         on_left_key(event,screen)
    #         #time.sleep(1)
    #     elif bot_move == 'u':
    #         on_up_key(event, screen)
    #         #time.sleep(1)
    #     elif bot_move == 'd':
    #         on_down_key(event,screen)
    #         #time.sleep(1)
    #     else:
    #         KeyError
            
        #On X key functions already checks if the game is ended

# def printBoard(board):
#     print("board:")
#     for i in range(4):
#         for j in range(4):
#             if (board[i][j] == ''):
#                 print('.', end=' ')
#             else:
#                 print(board[i][j], end=' ')
#         print()
#     print()


if __name__ == "__main__":
    display_board()
