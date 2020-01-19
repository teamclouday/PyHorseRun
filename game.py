# Game made for CIS400 course assignment

import os
import sys
import time
import random
import shutil

STD_OUTPUT_HANDLE = -11 # the handle value defined in windows kernel.dll

# import os specific libraries
try:
    import ctypes
    from ctypes import wintypes
    import msvcrt
except ImportError:
    import termios
    import tty

# helper class to make os specific calls easier
class OSEasyConsole:
    def __init__(self):
        if os.name == "nt":
            self.WinDll = ctypes.WinDLL("kernel32") # load kernel32.dll
            self.ConsoleHandler = self.WinDll.GetStdHandle(STD_OUTPUT_HANDLE) # get console standard handle

    # a wrapper method
    def MoveCursor(self, pos=(0, 0)):
        if os.name == "nt":
            self._WinMoveCursor(pos)
        else:
            self._UnixMoveCursor(pos)

    # a wrapper method
    def GetChar(self):
        if os.name == "nt":
            return self._WinGetCh()
        else:
            return self._UnixGetCh()

    # function to hide cursor for better game view
    def HideCursor(self):
        if os.name == "nt":
            class CursorInfo(ctypes.Structure):
                _fields_ = [("size", ctypes.c_int), ("visible", ctypes.c_byte)]
            ci = CursorInfo() # init structure to capture cursor information
            self.WinDll.GetConsoleCursorInfo(self.ConsoleHandler, ctypes.byref(ci))
            ci.visible = False
            self.WinDll.SetConsoleCursorInfo(self.ConsoleHandler, ctypes.byref(ci))
        else:
            sys.stdout.write("\033[?25l") # code for hiding cursor in linux terminal
            sys.stdout.flush()

    # function to restore cursor after game stops
    def ShowCursor(self):
        if os.name == "nt":
            class CursorInfo(ctypes.Structure):
                _fields_ = [("size", ctypes.c_int), ("visible", ctypes.c_byte)]
            ci = CursorInfo() # init structure to capture cursor information
            self.WinDll.GetConsoleCursorInfo(self.ConsoleHandler, ctypes.byref(ci))
            ci.visible = True
            self.WinDll.SetConsoleCursorInfo(self.ConsoleHandler, ctypes.byref(ci))
        else:
            sys.stdout.write("\033[?25h") # code for hiding cursor in linux terminal
            sys.stdout.flush()

    def _WinMoveCursor(self, pos):
        self.WinDll.SetConsoleCursorPosition(self.ConsoleHandler, wintypes._COORD(pos[0], pos[1])) # make kernel32 c function call

    def _UnixMoveCursor(self, pos):
        ...

    def _WinGetCh(self):
        if msvcrt.kbhit(): # if there's a keyboard message waiting for read
            return msvcrt.getch() # read the key and return it
        else:
            return None

    def _UnixGetCh(self):
        previous_state = termios.tcgetattr(fd) # store previous state of console
        tty.setcbreak(sys.stdin.fileno())
        bytecode = None
        try:
            bytecode = os.read(sys.stdin.fileno(), 3).decode() # read input 3 bytes into an integer and return it
        finally:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, previous_state) # restore console settings
        return bytecode

# class made for storing horse information
class GameObjHorse:
    def __init__(self, pos):
        self.height = pos
        self.left_left = True # is the left foot pointing to left ?
        self.on_ground = True # is the horse on ground ?
        self.jump = False # is the horse going to jump ?
        self.vel = 0 # vertical velocity, positive is up, negative is down
        self.on_top_count = 0 # count frames for horse to stay in top air

# class made for storing obstacles information
class GameObjObstacle:
    def __init__(self, right_most, size=1):
        self.right_most = right_most
        if size == 1:
            self.size = 1
            self.left_most = right_most - 1
        elif size == 2:
            self.size = 2
            self.left_most = right_most - 3
        else: # size == 3
            self.size = 3
            self.left_most = right_most - 5

# class for game engine
class GameEngine:
    def __init__(self, diff=2):
        self.diff = diff # store the difficulty
        self.playable = True # variable to maintain the game loop
        self.render_buffer = []
        self.live_obstacles = [] # here stores all the live obstacles
        self.time_tick = time.clock()
        self.sleep_interval = 0.1

    # get environment information
    def SetUpEnv(self):
        # init an console helper
        self.console_helper = OSEasyConsole()
        self.console_helper.HideCursor()
        # get console size
        self.console_W, self.console_H = shutil.get_terminal_size() # (width, height)
        self.console_H -= 1 # reduce height by one for better view
        # check console size is valid
        if self.console_H < 8:
            print("Please increase the console height and try again")
            sys.exit(1)
        if self.console_W < 40:
            print("Please increase the console width and try again")
            sys.exit(1)
        # setup os specific keys
        self.key_jump = b" " if os.name == "nt" else " "
        self.key_quit = b"q" if os.name == "nt" else "q"
        # setup scene
        self.console_helper.MoveCursor((0, self.console_H-1))
        print(self.console_W*"=") # draw the ground
        horse_body = [
            "\\  [=]",
            " [--] ",
            " /  \\ "
        ]
        for i in range(len(horse_body)):
            self.console_helper.MoveCursor((0, self.console_H-4+i))
            print(horse_body[i])
        # init game objects
        self.horse = GameObjHorse(self.console_H-2)
        # init game score
        self.score = 0
        self.console_helper.MoveCursor((self.console_W-13, 0))
        print("Score = {0:04d}".format(self.score))

    # render the scene to the console
    # or simply update the scene
    def Render(self):
        for task in self.render_buffer:
            w, h = task[0]
            string = task[1]
            if w < 0:
                string = string[abs(w):]
                w = 0
            self.console_helper.MoveCursor((w, h))
            print(string)
        
        # reset buffer
        self.render_buffer = []
        self.console_helper.MoveCursor((0, 0))
        time.sleep(self.sleep_interval)
    
    # update by game logic
    def Update(self):
        # first update horse's feet animation
        if not self.horse.on_ground and self.horse.left_left:
            self.render_buffer.append([(0, self.horse.height), " \\  / "])
            self.horse.left_left = False # if in air, the feet should not move and point to right
        if self.horse.on_ground:
            if self.horse.left_left:
                self.render_buffer.append([(0, self.horse.height), " \\  / "])
                self.horse.left_left = False
            else:
                self.render_buffer.append([(0, self.horse.height), " /  \\ "])
                self.horse.left_left = True

        # check if the horse is going to jump
        if self.horse.on_ground and self.horse.jump:
            self.horse.jump = False
            self.horse.on_ground = False
            self.vel = 5 # give and initial velocity

        # now check conditions when in the air
        if not self.horse.on_ground:
            # jump => 5 => 4 => 3 => 2 => 1 => 0 => -1 => -2 => -3 => -4 => back to ground
            if self.vel == 0:
                self.horse.on_top_count += 1
                if self.horse.on_top_count > 5:
                    self.vel -= 1
                    self.horse.on_top_count = 0
                    self._MoveHorseUpDown(delta=-1)
            elif self.vel < 0:
                self._MoveHorseUpDown(delta=-1)
                if self.vel == -4:
                    self.horse.on_ground = True # if vel is -4, then the horse is back to the ground
                    self.vel = 0
                else:
                    self.vel -= 1
            else:
                self._MoveHorseUpDown(delta=1)
                self.vel -= 1

        # now check the obstacles
        if self.live_obstacles == [] or (self.console_W - self.live_obstacles[-1].right_most > random.randint(10+4*(4-self.diff), 15+6*(4-self.diff))):
            ob = GameObjObstacle(right_most=self.console_W-2, size=random.randint(1, 3))
            self.live_obstacles.append(ob)

        # now update obstacles
        self._MoveObstacle()
        if self.live_obstacles != [] and self.live_obstacles[0].right_most < 0:
            self.live_obstacles.pop(0) # remove the obstacle out from scene
        
        # finally update the score
        self.score += 1
        self.render_buffer.append([(self.console_W-13, 0), "Score = {0:04d}".format(self.score)])

        # update the time ticks
        # every 5 seconds, speed up the game
        if time.clock() - self.time_tick > 5.0:
            self.time_tick = time.clock()
            self.sleep_interval /= 10
            self.sleep_interval *= 9

    def _MoveHorseUpDown(self, delta=1):
        if delta == 0: return
        elif delta > 0: # move up
            self.render_buffer.append([(0, self.horse.height), 6*" "])
            self.horse.height -= 1
            self.render_buffer.append([(0, self.horse.height), " \\  /"])
            self.render_buffer.append([(0, self.horse.height-1), " [--] "])
            self.render_buffer.append([(0, self.horse.height-2), "\\  [=] "])
        else: # move down
            self.render_buffer.append([(0, self.horse.height-2), 6*" "])
            self.horse.height += 1
            self.render_buffer.append([(0, self.horse.height), " \\  / "])
            self.render_buffer.append([(0, self.horse.height-1), " [--] "])
            self.render_buffer.append([(0, self.horse.height-2), "\\  [=]"])

    def _MoveObstacle(self):
        for ob in self.live_obstacles:
            if ob.size == 1:
                self.render_buffer.append([(ob.left_most, self.console_H-2), "/\\ "])
            elif ob.size == 2:
                self.render_buffer.append([(ob.left_most, self.console_H-2), "/==\\ "])
                self.render_buffer.append([(ob.left_most+1, self.console_H-3), "/\\ "])
            else: # size == 3
                self.render_buffer.append([(ob.left_most, self.console_H-2), "/====\\ "])
                self.render_buffer.append([(ob.left_most+1, self.console_H-3), "/==\\ "])
                self.render_buffer.append([(ob.left_most+2, self.console_H-4), "/\\ "])
            ob.right_most -= 1
            ob.left_most -= 1

    # handle keyboard input
    def PollKeyEvents(self):
        ch = self.console_helper.GetChar()
        if ch is None: return # if no key press, continue

        if ch == self.key_quit:
            self.playable = False
        elif ch == self.key_jump:
            self.horse.jump = True

    def Quit(self):
        self.console_helper.ShowCursor() # restore cursor
        self.console_helper.MoveCursor((0, self.console_H))

if __name__ == "__main__":
    # get user defined game difficulty:
    diff = input("Please enter a difficulty from 1 to 3\nOr game will assign a random difficulty\n")
    if diff not in "123":
        diff = random.randint(1, 3)
    else:
        diff = int(diff[0])

    print("You chose difficulty:", diff)
    print("To exit the game, press \"q\"")

    time.sleep(1) # wait one second for user to read

    os.system("cls" if os.name == "nt" else "clear")

    game = GameEngine(diff)
    game.SetUpEnv()
    try:
        while(game.playable):
            game.Render()
            game.PollKeyEvents()
            game.Update()
    except KeyboardInterrupt:
        pass
    finally:
        game.Quit()
    print("Game is over! Your score is: {0}\nThanks for playing!".format(game.score))