import pygame as pg
import numpy as np
import sys
import copy
import concurrent.futures
import threading
import random
import string
import time, datetime
from math import log, sqrt, factorial


class Button(object):
    def __init__(self, rect, command = None, position = None, text = None, fontsize = None, hover_text = None, clicked_text = None, disabled = False, **kwargs):
        self.rect = pg.Rect(rect)
        self.command = command
        self.disabled = disabled
        self.position = position
        self.clicked = False
        self.hovered = False
        self.process_kwargs(kwargs)
        self.parse_text(text, hover_text, clicked_text, InitRun = True, fontsize = fontsize)

    def resizefont(self, size=None):
        if size is None:
            size = self.rect.height
            while np.any(np.less(self.font.size(self.text), [0.95 * i for i in self.rect.size])):
              self.font = pg.font.Font(None, size)
              size +=1
            while np.any(np.greater(self.font.size(self.text), [0.95 * i for i in self.rect.size])):
              self.font = pg.font.Font(None, size)
              size -= 1
        else:
            self.font = pg.font.Font(None, size)
        self.fontsize = size

    def parse_text(self, text, hover_text = None, clicked_text = None, InitRun = False, fontsize = None):
        if InitRun:
            self.text = text
            if self.text != " ":
                self.resizefont(size = fontsize)
            else:
                self.fontsize = fontsize
            if hover_text:
              self.hover_text = hover_text
            else:
              self.hover_text = self.text
            if clicked_text:
              self.clicked_text = clicked_text
            else:
              self.clicked_text = self.text
        if text != self.text:
            self.text = text
        if hover_text is None:
            self.hover_text = self.text
        elif hover_text != self.hover_text:
            self.hover_text = hover_text
        if clicked_text is None:
            self.clicked_text = self.text
        elif clicked_text != self.clicked_text:
            self.clicked_text = clicked_text
        self.render_text()

    def render_text(self):
        if self.hover_font_color:
          color = self.hover_font_color
          self.hover_text_render = self.font.render(self.hover_text, True, color)
        if self.clicked_font_color:
          color = self.clicked_font_color
          self.clicked_text_render = self.font.render(self.clicked_text, True, color)
        self.text_render = self.font.render(self.text, True, self.font_color)

    def process_kwargs(self, kwargs):
        settings = {
          "color": pg.Color('white'),
          "clicked_text_render":None,
          "hover_text_render":None,
          "font": pg.font.SysFont(None, 72),
          "call_on_release": True,
          "hover_color": None,
          "clicked_color": None,
          "font_color": pg.Color('black'),
          "hover_font_color": None,
          "clicked_font_color": None,
          "click_sound": None,
          "hover_sound": None,
          'border_color': pg.Color('black'),
          'border_hover_color': pg.Color('yellow'),
          'disabled': False,
          'disabled_color': pg.Color('grey'),
          'radius': 3,
        }
        for kwarg in kwargs:
          if kwarg in settings:
            settings[kwarg] = kwargs[kwarg]
          else:
            raise AttributeError("{} has no keyword: {}".format(self.__class__.__name__, kwarg))
        self.__dict__.update(settings)

    def get_event(self, event):
        if not self.disabled:
            if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                self.on_click(event)
            elif event.type == pg.MOUSEBUTTONUP and event.button == 1:
                self.on_release(event)

    def on_click(self, event):
        if self.rect.collidepoint(event.pos):
            self.clicked = True

    def on_release(self, event):
        if self.clicked and self.call_on_release:
            if self.rect.collidepoint(pg.mouse.get_pos()):
                self.command()
            self.clicked = False

    def check_hover(self):
        if self.rect.collidepoint(pg.mouse.get_pos()):
          if not self.hovered:
            self.hovered = True
            if self.hover_sound:
              self.hover_sound.play()
        else:
          self.hovered = False

    def draw(self, surface):
        color = self.color
        text = self.text_render
        border = self.border_color
        self.check_hover()
        if not self.disabled:
          if self.clicked:
            color = self.clicked_color
            if self.clicked_font_color:
              text = self.clicked_text_render
          elif self.hovered and self.hover_color:
            color = self.hover_color
            if self.hover_font_color:
              text = self.hover_text_render
          if self.hovered and not self.clicked:
            border = self.border_hover_color
        else:
          color = self.disabled_color
        if self.radius:
          rad = self.radius
        else:
          rad = 0
        self.round_rect(surface, self.rect, border, rad, 1, color)
        if text:
          text_rect = text.get_rect(center = self.rect.center)
          surface.blit(text, text_rect)

    def round_rect(self, surface, rect, color, rad = 20, border = 0, inside = (0, 0, 0, 0)):
        rect = pg.Rect(rect)
        zeroed_rect = rect.copy()
        zeroed_rect.topleft = 0, 0
        image = pg.Surface(rect.size).convert_alpha()
        image.fill((0, 0, 0, 0))
        self._render_region(image, zeroed_rect, color, rad)
        if border:
          zeroed_rect.inflate_ip(-2 * border, -2 * border)
          self._render_region(image, zeroed_rect, inside, rad)
        surface.blit(image, rect)

    def _render_region(self, image, rect, color, rad):
        corners = rect.inflate(-2 * rad, -2 * rad)
        for attribute in ("topleft", "topright", "bottomleft", "bottomright"):
          pg.draw.circle(image, color, getattr(corners, attribute), rad)
        image.fill(color, rect.inflate(-2 * rad, 0))
        image.fill(color, rect.inflate(0, -2 * rad))


class Slider(object):
    def __init__(self, rect, sliderrectsize, startingvalue, command, slideroffset = None, text = None, hover_text = None, clicked_text = None, xlimit = None, ylimit = None, valuerange = (0,0), *args, **kwargs):
        self.rect = pg.Rect(rect)
        self.command = command
        self.startingvalue = startingvalue
        self.nearestnotch = startingvalue
        self.valuerange = valuerange
        self.notches = valuerange[1] - valuerange[0]
        self.clicked = False
        self.hovered = False
        self.parse_text(text,hover_text,clicked_text)
        self.set_limits(xlimit,ylimit,slideroffset)
        self.createsliderlines()
        self.sliderrectsize = sliderrectsize
        self.set_notches(self.sliderrectsize)
        self.sliderrect = pg.Rect(tuple(np.subtract(self.notchpoints[self.startingvalue],tuple([i/2 for i in self.sliderrectsize])))+sliderrectsize)
        self.process_kwargs(kwargs)
        self.resizefont()
        self.render_text()

    def createsliderlines(self):
        self.endpoints = list(tuple(zip(self.xlimit, self.ylimit)))
        self.gradient = np.subtract(self.endpoints[1], self.endpoints[0]) / np.linalg.norm(
            np.subtract(self.endpoints[1], self.endpoints[0]))
        self.perpgradient = (self.gradient[1], -self.gradient[0])

    def set_limits(self,xlimit,ylimit,slideroffset):
        if xlimit is not None:
          self.xlimit = xlimit
        else:
          self.xlimit = (self.rect.centerx+slideroffset[0],self.rect.centerx+slideroffset[0])
        if ylimit is not None:
          self.ylimit = ylimit
        else:
          self.ylimit = (self.rect.centery+slideroffset[1],self.rect.centery+slideroffset[1])

    def set_notches(self, sliderrectsize):
        increment = np.subtract(self.endpoints[1],self.endpoints[0])/self.notches
        linewidth = tuple([i * int(sliderrectsize[1] / 2) for i in self.perpgradient])
        self.notchlines = {}
        self.notchpoints = {}
        notchnumber = 0
        for notch in np.arange(self.valuerange[0],self.valuerange[1]+1):
          self.notchpoints[notch] = tuple(self.endpoints[0]+increment*notchnumber)
          self.notchlines[notch] = [(self.endpoints[0]+increment*notchnumber+linewidth),(self.endpoints[0]+increment*notchnumber-linewidth)]
          notchnumber += 1

    def findnearestnotch(self, position):
        notchdistances = {np.linalg.norm(np.subtract(value[1], position)):value[0] for value in self.notchpoints.items()}
        self.nearestnotch = notchdistances[min(notchdistances.keys())]
        return self.nearestnotch

    def movetonotch(self, rect, notchvalue):
        rect = rect.move(np.subtract(self.notchpoints[notchvalue], rect.center))
        return rect

    def resizefont(self, size=None):
          if size is None:
              size = self.rect.height
              while np.any(np.less(self.font.size(self.text),[0.95*i for i in self.rect.size])):
                self.font = pg.font.Font(None,size)
                size += 1
              while np.any(np.greater(self.font.size(self.text),[0.95*i for i in self.rect.size])):
                self.font = pg.font.Font(None,size)
                size -= 1
          else:
              self.font = pg.font.Font(None, size)
          self.fontsize = size

    def parse_text(self,text,hover_text,clicked_text):
        if text:
          self.text = text
        else:
          self.text = ""
        if hover_text:
          self.hover_text = hover_text
        else:
          self.hover_text = self.text
        if clicked_text:
          self.clicked_text = clicked_text
        else:
          self.clicked_text = self.text

    def process_kwargs(self, kwargs):
        settings = {
          "color": pg.Color('white'),
          "clicked_text_render":None,
          "hover_text_render":None,
          "font": pg.font.SysFont(None, 50),
          "call_on_release": True,
          "hover_color": None,
          "clicked_color": None,
          "font_color": pg.Color('black'),
          "hover_font_color": None,
          "clicked_font_color": None,
          "click_sound": None,
          "hover_sound": None,
          'border_color': pg.Color('black'),
          'border_hover_color': pg.Color('yellow'),
          'disabled': False,
          'disabled_color': pg.Color('grey'),
          'radius': 3,
        }
        for kwarg in kwargs:
          if kwarg in settings:
            settings[kwarg] = kwargs[kwarg]
          else:
            raise AttributeError("{} has no keyword: {}".format(self.__class__.__name__, kwarg))
        self.__dict__.update(settings)

    def render_text(self):
        if self.hover_font_color:
            color = self.hover_font_color
            self.hover_text_render = self.font.render(self.hover_text, True, color)
        if self.clicked_font_color:
            color = self.clicked_font_color
            self.clicked_text_render = self.font.render(self.clicked_text, True, color)
        self.text_render = self.font.render(self.text, True, self.font_color)

    def get_event(self, event):
        if event.type  ==  pg.MOUSEBUTTONDOWN and event.button  ==  1:
          self.on_click(event)
        elif event.type  ==  pg.MOUSEBUTTONUP and event.button  ==  1:
          self.on_release(event)

    def on_click(self, event):
        if self.sliderrect.collidepoint(event.pos):
            self.clicked = True

    def on_release(self, event):
        if self.clicked and self.call_on_release:
          #  if user is still within button rect upon mouse release
          if pg.mouse.get_rel():
            self.command(self.nearestnotch)
        self.clicked = False

    def check_hover(self):
        if self.sliderrect.collidepoint(pg.mouse.get_pos()):
          if not self.hovered:
            self.hovered = True
            if self.hover_sound:
              self.hover_sound.play()
        else:
          self.hovered = False

    def draw(self, surface):
        color = self.color
        text = self.text_render
        border = self.border_color
        self.check_hover()
        if not self.disabled:
          if self.clicked:
            color = self.clicked_color
            if self.clicked_font_color:
              text = self.clicked_text_render
          elif self.hovered and self.hover_color:
            color = self.hover_color
            if self.hover_font_color:
              text = self.hover_text_render
          if self.hovered and not self.clicked:
            border = self.border_hover_color
        else:
          color = self.disabled_color
        pg.draw.line(surface, color, self.endpoints[0],self.endpoints[1])
        for notch in self.notchlines:
          pg.draw.line(surface, color, self.notchlines[notch][0], self.notchlines[notch][1])
        if self.radius:
          rad = self.radius
        else:
          rad = 0
        self.round_rect(surface, self.rect, border, rad, 1, color)
        self.round_rect(surface, self.sliderrect, border, rad, 1, color)
        if text:
          text_rect = text.get_rect(center = self.rect.center)
          surface.blit(text, text_rect)

    def round_rect(self, surface, rect, color, rad = 20, border = 0, inside = (0, 0, 0, 0)):
        rect = pg.Rect(rect)
        zeroed_rect = rect.copy()
        zeroed_rect.topleft = 0, 0
        image = pg.Surface(rect.size).convert_alpha()
        image.fill((0, 0, 0, 0))
        self._render_region(image, zeroed_rect, color, rad)
        if border:
          zeroed_rect.inflate_ip(-2 * border, -2 * border)
          self._render_region(image, zeroed_rect, inside, rad)
        surface.blit(image, rect)

    def _render_region(self, image, rect, color, rad):
        corners = rect.inflate(-2 * rad, -2 * rad)
        for attribute in ("topleft", "topright", "bottomleft", "bottomright"):
            pg.draw.circle(image, color, getattr(corners, attribute), rad)
        image.fill(color, rect.inflate(-2 * rad, 0))
        image.fill(color, rect.inflate(0, -2 * rad))


class GameBoard:
    def __init__(self, VariablesDict):
        self.VariablesDict = VariablesDict
        self.boardsize = VariablesDict["Board Width"]["value"]
        self.positions = np.full((self.boardsize, self.boardsize), " ", 'U1')
        self.numplayers = VariablesDict["Total Players"]["value"]
        self.winlinelen = VariablesDict["Winning Line"]["value"]
        self.humanplayers = VariablesDict["Human Players"]["value"]
        self.gametokens = [" ", "X", "O"]

        self.actiontracker = []

        if self.numplayers > 2:
            for i in range(2, self.numplayers):
                self.addtoken()

        self.TurnNum = 0
        self.humanturnnums = np.sort(np.random.choice(self.numplayers, self.humanplayers, replace = False))
        self.AITurnNums = [turns for turns in np.arange(self.numplayers) if turns not in self.humanturnnums]

    def addtoken(self):
        self.gametokens.append(random.choice([i for i in string.ascii_uppercase if i not in self.gametokens]))

    def playernum(self, playerindex):
        return playerindex + 1

    def previousturnnum(self):
        return (self.TurnNum - 1) % self.numplayers

    def playertoken(self, playerindex):
        return self.gametokens[self.playernum(playerindex)]

    def availablepositions(self):
        AvailablePositionsArray = np.asarray(np.where((self.positions == self.gametokens[0]) == True))
        AvailablePositionsTuples = []
        for col in range(0, AvailablePositionsArray.shape[1]):
          AvailablePositionsTuples.append(tuple(AvailablePositionsArray[:, col]))
        return AvailablePositionsTuples

    def adjustedposition(self, position):
        return tuple(np.subtract(position, 1))

    def next_turn(self, turn):
        return (self.TurnNum + 1) % self.numplayers

    def makenextplay(self, action):
        if self.positions[action] == self.gametokens[0]:
            self.positions[action] = self.gametokens[self.playernum(self.TurnNum)]
            self.TurnNum = self.next_turn(self.TurnNum)
            self.actiontracker.append((len(self.actiontracker), self.gametokens[self.playernum(self.TurnNum)], action))
        else:
            return False

    def copy(self):
        return self.boardsize, self.numplayers, self.winlinelen, self.humanplayers


    @staticmethod
    def findsubarray(array, subarray):
        if array.tostring().find(subarray.tostring()) != -1:
          return True
        else:
          return False

    def rowcheck(self, type, i):
        return self.findsubarray(self.positions[i, :], np.resize(np.array(type), self.winlinelen))

    def colcheck(self, type, i):
        return self.findsubarray(self.positions[:, i], np.resize(np.array(type), self.winlinelen))

    def diagcheck(self, type, i):
        return self.findsubarray(np.diagonal(self.positions, i), np.resize(np.array(type), self.winlinelen))

    def oppdiagcheck(self, type, i):
        return self.findsubarray(np.diagonal(np.fliplr(self.positions), i), np.resize(np.array(type), self.winlinelen))

    def endgame(self):
        for i in range(0, self.boardsize):
            if self.rowcheck(self.playertoken(self.previousturnnum()), i) or self.colcheck(self.playertoken(self.previousturnnum()), i):
                return self.playernum(self.previousturnnum())
        for i in range(-self.boardsize + self.winlinelen, self.boardsize + 1 - self.winlinelen):
            if self.diagcheck(self.playertoken(self.previousturnnum()), i) or self.oppdiagcheck(self.playertoken(self.previousturnnum()),i):
                return self.playernum(self.previousturnnum())
        if len(self.availablepositions()) == 0:
            return 0
        else:
            return -1


class Node:
    def __init__(self, TreeLevel, action=None, parent=None, board=None):
        self.parent = parent
        self.board = copy.deepcopy(board)
        if action is not None:
            self.board.makenextplay(action)
        self.children = []
        self.score = 0
        self.visits = 0
        self.TreeLevel = TreeLevel
        self.untried_actions = self.board.availablepositions()
        self.action = action

    def select(self):
        s = sorted(self.children, key=lambda c: c.score / c.visits + 0.2 * sqrt(2 * log(self.visits) / c.visits))
        s[-1].score -= 1
        return s[-1]

    def expand(self, action):
        child = Node(TreeLevel=self.TreeLevel + 1, parent=self, action=action, board=self.board)
        self.children.append(child)
        self.untried_actions.remove(action)
        return child

    def update(self, result):
        self.visits += 1
        self.score += result + 1


def UCTIteration(node, player, lock):
    start = time.time()

    #  expansion - expand parent to a random untried action
    if len(node.untried_actions) > 0:
        #  simulation - rollout to terminal state from current
        #  state using random actions
        while node.board.endgame() < 0:
            action = random.choice(node.untried_actions)
            lock.acquire()
            node = node.expand(action)
            lock.release()

    #  back propagation - propagate result of rollout game up the tree
    #  reverse the result if player at the node lost the rollout game
    if node.board.endgame() >= 0:
        #  result = node.board.endgame() / node.TreeLevel
        result = 0
        if node.board.endgame() != 0:
            if node.board.endgame() == player:
                result = 1 / node.TreeLevel
            else:
                result = -2 / node.TreeLevel
        while node is not None:
            lock.acquire()
            node.update(result)
            lock.release()
            #  print("Level", node.TreeLevel,"Result", result,node.board.positions)
            node = node.parent


def UpdateRootNode(rootstate, player, lock):
    global root
    newroot = root[player]

    while len(newroot.board.actiontracker) < len(rootstate.actiontracker):
        if newroot.children:
            child = [child for child in newroot.children if child.action == rootstate.actiontracker[len(newroot.board.actiontracker)][2]]
            if len(child) > 0:
                child = child[0]
        else:
            child = newroot.expand(rootstate.actiontracker[len(newroot.board.actiontracker)][2])
        if child:
            newroot = child

    return newroot


def SelectNode(root, player, lock, executor):
    node = root
    #  selection - select best child if parent fully expanded and not terminal
    while not node.untried_actions and node.children:
        lock.acquire()
        node = node.select()
        lock.release()
    executor.submit(UCTIteration(node, player, lock))


def PickOpponentMove(root):
    s = sorted(root.children, key=lambda c: c.score / c.visits)

    for child in root.children:
        print("Visits", child.visits, "score", child.score, "\n", child.board.positions)

    return tuple(s[-1].action)


def ResetBoardFunc():
    global GameResetBoolean
    GameResetBoolean = True


def ChangeBoardSizeFunc(newsize):
    global GameVariablesDict
    GameVariablesDict["Board Width"]["value"] = newsize


def ChangeWinningLineFunc(newlength):
    global GameVariablesDict
    GameVariablesDict["Winning Line"]["value"] = newlength


def ChangePlayerCountFunc(newplayers):
    global GameVariablesDict
    GameVariablesDict["Total Players"]["value"] = newplayers
    if newplayers < GameVariablesDict["Human Players"]["value"]:
        ChangeHumanPlayerCountFunc(newplayers)


def ChangeHumanPlayerCountFunc(newhumanplayers):
    global GameVariablesDict
    GameVariablesDict["Human Players"]["value"] = newhumanplayers
    if newhumanplayers > GameVariablesDict["Total Players"]["value"]:
        ChangePlayerCountFunc(newhumanplayers)


def ChangeDifficultyFunc(newdifficulty):
    global GameVariablesDict
    GameVariablesDict["Difficulty"]["value"] = newdifficulty


def CreateButtonsFunc(boardsize):
    global btns, screensize, board
    if btns != []:
        del btns
    btns = []
    btn_height = min(screensize[0] * 3 / 4, screensize[1]) / boardsize
    btn_width = btn_height
    for row in range(0, boardsize):
        for col in range(0, boardsize):
            top = btn_height * row
            left = btn_width * col
            if row+col == 0:
                b = Button(rect = (left, top, btn_width, btn_height), text = "X", command = lambda l = (row,col): board.makenextplay(l), position = (row,col), **buttonsettings)
                btns.append(b)
                fontsize = b.fontsize
            else:
                b = Button(rect=(left, top, btn_width, btn_height), text="X", fontsize = fontsize,
                         command=lambda l=(row, col): board.makenextplay(l), position=(row, col), **buttonsettings)
                btns.append(b)
    b = Button(rect=(screensize[0] * 61/80-80, screensize[1]-130, 300, 100),
               command=ResetBoardFunc, text="Restart", **buttonsettings)
    btns.append(b)


def CreateSlidersFunc(availablerect, labelsize, sliderrectsize):
    global slds
    global GameVariablesDict
    if slds != {}:
        slds = {}

    labelposition = np.subtract((int(availablerect[0]+availablerect[2]*1/2),int(availablerect[1]+availablerect[3] * 1 / 20)),[int(0.5*i) for i in labelsize])
    xlimit = np.add((availablerect[2]*1/10,availablerect[2]*9/10),availablerect[0])
    ylimit = (labelposition[1] + labelsize[1] + sliderrectsize[1]*1/2 ,)*2
    slidernumber = 0
    totalsliders = len(GameVariablesDict.keys()) + 1
    increment = int(availablerect[3]/totalsliders)

    for key in GameVariablesDict.keys():
        s = Slider(rect=(labelposition[0],labelposition[1]+slidernumber*increment+10)+labelsize, sliderrectsize=sliderrectsize,
                   startingvalue=GameVariablesDict[key]["value"], command=GameVariablesDict[key]["function"], text=key, xlimit=xlimit,
                   ylimit=np.add(ylimit, slidernumber*increment+10), valuerange=GameVariablesDict[key]["range"], **slidersettings)
        slds[key] = s
        slidernumber += 1


def CreateDisplayWindowsFunc(sliders):
    global wndws, screensize
    wndws = {}
    firstsliderbool = True
    for key in sliders.keys():
        rect = sliders[key].rect
        rectposition = rect.topleft
        windowrect = (rectposition[0]+rect.size[0]+30, rectposition[1], 40, rect.size[1])
        if firstsliderbool:
            window = Button(windowrect, text = str(sliders[key].startingvalue), disabled=True, **buttonsettings)
            wndws[key] = window
            fontsize = window.fontsize
        else:
            window = Button(windowrect, text=str(sliders[key].startingvalue), fontsize=fontsize, disabled=True, **buttonsettings)
            wndws[key] = window

    currentturnrect = (screensize[1], 0, screensize[0]-screensize[1], 150)
    wndws["Current Turn"] = Button(currentturnrect, text="Player 1's turn", disabled=True, **buttonsettings)


def CreateWinScreenFunc(screensize, board):
    global btns, slds, wndws, EndGameScreenBool
    btns = []
    slds = {}
    wndws = {}

    if board.endgame()  ==  0:
        victorytext = "Stalemate"
    else:
        if board.previousturnnum() in board.humanturnnums:
            victorytext = "Human player "+ str(board.playernum(list(board.humanturnnums).index(board.previousturnnum())))+" wins!"
        else:
            victorytext = "Player "+ str(board.playernum(board.previousturnnum()))+ " wins!"

    window = Button(rect = (0, screensize[1]*3/8, screensize[0], screensize[1]*1/4), text = victorytext, disabled = True, **buttonsettings)
    wndws["End Game"] = window
    b = Button(rect = (screensize[0] * 1/2-150, screensize[1]*5/8, 300, 100), command = ResetBoardFunc, text = "Restart",
               **buttonsettings)
    btns.append(b)
    EndGameScreenBool = True


def GameResetFunc():
    global screen, factor
    global btns, slds, wndws
    global GameVariablesDict, GameOver, GameResetBoolean, EndGameScreenBool
    global board, boardsim, root, turn, iterations, OpponentIterations

    screen.fill(pg.Color("Black"))
    factor = board.boardsize / GameVariablesDict["Board Width"]["value"] - 1

    board = GameBoard(GameVariablesDict)
    boardsim = CopyBoard(board)
    root = CreateRootNodes()
    OpponentIterations = CalculateAIIterations(GameVariablesDict)

    CreateButtonsFunc(GameVariablesDict["Board Width"]["value"])
    CreateSlidersFunc(
        (screensize[1], screensize[1] * 1 / 8, screensize[0] - screensize[1], screensize[1] * 9 / 10),
        labelsize=(150, 50), sliderrectsize=(10, 50))
    CreateDisplayWindowsFunc(slds)

    GameResetBoolean = False
    EndGameScreenBool = False
    turn = -1
    iterations = 0
    GameOver = -1


def ScreenUpdate():
    global screen
    global screensize, factor
    global btns, slds, wndws
    global GameVariablesDict, GameOver
    global board, turn

    screen.fill(pg.Color("Black"))
    mouse = pg.mouse.get_pos()
    for event in pg.event.get():
        if event.type == pg.QUIT:
            pg.quit()
            sys.exit(0)
        if event.type == pg.VIDEORESIZE and screensize != event.size:
            factor = np.subtract(np.divide(event.size, screensize), 1)
            screensize = event.size
            for btn in btns:
                btn.rect = btn.rect.inflate(btn.rect.size * factor)
                btn.rect = btn.rect.move(btn.rect.center * factor)
                btn.resizefont(size=int(btn.fontsize * (1 + np.min(factor))))
            for sld in slds.values():
                sld.rect = sld.rect.inflate(sld.rect.size * factor)
                sld.sliderrect = sld.sliderrect.inflate(sld.sliderrect.size * factor)
                sld.rect = sld.rect.move(sld.rect.center * factor)
                sld.sliderrect = sld.sliderrect.move(sld.sliderrect.center * factor)
                sld.xlimit = sld.xlimit * (1 + factor[0])
                sld.ylimit = sld.ylimit * (1 + factor[1])
                sld.createsliderlines()
                sld.set_notches(sld.sliderrect.size)
                sld.resizefont(size=int(sld.fontsize * (1 + np.min(factor))))
            for wndw in wndws.values():
                wndw.rect = wndw.rect.inflate(wndw.rect.size * factor)
                wndw.rect = wndw.rect.move(wndw.rect.center * factor)
                wndw.resizefont(size=int(wndw.fontsize * (1 + 2 * np.min(factor))))
            screencopy = screen.copy()
            screen = pg.display.set_mode(screensize, pg.RESIZABLE)
            screen.blit(screencopy, (0, 0))
        for btn in btns:
            btn.get_event(event)
            if btn.position:
                if board.positions[btn.position] == " " and turn in board.humanturnnums:
                    btn.parse_text(text=board.positions[btn.position], hover_text=board.playertoken(turn),
                                   clicked_text=board.playertoken(turn))
                else:
                    btn.parse_text(text=board.positions[btn.position], hover_text=board.positions[btn.position],
                                   clicked_text=board.positions[btn.position])
            btn.draw(screen)
        for key in slds.keys():
            slds[key].get_event(event)
            if slds[key].clicked:
                notchvalue = slds[key].findnearestnotch(mouse)
                slds[key].sliderrect = slds[key].movetonotch(slds[key].sliderrect, notchvalue)
                wndws[key].parse_text(str(notchvalue))
            elif slds[key].nearestnotch != GameVariablesDict[key]["value"]:
                notchvalue = GameVariablesDict[key]["value"]
                slds[key].sliderrect = slds[key].movetonotch(slds[key].sliderrect, notchvalue)
                wndws[key].parse_text(str(notchvalue))
            slds[key].draw(screen)

        for wndw in wndws.values():
            wndw.draw(screen)
        pg.display.update()


def CalculateAIIterations(GameVariablesDict):
    return int(GameVariablesDict["Difficulty"]["value"]*(GameVariablesDict["Board Width"]["value"]**2)*5)


def CreateRootNodes():
    try:
        global root
    except Exception:
        pass
    rootcopy = Node(board=boardsim, TreeLevel=1)
    root = {}
    for turn in board.AITurnNums:
        root[board.playernum(turn)] = rootcopy
    return root


def CopyBoard(board):
    boardcopy = GameBoard(board.VariablesDict)
    boardcopy.gametokens = board.gametokens
    return boardcopy


btns = []
slds = {}
wndws = {}

if __name__  ==  '__main__':
    pg.init()

    slidersettings = {
        "clicked_font_color": (0, 0, 0),
        "clicked_color": (255, 255, 255),
        "hover_font_color": (0, 0, 0),
        "hover_color": (255, 255, 235),
        'font': pg.font.Font(None, 30),
        'font_color': (0, 0, 0),
        'border_color': (0, 0, 0),
    }
    buttonsettings = {
        "clicked_font_color": (0, 0, 0),
        "clicked_color": (255, 255, 255),
        "hover_font_color": (0, 0, 0),
        "hover_color": (255, 255, 235),
        'font': pg.font.Font(None, 250),
        'font_color': (0, 0, 0),
        'border_color': (0, 0, 0),
    }
    GameVariablesDict = {
        "Board Width": {"function": ChangeBoardSizeFunc, "range": (3, 8), "value": 3},
        "Winning Line": {"function": ChangeWinningLineFunc, "range": (2, 8), "value": 3},
        "Total Players": {"function": ChangePlayerCountFunc, "range": (2, 8), "value": 2},
        "Human Players": {"function": ChangeHumanPlayerCountFunc, "range": (0, 8), "value": 1},
        "Difficulty": {"function": ChangeDifficultyFunc, "range": (1, 10), "value": 5},
    }

    GameClock = pg.time.Clock()
    GameResetBoolean = False
    EndGameScreenBool = False
    turn = -1
    screensize = (1920, 1080)

    screen = pg.display.set_mode(screensize, pg.RESIZABLE)
    pg.display.set_caption("Noughts and Crosses")
    screen_rect = screen.get_rect()
    fps_int = 60
    refresh_time = datetime.timedelta(seconds=1)/fps_int

    CreateSlidersFunc((screensize[1], screensize[1]*1/8, screensize[0]-screensize[1], screensize[1]*8/10),
                      labelsize=(150, 50), sliderrectsize=(10, 50))
    CreateButtonsFunc(GameVariablesDict["Board Width"]["value"])
    CreateDisplayWindowsFunc(slds)

    board = GameBoard(GameVariablesDict)
    GameOver = board.endgame()

    #  Create a copy of the board for the UCT algorithm to modify
    boardsim = CopyBoard(board)

    #  Create the top level node for all simulations of board states
    root = CreateRootNodes()

    OpponentIterations = CalculateAIIterations(GameVariablesDict)
    iterations = 0
    lock = threading.RLock()

    with concurrent.futures.ThreadPoolExecutor() as executor:
        while True:
            executor.submit(ScreenUpdate())
            GameOver = board.endgame()
            if GameOver != -1:
                if not EndGameScreenBool:
                    CreateWinScreenFunc(screensize, board)
                    for btn in btns:
                        btn.disabled = False
            else:
                if turn != board.TurnNum:
                    turn = board.TurnNum
                    if wndws["Current Turn"]:
                        turntext = "Player " + str(board.playernum(board.TurnNum)) + "'s turn"
                        wndws["Current Turn"].parse_text(turntext)
                    for btn in btns:
                        if turn not in board.humanturnnums:
                            btn.disabled = True
                        else:
                            btn.disabled = False

                    current_turn = board.TurnNum
                    while current_turn not in board.AITurnNums:
                        current_turn = board.next_turn(current_turn)
                    player = board.playernum(current_turn)
                    newroot = UpdateRootNode(board, player, lock)

                if newroot.visits > OpponentIterations and turn in board.AITurnNums:
                    print("Opponent Turn")
                    Opponent_play = PickOpponentMove(newroot)
                    board.makenextplay(Opponent_play)
                    iterations += 1

                loop_start_time = datetime.datetime.now()
                while datetime.datetime.now() - loop_start_time < refresh_time:
                    executor.submit(SelectNode(newroot, player, lock, executor))
                    iterations += 1

            if GameResetBoolean:
                GameResetFunc()
                
