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
except Exception:
    import curses

# helper class to make os specific calls easier
class OSEasyConsole:
    def __init__(self):
        if os.name == "nt":
            self.WinDll = ctypes.WinDLL("kernel32") # load kernel32.dll
            self.ConsoleHandler = self.WinDll.GetStdHandle(STD_OUTPUT_HANDLE) # get console standard handle
        else:
            self.stdscr = curses.initscr()
            self.stdscr.nodelay(1) # do not wait for key press
            curses.noecho() # turn on key echo
            curses.cbreak() # react to key press immediately

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
            curses.curs_set(False)

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
            curses.curs_set(True)

    def _WinMoveCursor(self, pos):
        self.WinDll.SetConsoleCursorPosition(self.ConsoleHandler, wintypes._COORD(pos[0], pos[1])) # make kernel32 c function call

    def _UnixMoveCursor(self, pos):
        print("\033[{0};{1}H".format(pos[1], pos[0]))
        #self.stdscr.move(pos[1], pos[0])

    def _WinGetCh(self):
        if msvcrt.kbhit(): # if there's a keyboard message waiting for read
            return msvcrt.getch() # read the key and return it
        else:
            return None

    def _UnixGetCh(self):
        try:
            c = self.stdscr.getkey()
        except Exception:
            return None # getch raise error if no key is pressed
        else:
            return c

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
        self.time_tick = time.process_time()
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
                self.render_buffer.append([(0, self.horse.height-2), "\\  [=]"])
                self.render_buffer.append([(0, self.horse.height-1), " [--] "])
                self.render_buffer.append([(0, self.horse.height), " \\  / "])
                self.horse.left_left = False
            else:
                self.render_buffer.append([(0, self.horse.height-2), "\\  [=]"])
                self.render_buffer.append([(0, self.horse.height-1), " [--] "])
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

        # check for any hit
        if self._AnyHit():
            self.playable = False
            time.sleep(1)
            return

        # now update obstacles
        self._MoveObstacle()
        if self.live_obstacles != [] and self.live_obstacles[0].right_most < 0:
            self.live_obstacles.pop(0) # remove the obstacle out from scene

        # finally update the score
        self.score += 1
        self.render_buffer.append([(self.console_W-13, 0), "Score = {0:04d}".format(self.score)])

        # update the time ticks
        # every 5 seconds, speed up the game
        if time.process_time() - self.time_tick > 5.0:
            self.time_tick = time.process_time()
            self.sleep_interval /= 10
            self.sleep_interval *= 9

        # if using curses, then need to draw the ground every frame
        if os.name != "nt":
            self.render_buffer.append([(0, self.console_H-1), self.console_W*"="])

    # helper function to move horse up or down
    def _MoveHorseUpDown(self, delta=1):
        if delta == 0: return
        elif delta > 0: # move up
            self.render_buffer.append([(0, self.horse.height), 6*" "])
            self.horse.height -= 1
            self.render_buffer.append([(0, self.horse.height), " \\  /"])
            self.render_buffer.append([(0, self.horse.height-1), " [--] "])
            if self.horse.height == self.console_H-7:
                self.render_buffer.append([(0, self.horse.height-2), "\\  [=] "])
            else:
                self.render_buffer.append([(0, self.horse.height-2), "_  [=] "])
        else: # move down
            self.render_buffer.append([(0, self.horse.height-2), 6*" "])
            self.horse.height += 1
            self.render_buffer.append([(0, self.horse.height), " \\  / "])
            self.render_buffer.append([(0, self.horse.height-1), " [--] "])
            if self.horse.height == self.console_H-2:
                self.render_buffer.append([(0, self.horse.height-2), "\\  [=]"])
            else:
                self.render_buffer.append([(0, self.horse.height-2), "|  [=]"])

    # helper function to move each obstacle 1 distance left
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

    # check for horse hit with obstacles
    def _AnyHit(self):
        if len(self.live_obstacles) >= 1:
            # first check with the nearest obstacle
            ob = self.live_obstacles[0]
            h = self.console_H - 2 - self.horse.height
            if h < ob.size:
                if ob.left_most <= (4-h) and ob.left_most > -(ob.size):
                    return True
                elif ob.right_most > h and ob.left_most <= -(ob.size):
                    return True
            if len(self.live_obstacles) >= 2:
                # next check with second nearest obstacle
                ob = self.live_obstacles[1]
                if h < ob.size:
                    if ob.left_most <= (4-h) and ob.left_most > -(ob.size):
                        return True
                    elif ob.right_most > h and ob.left_most <= -(ob.size):
                        return True
        return False

    # handle keyboard input
    def PollKeyEvents(self):
        ch = self.console_helper.GetChar()
        if ch is None: return # if no key press, continue

        if ch == self.key_quit:
            self.playable = False
        elif ch == self.key_jump:
            self.horse.jump = True

    # do the clean up and restore environment
    def Quit(self):
        self.console_helper.ShowCursor() # restore cursor
        self.console_helper.MoveCursor((0, self.console_H))
        if os.name != "nt":
            curses.nocbreak()
            curses.echo()
            curses.endwin()

if __name__ == "__main__":
    # get user defined game difficulty:
    diff = input("Please enter a difficulty from 1 to 3\nOr game will assign a random difficulty\n")
    if diff not in "123":
        diff = random.randint(1, 3) # if input is not valid, then random pick one difficulty
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

    # following codes are only created for fulfilling the assignment requirements
    # list comprehension here
    sample = [chr(x) for x in range(30, 50)]
    # dic comprehension here
    sample_dict = {x: chr(x) for x in range(40, 60)}