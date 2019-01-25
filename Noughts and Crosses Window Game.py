import pygame as pg
import numpy as np
import sys
import copy
import concurrent.futures
import threading
from PyQt5.QtWidgets import QApplication, QColorDialog
from PyQt5.QtGui import QColor
import random
import string
import time
import datetime
from math import log, sqrt


class Button(object):
    def __init__(self, rect, command=None, position=None, text=None, fontsize=None, hover_text=None,
                 clicked_text=None, disabled=False, **kwargs):
        self.rect = pg.Rect(rect)
        self.command = command
        self.disabled = disabled
        self.position = position
        self.clicked = False
        self.hovered = False
        self.process_kwargs(kwargs)
        self.parse_text(text, hover_text, clicked_text, InitRun=True, fontsize=fontsize)

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

    def parse_text(self, text, hover_text=None, clicked_text=None, InitRun=False, fontsize=None):
        if InitRun:
            self.text = text
            if self.text != " ":
                self.resizefont(size=fontsize)
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
        if self.hover_font_colour:
            colour = self.hover_font_colour
            self.hover_text_render = self.font.render(self.hover_text, True, colour)
        if self.clicked_font_colour:
            colour = self.clicked_font_colour
            self.clicked_text_render = self.font.render(self.clicked_text, True, colour)
        self.text_render = self.font.render(self.text, True, self.font_colour)

    def process_kwargs(self, kwargs):
        settings = {
          "colour": pg.Color('white'),
          "clicked_text_render":None,
          "hover_text_render":None,
          "font": pg.font.SysFont(None, 72),
          "call_on_release": True,
          "hover_colour": None,
          "clicked_colour": None,
          "font_colour": pg.Color('black'),
          "hover_font_colour": None,
          "clicked_font_colour": None,
          "click_sound": None,
          "hover_sound": None,
          'border_colour': pg.Color('black'),
          'border_hover_colour': pg.Color('yellow'),
          'disabled': False,
          'disabled_colour': pg.Color('grey'),
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
                self.on_release()

    def on_click(self, event):
        if self.rect.collidepoint(event.pos):
            self.clicked = True

    def on_release(self):
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
        colour = self.colour
        text = self.text_render
        border = self.border_colour
        self.check_hover()
        if not self.disabled:
            if self.clicked:
                colour = self.clicked_colour
                if self.clicked_font_colour:
                    text = self.clicked_text_render
            elif self.hovered and self.hover_colour:
                colour = self.hover_colour
                if self.hover_font_colour:
                    text = self.hover_text_render
            if self.hovered and not self.clicked:
                border = self.border_hover_colour
        else:
            colour = self.disabled_colour
        if self.radius:
            rad = self.radius
        else:
            rad = 0
        self.round_rect(surface, self.rect, border, rad, 1, colour)
        if text:
            text_rect = text.get_rect(center=self.rect.center)
            surface.blit(text, text_rect)

    def round_rect(self, surface, rect, colour, rad=20, border=0, inside=(0, 0, 0, 0)):
        rect = pg.Rect(rect)
        zeroed_rect = rect.copy()
        zeroed_rect.topleft = 0, 0
        image = pg.Surface(rect.size).convert_alpha()
        image.fill((0, 0, 0, 0))
        self._render_region(image, zeroed_rect, colour, rad)
        if border:
            zeroed_rect.inflate_ip(-2 * border, -2 * border)
            self._render_region(image, zeroed_rect, inside, rad)
        surface.blit(image, rect)

    def _render_region(self, image, rect, colour, rad):
        corners = rect.inflate(-2 * rad, -2 * rad)
        for attribute in ("topleft", "topright", "bottomleft", "bottomright"):
            pg.draw.circle(image, colour, getattr(corners, attribute), rad)
        image.fill(colour, rect.inflate(-2 * rad, 0))
        image.fill(colour, rect.inflate(0, -2 * rad))


class Slider(object):
    def __init__(self, rect, sliderrectsize, startingvalue, command, slideroffset=None, text=None, hover_text=None, 
                 clicked_text=None, xlimit=None, ylimit=None, valuerange=(0, 0), slider_player=None, **kwargs):
        self.rect = pg.Rect(rect)
        self.command = command
        self.slider_player = slider_player
        self.startingvalue = startingvalue
        self.nearest_notch_value = startingvalue
        self.valuerange = valuerange
        self.notches = valuerange[1] - valuerange[0]
        self.clicked = False
        self.hovered = False
        self.parse_text(text, hover_text, clicked_text)
        self.set_limits(xlimit, ylimit, slideroffset)
        self.createsliderlines()
        self.sliderrectsize = sliderrectsize
        self.set_notches(self.sliderrectsize)
        self.sliderrect = pg.Rect(tuple(np.subtract(self.notchpoints[self.startingvalue], 
                                                    tuple([i/2 for i in self.sliderrectsize])))+sliderrectsize)
        self.process_kwargs(kwargs)
        self.resizefont()
        self.render_text()

    def createsliderlines(self):
        self.endpoints = list(tuple(zip(self.xlimit, self.ylimit)))
        self.gradient = np.subtract(self.endpoints[1], self.endpoints[0]) / np.linalg.norm(
            np.subtract(self.endpoints[1], self.endpoints[0]))
        self.perpgradient = (self.gradient[1], -self.gradient[0])

    def set_limits(self, xlimit, ylimit, slideroffset):
        if xlimit is not None:
            self.xlimit = xlimit
        else:
            self.xlimit = (self.rect.centerx+slideroffset[0], self.rect.centerx+slideroffset[0])
        if ylimit is not None:
            self.ylimit = ylimit
        else:
            self.ylimit = (self.rect.centery+slideroffset[1], self.rect.centery+slideroffset[1])

    def set_notches(self, sliderrectsize):
        increment = np.subtract(self.endpoints[1], self.endpoints[0])/self.notches
        linewidth = tuple([i * int(sliderrectsize[1] / 2) for i in self.perpgradient])
        self.notchlines = {}
        self.notchpoints = {}
        notchnumber = 0
        for notch in np.arange(self.valuerange[0], self.valuerange[1]+1):
            self.notchpoints[notch] = tuple(self.endpoints[0]+increment*notchnumber)
            self.notchlines[notch] = [(self.endpoints[0]+increment*notchnumber+linewidth),
                                      (self.endpoints[0]+increment*notchnumber-linewidth)]
            notchnumber += 1

    def findnearestnotch(self, position):
        notchdistances = {np.linalg.norm(np.subtract(value[1], position))
                          : value[0] for value in self.notchpoints.items()}
        self.nearest_notch_value = notchdistances[min(notchdistances.keys())]
        return self.nearest_notch_value

    def movetonotch(self, rect, notchvalue):
        rect = rect.move(np.subtract(self.notchpoints[notchvalue], rect.center))
        return rect

    def resizefont(self, size=None):
        if size is None:
            size = self.rect.height
            while np.any(np.less(self.font.size(self.text), [0.95*i for i in self.rect.size])):
                self.font = pg.font.Font(None,size)
                size += 1
            while np.any(np.greater(self.font.size(self.text), [0.95*i for i in self.rect.size])):
                self.font = pg.font.Font(None,size)
                size -= 1
            else:
                self.font = pg.font.Font(None, size)
            self.fontsize = size

    def parse_text(self, text, hover_text, clicked_text):
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
            "colour": pg.Color('white'),
            "rect_colour": pg.Color('white'),
            "clicked_text_render": None,
            "hover_text_render": None,
            "font": pg.font.SysFont(None, 50),
            "call_on_release": True,
            "hover_colour": None,
            "clicked_colour": None,
            "font_colour": pg.Color('black'),
            "hover_font_colour": None,
            "clicked_font_colour": None,
            "click_sound": None,
            "hover_sound": None,
            'border_colour': pg.Color('black'),
            'border_hover_colour': pg.Color('yellow'),
            'disabled': False,
            'disabled_colour': pg.Color('grey'),
            'radius': 3,
        }
        for kwarg in kwargs:
            if kwarg in settings:
                settings[kwarg] = kwargs[kwarg]
            else:
                raise AttributeError("{} has no keyword: {}".format(self.__class__.__name__, kwarg))
        self.__dict__.update(settings)

    def render_text(self):
        if self.hover_font_colour:
            colour = self.hover_font_colour
            self.hover_text_render = self.font.render(self.hover_text, True, colour)
        if self.clicked_font_colour:
            colour = self.clicked_font_colour
            self.clicked_text_render = self.font.render(self.clicked_text, True, colour)
        self.text_render = self.font.render(self.text, True, self.font_colour)

    def get_event(self, event):
        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            self.on_click(event)
        elif event.type == pg.MOUSEBUTTONUP and event.button == 1:
            self.on_release()

    def on_click(self, event):
        if self.sliderrect.collidepoint(event.pos):
            self.clicked = True

    def on_release(self):
        if self.clicked and self.call_on_release:
          #  if user is still within button rect upon mouse release
            if pg.mouse.get_rel():
                if self.slider_player is None:
                    self.command(self.nearest_notch_value)
                else:
                    self.command(self.nearest_notch_value, self.slider_player)
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
        colour = self.colour
        text = self.text_render
        border = self.border_colour
        self.check_hover()
        if not self.disabled:
            if self.clicked:
                colour = self.clicked_colour
                if self.clicked_font_colour:
                    text = self.clicked_text_render
            elif self.hovered and self.hover_colour:
                colour = self.hover_colour
                if self.hover_font_colour:
                    text = self.hover_text_render
            if self.hovered and not self.clicked:
                border = self.border_hover_colour
        else:
            colour = self.disabled_colour

        self.draw_highlighted_line(surface, self.colour, self.font_colour, self.endpoints[0], self.endpoints[1], self.perpgradient)
        for notch in self.notchlines:
            self.draw_highlighted_line(surface, self.colour, self.font_colour, self.notchlines[notch][0], self.notchlines[notch][1],
                                       self.gradient)
        if self.radius:
            rad = self.radius
        else:
            rad = 0
        self.round_rect(surface, self.rect, border, rad, 1, colour)
        self.round_rect(surface, self.sliderrect, border, rad, 1, colour)
        if text:
            text_rect = text.get_rect(center=self.rect.center)
            surface.blit(text, text_rect)

    def round_rect(self, surface, rect, colour, rad=20, border=0, inside=(0, 0, 0, 0)):
        rect = pg.Rect(rect)
        zeroed_rect = rect.copy()
        zeroed_rect.topleft = 0, 0
        image = pg.Surface(rect.size).convert_alpha()
        image.fill((0, 0, 0, 0))
        self._render_region(image, zeroed_rect, colour, rad)
        if border:
            zeroed_rect.inflate_ip(-2 * border, -2 * border)
            self._render_region(image, zeroed_rect, inside, rad)
        surface.blit(image, rect)

    @staticmethod
    def _render_region(image, rect, colour, rad):
        corners = rect.inflate(-2 * rad, -2 * rad)
        for attribute in ("topleft", "topright", "bottomleft", "bottomright"):
            pg.draw.circle(image, colour, getattr(corners, attribute), rad)
        image.fill(colour, rect.inflate(-2 * rad, 0))
        image.fill(colour, rect.inflate(0, -2 * rad))

    @staticmethod
    def draw_highlighted_line(surface, slider_colour, border_colour, start_point, end_point, perp_gradient):
        gradient = (perp_gradient[1], -perp_gradient[0])
        perp_gradient = tuple(np.multiply(perp_gradient, 2))

        positive_offset_point = tuple(np.add(np.negative(gradient), perp_gradient))
        negative_offset_point = tuple(np.add(np.negative(gradient), np.negative(perp_gradient)))
        start_positive_offset_point = tuple(np.add(start_point, positive_offset_point))
        start_negative_offset_point = tuple(np.add(start_point, negative_offset_point))
        end_positive_offset_point = tuple(np.add(end_point, positive_offset_point))
        end_negative_offset_point = tuple(np.add(end_point, negative_offset_point))

        left, top = start_negative_offset_point
        width, height = np.subtract(end_positive_offset_point, start_negative_offset_point)
        rect = pg.Rect(left, top, width, height)
        pg.draw.rect(surface, slider_colour, rect)

        pg.draw.line(surface, border_colour, start_positive_offset_point, end_positive_offset_point)
        pg.draw.line(surface, border_colour, start_negative_offset_point, end_negative_offset_point)
        pg.draw.line(surface, border_colour, start_positive_offset_point, start_negative_offset_point)
        pg.draw.line(surface, border_colour, end_positive_offset_point, end_negative_offset_point)


class GameBoard:
    def __init__(self, parameters_dict):
        self.parameters_dict = parameters_dict
        self.board_width = parameters_dict["Board Width"]["value"]
        self.positions = np.full((self.board_width, self.board_width), ' ', 'U1')
        self.total_players = parameters_dict["Total Players"]["value"]
        self.winning_line = parameters_dict["Winning Line"]["value"]
        self.total_humans = parameters_dict["Human Players"]["value"]
        self.gametokens = [" ", "X", "O"]

        self.move_history_dict = []

        if self.total_players > 2:
            for i in range(2, self.total_players):
                self.add_board_token()

        self.current_turn_number = 0
        self.human_turn_list = np.sort(np.random.choice(self.total_players, self.total_humans, replace = False))
        self.ai_turn_list = [turns for turns in np.arange(self.total_players) if turns not in self.human_turn_list]

    def add_board_token(self):
        self.gametokens.append(random.choice([i for i in string.ascii_uppercase if i not in self.gametokens]))

    def player_number(self, playerindex):
        return playerindex + 1

    def previous_turn(self):
        return (self.current_turn_number - 1) % self.total_players

    def player_token(self, playerindex):
        return self.gametokens[self.player_number(playerindex)]

    def available_board_positions(self):
        available_board_positions_array = np.asarray(np.where((self.positions == self.gametokens[0])))
        available_board_positions_tuple_list = []
        for col in range(0, available_board_positions_array.shape[1]):
            available_board_positions_tuple_list.append(tuple(available_board_positions_array[:, col]))
        return available_board_positions_tuple_list

    def next_turn(self, turn):
        return (turn + 1) % self.total_players

    def make_next_play(self, action):
        if self.positions[action] == self.gametokens[0]:
            self.positions[action] = self.gametokens[self.player_number(self.current_turn_number)]
            self.current_turn_number = self.next_turn(self.current_turn_number)
            self.move_history_dict.append((len(self.move_history_dict), self.gametokens[self.player_number(self.current_turn_number)], action))
        else:
            return False

    def copy(self):
        return self.board_width, self.total_players, self.winning_line, self.total_humans

    @staticmethod
    def find_subarray(array, subarray):
        if array.tostring().find(subarray.tostring()) != -1:
            return True
        else:
            return False

    def rowcheck(self, type, i):
        return self.find_subarray(self.positions[i, :], np.resize(np.array(type), self.winning_line))

    def colcheck(self, type, i):
        return self.find_subarray(self.positions[:, i], np.resize(np.array(type), self.winning_line))

    def diagcheck(self, type, i):
        return self.find_subarray(np.diagonal(self.positions, i), np.resize(np.array(type), self.winning_line))

    def oppdiagcheck(self, type, i):
        return self.find_subarray(np.diagonal(np.fliplr(self.positions), i), np.resize(np.array(type), self.winning_line))

    def find_winning_player(self):
        for i in range(0, self.board_width):
            if self.rowcheck(self.player_token(self.previous_turn()), i) or \
                    self.colcheck(self.player_token(self.previous_turn()), i):
                return self.player_number(self.previous_turn())
        for i in range(-self.board_width + self.winning_line, self.board_width + 1 - self.winning_line):
            if self.diagcheck(self.player_token(self.previous_turn()), i) or \
                    self.oppdiagcheck(self.player_token(self.previous_turn()), i):
                return self.player_number(self.previous_turn())
        if len(self.available_board_positions()) == 0:
            return 0
        else:
            return -1


class Node:
    def __init__(self, node_depth, action=None, parent=None, board=None):
        self.parent = parent
        self.board = copy.deepcopy(board)
        if action is not None:
            self.board.make_next_play(action)
        self.children = []
        self.score = 0
        self.visits = 0
        self.node_depth = node_depth
        self.untried_actions = self.board.available_board_positions()
        self.action = action

    def select(self):
        s = sorted(self.children, key=lambda c: c.score / c.visits + 0.2 * sqrt(2 * log(self.visits) / c.visits))
        s[-1].score -= 1
        return s[-1]

    def expand(self, action):
        child = Node(node_depth=self.node_depth + 1, parent=self, action=action, board=self.board)
        self.children.append(child)
        self.untried_actions.remove(action)
        return child

    def update(self, result):
        self.visits += 1
        self.score += result + 1

    def UpdateRootNode(self, rootstate, player):
        #global root
        #new_root_node = root[player]
        new_root_node = self

        while len(new_root_node.board.move_history_dict) < len(rootstate.move_history_dict):
            if new_root_node.children:
                child = [child for child in new_root_node.children if
                         child.action == rootstate.move_history_dict[len(new_root_node.board.move_history_dict)][2]]
                if len(child) > 0:
                    child = child[0]
            else:
                child = new_root_node.expand(rootstate.move_history_dict[len(new_root_node.board.move_history_dict)][2])
            if child:
                new_root_node = child

        return new_root_node

    def UCTIteration(self, node, player, lock):
        #  expansion - expand parent to a random untried action
        if len(node.untried_actions) > 0:
            #  simulation - rollout to terminal state from current
            #  state using random actions
            while node.board.find_winning_player() < 0:
                action = random.choice(node.untried_actions)
                lock.acquire()
                node = node.expand(action)
                lock.release()

        #  back propagation - propagate result of rollout game up the tree
        #  reverse the result if player at the node lost the rollout game
        if node.board.find_winning_player() >= 0:
            #  result = node.board.find_winning_player() / node.node_depth
            result = 0
            if node.board.find_winning_player() != 0:
                if node.board.find_winning_player() == player:
                    result = 1 / node.node_depth
                else:
                    result = -1 / node.node_depth
            while node is not None:
                lock.acquire()
                node.update(result)
                lock.release()
                #  print("Level", node.node_depth,"Result", result,node.board.positions)
                node = node.parent

    def SelectNode(self, root, player, lock, executor):
        node = root
        #  selection - select best child if parent fully expanded and not terminal
        while not node.untried_actions and node.children:
            lock.acquire()
            node = node.select()
            lock.release()
        executor.submit(self.UCTIteration(node, player, lock))

    def PickOpponentMove(self, root):
        s = sorted(root.children, key=lambda c: c.score / c.visits)

        #for child in root.children:
         #   print("Visits", child.visits, "score", child.score, "\n", child.board.positions)

        return tuple(s[-1].action)


def ResetBoardFunc():
    global reset_game
    reset_game = True


def ChangeBoardsizeFunc(newsize):
    global board_parameter_dict
    board_parameter_dict["Board Width"]["value"] = newsize


def ChangeWinningLineFunc(newlength):
    global board_parameter_dict
    board_parameter_dict["Winning Line"]["value"] = newlength


def ChangePlayerCountFunc(newplayers):
    global board_parameter_dict
    board_parameter_dict["Total Players"]["value"] = newplayers
    if newplayers < board_parameter_dict["Human Players"]["value"]:
        ChangeHumanPlayerCountFunc(newplayers)


def ChangeHumanPlayerCountFunc(newtotal_humans):
    global board_parameter_dict
    board_parameter_dict["Human Players"]["value"] = newtotal_humans
    if newtotal_humans > board_parameter_dict["Total Players"]["value"]:
        ChangePlayerCountFunc(newtotal_humans)


def ChangeDifficultyFunc(newdifficulty, player):
    global player_dict
    player_dict[player]["value"] = newdifficulty


def OpenColourDialog(dict, player):
    colour = QColorDialog.getColor().name()
    red, green, blue = bytes.fromhex(colour[1:])
    colour = (red, green, blue)
    dict[player]["colour"] = colour
    try:
        dict[player]["updated"] = False
    except KeyError:
        pass


def CreateButtonsFunc(board_width):
    global button_list, screen_pixels, board
    if button_list:
        del button_list
    button_list = []
    button_height = min(screen_pixels[0] * 3 / 4, screen_pixels[1]) / board_width
    button_width = button_height
    for row in range(0, board_width):
        for col in range(0, board_width):
            top = button_height * row
            left = button_width * col
            if row+col == 0:
                b = Button(rect=(left, top, button_width, button_height), text="X", command=lambda l=(row, col):
                           board.make_next_play(l), position=(row, col), **buttonsettings)
                button_list.append(b)
                fontsize = b.fontsize
            else:
                b = Button(rect=(left, top, button_width, button_height), text="X", fontsize=fontsize,
                           command=lambda l=(row, col): board.make_next_play(l), position=(row, col), **buttonsettings)
                button_list.append(b)
    b = Button(rect=(screen_pixels[0] * 63 / 80, screen_pixels[1] - 130, 300, 100),
               command=ResetBoardFunc, text="Restart", **buttonsettings)
    button_list.append(b)
    b = Button(rect=(screen_pixels[0] * 49 / 80, screen_pixels[1] - 130, 300, 100),
               command=CreateOptionsScreen, text="Options", **buttonsettings)
    button_list.append(b)


def CreateSlidersFunc(availablerect, labelsize, sliderrectsize, slider_parameter_dict):
    global slider_list, screen_colour_dict
    if slider_list != {}:
        slider_list = {}

    labelposition = np.subtract((int(availablerect[0]+availablerect[2]*1/2)
                                 , int(availablerect[1]+availablerect[3] * 1 / 20)), [int(0.5*i) for i in labelsize])
    xlimit = np.add((availablerect[2]*1/10, availablerect[2]*9/10), availablerect[0])
    ylimit = (labelposition[1] + labelsize[1] + sliderrectsize[1]*1/2, )*2
    slidernumber = 0
    totalsliders = len(slider_parameter_dict.keys()) + 1
    increment = int(availablerect[3]/totalsliders)

    for key in slider_parameter_dict.keys():
        if slider_parameter_dict == player_dict:
            text = "Player " + str(key) + " Difficulty"
            player = key
        else:
            text = key
            player = None
        s = Slider(rect=(labelposition[0], labelposition[1]+slidernumber*increment)+labelsize,
                   sliderrectsize=sliderrectsize, startingvalue=slider_parameter_dict[key]["value"],
                   command=slider_parameter_dict[key]["function"], text=text, xlimit=xlimit,
                   ylimit=np.add(ylimit, slidernumber*increment+availablerect[3]*1/100), valuerange=slider_parameter_dict[key]["range"]
                   , slider_player=player, **slidersettings)
        slider_list[key] = s
        slidernumber += 1


def CreateDisplayWindowsFunc(sliders, show_turn_count=True):
    global window_list, screen_pixels
    window_list = {}
    firstsliderbool = True
    for key in sliders.keys():
        rect = sliders[key].rect
        rectposition = rect.topleft
        windowrect = (rectposition[0]+rect.size[0]+30, rectposition[1], 40, rect.size[1])
        if firstsliderbool:
            window = Button(windowrect, text=str(sliders[key].startingvalue)
                            , disabled=True, **buttonsettings)
            window_list[key] = window
            fontsize = window.fontsize
        else:
            window = Button(windowrect, text=str(sliders[key].startingvalue)
                            , fontsize=fontsize, disabled=True, **buttonsettings)
            window_list[key] = window

    if show_turn_count:
        currentturnrect = (screen_pixels[1], 0, screen_pixels[0]-screen_pixels[1], 150)
        window_list["Current Turn"] = Button(currentturnrect, text="Player 1's turn", disabled=True, **buttonsettings)


def CreateWinScreenFunc(screen_pixels, board):
    global button_list, slider_list, window_list, show_win_screen_bool
    button_list = []
    slider_list = {}
    window_list = {}

    if board.find_winning_player() == 0:
        victorytext = "Stalemate"
    else:
        if board.previous_turn() in board.human_turn_list:
            victorytext = "Human player " \
                          + str(board.player_number(list(board.human_turn_list).index(board.previous_turn()))) \
                          + " wins!"
        else:
            victorytext = "Player " + str(board.player_number(board.previous_turn())) + " wins!"

    window = Button(rect=(0, screen_pixels[1]*3/8, screen_pixels[0], screen_pixels[1]*1/4)
                    , text=victorytext, disabled=True, **buttonsettings)
    window_list["End Game"] = window
    b = Button(rect=(screen_pixels[0] * 1/2-150, screen_pixels[1]*5/8, 300, 100)
               , command=ResetBoardFunc, text="Restart", **buttonsettings)
    b.disabled = False
    button_list.append(b)
    for button in button_list:
        button.disabled = False
    show_win_screen_bool = True


def CreateOptionsScreen():
    global button_list, slider_list, window_list, show_option_screen, screen_pixels
    global app, player_dict
    show_option_screen = True
    button_list = []
    slider_list = {}
    window_list = {}

    CreateSlidersFunc((0, 0, screen_pixels[0]*9/10, screen_pixels[1]*8/10)
                      , labelsize=(300, 50), sliderrectsize=(10, 50), slider_parameter_dict=player_dict)
    CreateDisplayWindowsFunc(slider_list, False)

    player = 1
    for slider in slider_list.values():
        b = Button(rect=(*np.subtract(slider.endpoints[1], (-20, 50)), 300, 100), command=lambda l=(player_dict, player)
                   : OpenColourDialog(*l), text="Change colour", **buttonsettings)
        button_list.append(b)
        player += 1
    unchanging_button_y_offset = screen_pixels[1]*8/10

    b = Button(rect=(screen_pixels[0] * 19 / 80 - 300, unchanging_button_y_offset, 300, 80),
               command=lambda l=(screen_colour_dict, "Board"): OpenColourDialog(*l),
               text="Board Colour", **buttonsettings)
    button_list.append(b)
    b = Button(rect=(screen_pixels[0] * 21 / 80, unchanging_button_y_offset, 300, 80),
               command=lambda l=(screen_colour_dict, "Screen"): OpenColourDialog(*l),
               text="Background Colour", **buttonsettings)
    button_list.append(b)

    b = Button(rect=(screen_pixels[0] * 59 / 80 - 300, unchanging_button_y_offset, 300, 80),
               command=CreateMainScreen, text="Return to Game", **buttonsettings)
    button_list.append(b)
    b = Button(rect=(screen_pixels[0] * 61 / 80, unchanging_button_y_offset, 300, 80),
               command=ResetBoardFunc, text="Restart", **buttonsettings)
    button_list.append(b)


def CreateMainScreen():
    global button_list, slider_list, window_list, board_parameter_dict, screen_pixels, screen_colour_dict
    screen_colour_dict["Screen"]["updated"] = False
    CreateSlidersFunc((screen_pixels[1], screen_pixels[1]*1/8, screen_pixels[0]-screen_pixels[1], screen_pixels[1]*8/10)
                      , labelsize=(150, 40), sliderrectsize=(10, 50), slider_parameter_dict=board_parameter_dict)
    CreateButtonsFunc(board_parameter_dict["Board Width"]["value"])
    CreateDisplayWindowsFunc(slider_list)


def GameResetFunc():
    global screen, factor
    global button_list, slider_list, window_list
    global board_parameter_dict, player_dict, winning_player, reset_game, show_win_screen_bool
    global board, boardsim, root, turn, iterations, ai_iteration_limit

    screen.fill(screen_colour_dict["Screen"]["colour"])
    factor = board.board_width / board_parameter_dict["Board Width"]["value"] - 1

    board = GameBoard(board_parameter_dict)
    boardsim = CopyBoard(board)
    root = CreateRootNodes()

    oldplayers = len(player_dict.keys())
    newplayers = board_parameter_dict["Total Players"]["value"]
    if oldplayers < newplayers:
        for player in range(oldplayers + 1, newplayers + 1):
            player_dict[player] = {"token": board.player_token(player-1), "colour": (0, 0, 0), "value": 5,
                                        "function": ChangeDifficultyFunc, "range": (1, 10)}
    elif oldplayers > newplayers:
        for player in range(newplayers + 1, oldplayers + 1):
            del player_dict[player]

    CreateButtonsFunc(board_parameter_dict["Board Width"]["value"])
    CreateSlidersFunc(
        (screen_pixels[1], screen_pixels[1] * 1 / 8, screen_pixels[0] - screen_pixels[1], screen_pixels[1] * 9 / 10),
        labelsize=(150, 50), sliderrectsize=(10, 50), slider_parameter_dict=board_parameter_dict)
    CreateDisplayWindowsFunc(slider_list)

    reset_game = False
    show_win_screen_bool = False
    turn = -1
    iterations = 0
    winning_player = -1


def ScreenUpdate():
    global screen
    global screen_pixels, factor
    global button_list, slider_list, window_list
    global board_parameter_dict, player_dict, winning_player
    global board, turn

    screen.fill(screen_colour_dict["Screen"]["colour"])
    mouse = pg.mouse.get_pos()
    for event in pg.event.get():
        if event.type == pg.QUIT:
            pg.quit()
            sys.exit(0)
        if event.type == pg.VIDEORESIZE and screen_pixels != event.size:
            factor = np.subtract(np.divide(event.size, screen_pixels), 1)
            screen_pixels = event.size
            for button in button_list:
                button.rect = button.rect.inflate(button.rect.size * factor)
                button.rect = button.rect.move(button.rect.center * factor)
                button.resizefont(size=int(button.fontsize * (1 + np.min(factor))))
            for slider in slider_list.values():
                slider.rect = slider.rect.inflate(slider.rect.size * factor)
                slider.sliderrect = slider.sliderrect.inflate(slider.sliderrect.size * factor)
                slider.rect = slider.rect.move(slider.rect.center * factor)
                slider.sliderrect = slider.sliderrect.move(slider.sliderrect.center * factor)
                slider.xlimit = slider.xlimit * (1 + factor[0])
                slider.ylimit = slider.ylimit * (1 + factor[1])
                slider.createsliderlines()
                slider.set_notches(slider.sliderrect.size)
                slider.resizefont(size=int(slider.fontsize * (1 + np.min(factor))))
            for window in window_list.values():
                window.rect = window.rect.inflate(window.rect.size * factor)
                window.rect = window.rect.move(window.rect.center * factor)
                window.resizefont(size=int(window.fontsize * (1 + 2 * np.min(factor))))
            screencopy = screen.copy()
            screen = pg.display.set_mode(screen_pixels, pg.RESIZABLE)
            screen.blit(screencopy, (0, 0))

        for button in button_list:
            button.get_event(event)
            if button.position:
                button.colour = button.hover_colour = button.clicked_colour = screen_colour_dict["Board"]["colour"]
                if turn in player_dict.keys():
                    if board.positions[button.position] == " ":
                        button.font_colour = button.hover_font_colour = button.clicked_font_colour \
                            = player_dict[board.player_number(turn)]["colour"]
                    else:
                        button.font_colour = button.hover_font_colour = button.clicked_font_colour \
                            = player_dict[board.gametokens.index(board.positions[button.position])]["colour"]

                if board.positions[button.position] == " " and turn in board.human_turn_list:
                    button.parse_text(text=board.positions[button.position], hover_text=board.player_token(turn)
                                      , clicked_text=board.player_token(turn))
                else:
                    button.parse_text(text=board.positions[button.position], hover_text=board.positions[button.position]
                                      , clicked_text=board.positions[button.position])
            button.draw(screen)
        for key in slider_list.keys():
            slider_list[key].get_event(event)
            if slider_list[key].clicked:
                notchvalue = slider_list[key].findnearestnotch(mouse)
                slider_list[key].sliderrect = slider_list[key].movetonotch(slider_list[key].sliderrect, notchvalue)
                window_list[key].parse_text(str(notchvalue))
            slider_list[key].draw(screen)
        for window in window_list.values():
            window.draw(screen)
        pg.display.update()


def CalculateAIIterations(player):
    global board_parameter_dict, player_dict
    return int(player_dict[player]["value"]*(board_parameter_dict["Board Width"]["value"]**2)*5)


def CreateRootNodes():
    try:
        global root
    except Exception:
        pass
    rootcopy = Node(board=boardsim, node_depth=1)
    root = {}
    for turn in board.ai_turn_list:
        root[board.player_number(turn)] = rootcopy
    return root


def CopyBoard(board):
    boardcopy = GameBoard(board.parameters_dict)
    boardcopy.gametokens = board.gametokens
    return boardcopy


button_list = []
slider_list = {}
window_list = {}
player_dict = {}
screen_colour_dict = {}

if __name__ == '__main__':
    pg.init()
    app = QApplication(sys.argv)

    slidersettings = {
        "clicked_font_colour": (0, 0, 0),
        "clicked_colour": (255, 255, 255),
        "hover_font_colour": (0, 0, 0),
        "hover_colour": (255, 255, 235),
        'font': pg.font.Font(None, 30),
        'font_colour': (0, 0, 0),
        'border_colour': (0, 0, 0),
        'colour': (255, 255, 255),
    }
    buttonsettings = {
        "clicked_font_colour": (0, 0, 0),
        "clicked_colour": (255, 255, 255),
        "hover_font_colour": (0, 0, 0),
        "hover_colour": (255, 255, 235),
        'font': pg.font.Font(None, 250),
        'font_colour': (0, 0, 0),
        'border_colour': (0, 0, 0),
    }
    board_parameter_dict = {
        "Board Width": {"function": ChangeBoardsizeFunc, "range": (3, 8), "value": 3},
        "Winning Line": {"function": ChangeWinningLineFunc, "range": (2, 8), "value": 3},
        "Total Players": {"function": ChangePlayerCountFunc, "range": (2, 8), "value": 2},
        "Human Players": {"function": ChangeHumanPlayerCountFunc, "range": (0, 8), "value": 1},
    }
    screen_colour_dict = {
        "Screen": {"colour": (0, 0, 0), "updated": False},
        "Board": {"colour": (255, 255, 255), },
    }

    clock = pg.time.Clock()
    reset_game = False
    show_win_screen_bool = False
    show_option_screen = False
    turn = -1
    screen_pixels = (1920, 1080)

    screen = pg.display.set_mode(screen_pixels, pg.RESIZABLE)
    pg.display.set_caption("Noughts and Crosses")
    screen_rect = screen.get_rect()
    fps_int = 60
    refresh_time = datetime.timedelta(seconds=1)/fps_int

    CreateMainScreen()

    board = GameBoard(board_parameter_dict)
    winning_player = board.find_winning_player()

    player = 0
    while player < board.total_players:
        player_dict[player + 1] = {"token": board.player_token(player), "colour": (0, 0, 0), "value": 5,
                                   "function": ChangeDifficultyFunc, "range": (1, 10)}
        player += 1

    #  Create a copy of the board for the UCT algorithm to modify
    boardsim = CopyBoard(board)

    #  Create the top level node for all simulations of board states
    root = CreateRootNodes()

    ai_iteration_limit = CalculateAIIterations(board.player_number(board.current_turn_number))
    iterations = 0
    lock = threading.RLock()

    with concurrent.futures.ThreadPoolExecutor() as executor:
        previous_frame_time = datetime.datetime.now()
        while True:
            if datetime.datetime.now() - previous_frame_time > refresh_time:
                executor.submit(ScreenUpdate())
                previous_frame_time = datetime.datetime.now()

            if board.find_winning_player() != -1:
                if not show_win_screen_bool:
                    CreateWinScreenFunc(screen_pixels, board)
            else:
                if turn != board.current_turn_number:
                    turn = board.current_turn_number
                    ai_iteration_limit = CalculateAIIterations(board.player_number(turn))
                    try:
                        if window_list["Current Turn"]:
                            turntext = "Player " + str(board.player_number(board.current_turn_number)) + "'s turn"
                            window_list["Current Turn"].parse_text(turntext)
                    except KeyError:
                        pass
                    for button in button_list:
                        if button.position:
                            if turn in board.human_turn_list:
                                button.disabled = False
                            else:
                                button.disabled = True

                    if board.ai_turn_list:
                        current_turn = board.current_turn_number
                        if len(board.ai_turn_list) == 1:
                            current_turn = board.ai_turn_list[0]
                        else:
                            while current_turn not in board.ai_turn_list:
                                current_turn = board.next_turn(current_turn)
                        player = board.player_number(current_turn)
                        new_root_node = root[player].UpdateRootNode(board, player)

                if new_root_node.visits > ai_iteration_limit:
                    if turn in board.ai_turn_list:
                        print("Opponent Turn")
                        Opponent_play = new_root_node.PickOpponentMove(new_root_node)
                        board.make_next_play(Opponent_play)
                    else:
                        player = board.player_number(current_turn)
                        new_root_node = root[player].UpdateRootNode(board, player)

                while datetime.datetime.now() - previous_frame_time < refresh_time:
                    executor.submit(new_root_node.SelectNode(new_root_node, player, lock, executor))

            if reset_game:
                GameResetFunc()
